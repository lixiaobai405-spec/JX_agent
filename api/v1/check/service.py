import math
from collections import Counter
from datetime import datetime, timezone
from types import SimpleNamespace

from sqlalchemy import and_, distinct, exists, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.check_phase import SelfAssessment, EvaluationTask, Evaluation, ScoreAggregate, FinalResult
from models.check_phase import Goal, Indicator
from models.do_phase import DataCheckin
from models.period import Period, PeriodStatus
from models.user import User, UserRole, UserStatus
from core.exceptions import (
    AppException,
    PermissionDeniedError,
    SelfAssessmentNotFoundError,
    EvaluationTaskNotFoundError,
    SelfAssessmentRequiredError,
    SelfAssessmentAlreadySubmittedError,
    ScoreAggregateNotFoundError,
    FinalResultNotFoundError,
    WeightValidationError,
)


def _invalid_evaluation(message: str) -> AppException:
    return AppException(422, "CHECK_008", message)


def _evaluation_conflict(message: str = "Evaluation task is no longer pending") -> AppException:
    return AppException(409, "CHECK_009", message)


def _final_result_incomplete(missing_indicator_ids: set[str]) -> AppException:
    missing = ", ".join(sorted(missing_indicator_ids))
    return AppException(
        409,
        "CHECK_012",
        f"Missing valid evaluations for indicators: {missing}",
    )


def _invalid_self_assessment(message: str) -> AppException:
    return AppException(422, "CHECK_014", message)


_ADMIN_ROLES = (UserRole.hr_admin, UserRole.system_admin)


async def _get_subordinate_ids(db: AsyncSession, manager_id: str) -> list[str]:
    direct_reports = (
        select(User.id.label("id"))
        .where(
            User.manager_id == manager_id,
            User.status == UserStatus.active,
            User.deleted_at.is_(None),
        )
        .cte("check_subordinate_ids", recursive=True)
    )
    descendants = (
        select(User.id.label("id"))
        .join(direct_reports, User.manager_id == direct_reports.c.id)
        .where(
            User.status == UserStatus.active,
            User.deleted_at.is_(None),
        )
    )
    subordinate_ids = direct_reports.union(descendants)
    result = await db.execute(select(subordinate_ids.c.id))
    return list(result.scalars().all())


async def _get_active_goal(
    db: AsyncSession,
    goal_id: str,
    *,
    for_update: bool = False,
) -> Goal:
    query = (
        select(Goal)
        .join(User, User.id == Goal.owner_user_id)
        .where(
            Goal.id == goal_id,
            Goal.deleted_at.is_(None),
            User.status == UserStatus.active,
            User.deleted_at.is_(None),
        )
    )
    if for_update:
        query = query.with_for_update()
    result = await db.execute(query)
    goal = result.scalar_one_or_none()
    if goal is None:
        raise AppException(404, "CHECK_010", "Evaluation goal not found")
    return goal


async def _assert_goal_access(
    db: AsyncSession,
    current_user: User,
    goal: Goal,
) -> None:
    if current_user.role in _ADMIN_ROLES or current_user.id == goal.owner_user_id:
        return
    if current_user.role == UserRole.manager:
        subordinate_ids = await _get_subordinate_ids(db, current_user.id)
        if goal.owner_user_id in subordinate_ids:
            return
    assigned_task = await db.scalar(
        select(EvaluationTask.id)
        .where(
            EvaluationTask.goal_id == goal.id,
            EvaluationTask.evaluator_user_id == current_user.id,
            EvaluationTask.deleted_at.is_(None),
        )
        .limit(1)
    )
    if assigned_task is not None:
        return
    raise PermissionDeniedError("Cannot access this user's check-stage data")


async def _assert_goal_owner(current_user: User, goal: Goal) -> None:
    if current_user.id != goal.owner_user_id:
        raise PermissionDeniedError("Only the goal owner can change self-assessment")


async def _assert_goal_manager(
    db: AsyncSession,
    current_user: User,
    goal: Goal,
) -> None:
    if current_user.role in _ADMIN_ROLES:
        return
    if current_user.role == UserRole.manager:
        subordinate_ids = await _get_subordinate_ids(db, current_user.id)
        if goal.owner_user_id in subordinate_ids:
            return
    raise PermissionDeniedError("Only the employee's manager can perform this action")


def validate_score_value(score: float) -> float:
    if not math.isfinite(score) or score < 0 or score > 100:
        raise ValueError("评分必须在 0-100 之间")
    return score


def validate_score_items(items: dict | None) -> dict | None:
    if items is None:
        return None
    for item in items.values():
        score = item.get("score") if isinstance(item, dict) else None
        if score is None:
            raise ValueError("评分不能为空")
        validate_score_value(float(score))
    return items


async def _normalize_self_assessment_items(
    db: AsyncSession,
    goal_id: str,
    items: dict,
    *,
    require_complete: bool = False,
) -> dict:
    result = await db.execute(
        select(Indicator.id, Indicator.name).where(
            Indicator.goal_id == goal_id,
            Indicator.redline.is_(False),
            Indicator.deleted_at.is_(None),
        )
    )
    indicator_rows = result.all()
    indicator_ids = {indicator_id for indicator_id, _name in indicator_rows}
    name_counts = Counter(name for _indicator_id, name in indicator_rows)
    unique_name_ids = {
        name: indicator_id
        for indicator_id, name in indicator_rows
        if name_counts[name] == 1
    }

    normalized: dict[str, dict] = {}
    for raw_key, item in items.items():
        key = str(raw_key)
        indicator_id = key if key in indicator_ids else unique_name_ids.get(key)
        if indicator_id is None:
            raise _invalid_self_assessment(
                f"Unknown or ambiguous self-assessment indicator: {key}"
            )
        if indicator_id in normalized:
            raise _invalid_self_assessment(
                f"Duplicate self-assessment indicator: {indicator_id}"
            )
        normalized[indicator_id] = item

    try:
        validated = validate_score_items(normalized) or {}
    except (TypeError, ValueError) as exc:
        raise _invalid_self_assessment(str(exc)) from exc
    if require_complete:
        missing = indicator_ids - set(validated)
        if missing:
            raise _invalid_self_assessment(
                "Missing self-assessment scores for indicators: "
                + ", ".join(sorted(missing))
            )
    return validated


async def _normalize_self_assessment_for_read(
    db: AsyncSession,
    assessment: SelfAssessment,
) -> None:
    normalized = await _normalize_self_assessment_items(
        db,
        assessment.goal_id,
        assessment.items or {},
    )
    if normalized != assessment.items:
        assessment.items = normalized


# Self Assessment
async def create_self_assessment(db: AsyncSession, current_user: User, goal_id: str, items: dict):
    goal = await _get_active_goal(db, goal_id)
    await _assert_goal_owner(current_user, goal)
    assessment = SelfAssessment(
        goal_id=goal_id,
        user_id=current_user.id,
        items=await _normalize_self_assessment_items(db, goal_id, items),
        status="draft"
    )
    db.add(assessment)
    await db.commit()
    await db.refresh(assessment)
    return assessment


async def get_self_assessment(
    db: AsyncSession,
    current_user: User,
    assessment_id: str,
):
    result = await db.execute(
        select(SelfAssessment).where(
            SelfAssessment.id == assessment_id,
            SelfAssessment.deleted_at.is_(None),
        )
    )
    assessment = result.scalar_one_or_none()
    if not assessment:
        raise SelfAssessmentNotFoundError()
    goal = await _get_active_goal(db, assessment.goal_id)
    await _assert_goal_access(db, current_user, goal)
    await _normalize_self_assessment_for_read(db, assessment)
    return assessment


async def update_self_assessment(db: AsyncSession, current_user: User, assessment_id: str, items: dict | None = None):
    assessment = await get_self_assessment(db, current_user, assessment_id)
    goal = await _get_active_goal(db, assessment.goal_id)
    await _assert_goal_owner(current_user, goal)
    if assessment.status != "draft":
        raise SelfAssessmentAlreadySubmittedError()
    if items is not None:
        assessment.items = await _normalize_self_assessment_items(
            db,
            goal.id,
            items,
        )
    await db.commit()
    await db.refresh(assessment)
    return assessment


async def submit_self_assessment(db: AsyncSession, current_user: User, assessment_id: str):
    assessment = await get_self_assessment(db, current_user, assessment_id)
    goal = await _get_active_goal(db, assessment.goal_id)
    await _assert_goal_owner(current_user, goal)
    if assessment.status != "draft":
        raise SelfAssessmentAlreadySubmittedError()
    assessment.items = await _normalize_self_assessment_items(
        db,
        goal.id,
        assessment.items or {},
        require_complete=True,
    )
    assessment.status = "submitted"
    assessment.submitted_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(assessment)
    return assessment


async def get_goal_self_assessment(db: AsyncSession, current_user: User, goal_id: str):
    goal = await _get_active_goal(db, goal_id)
    await _assert_goal_access(db, current_user, goal)
    query = select(SelfAssessment).where(
        SelfAssessment.goal_id == goal_id,
        SelfAssessment.deleted_at.is_(None),
    )
    result = await db.execute(query)
    assessment = result.scalar_one_or_none()
    if assessment is not None:
        await _normalize_self_assessment_for_read(db, assessment)
    return assessment


# Evaluation Tasks
async def list_evaluation_tasks(db: AsyncSession, current_user: User, status: str | None = None):
    query = select(EvaluationTask).where(
        EvaluationTask.evaluator_user_id == current_user.id,
        EvaluationTask.deleted_at.is_(None),
    )
    if status:
        query = query.where(EvaluationTask.status == status)
    query = query.order_by(EvaluationTask.due_at)
    result = await db.execute(query)
    return result.scalars().all()


async def get_evaluation_task(db: AsyncSession, task_id: str):
    result = await db.execute(
        select(EvaluationTask).where(
            EvaluationTask.id == task_id,
            EvaluationTask.deleted_at.is_(None),
        )
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise EvaluationTaskNotFoundError()
    return task


async def get_my_pending_evaluation_tasks(db: AsyncSession, current_user: User):
    query = select(EvaluationTask).where(
        EvaluationTask.evaluator_user_id == current_user.id,
        EvaluationTask.status == "pending",
        EvaluationTask.deleted_at.is_(None),
    ).order_by(EvaluationTask.due_at)
    result = await db.execute(query)
    return result.scalars().all()


async def get_my_pending_evaluation_count(
    db: AsyncSession,
    current_user: User,
) -> int:
    query = (
        select(func.count(distinct(Goal.owner_user_id)))
        .select_from(EvaluationTask)
        .join(Goal, Goal.id == EvaluationTask.goal_id)
        .join(
            Indicator,
            and_(
                Indicator.id == EvaluationTask.indicator_id,
                Indicator.goal_id == Goal.id,
            ),
        )
        .join(Period, Period.id == Goal.period_id)
        .where(
            EvaluationTask.evaluator_user_id == current_user.id,
            EvaluationTask.status == "pending",
            EvaluationTask.deleted_at.is_(None),
            Goal.deleted_at.is_(None),
            Indicator.deleted_at.is_(None),
            Indicator.redline.is_(False),
            Period.status.in_((PeriodStatus.draft, PeriodStatus.open)),
            Period.deleted_at.is_(None),
        )
    )
    result = await db.execute(query)
    return int(result.scalar_one() or 0)


async def _begin_check_write_transaction(db: AsyncSession) -> None:
    bind = db.bind
    dialect_name = bind.dialect.name if bind is not None else db.get_bind().dialect.name

    if dialect_name == "sqlite":
        if db.in_transaction():
            if db.new or db.dirty or db.deleted:
                raise RuntimeError(
                    "Cannot start an evaluation-task write while the session has pending changes"
                )
            await db.commit()
        await db.execute(text("BEGIN IMMEDIATE"))
    elif not db.in_transaction():
        await db.begin()


async def generate_evaluation_tasks(db: AsyncSession, current_user: User, goal_id: str):
    from datetime import timedelta

    actor = SimpleNamespace(id=current_user.id, role=current_user.role)
    await _begin_check_write_transaction(db)

    try:
        goal = await _get_active_goal(db, goal_id, for_update=True)
        await _assert_goal_manager(db, actor, goal)

        period_result = await db.execute(
            select(Period)
            .where(
                Period.id == goal.period_id,
                Period.deleted_at.is_(None),
            )
            .with_for_update()
        )
        period = period_result.scalar_one_or_none()
        if not period or not period.d_phase_completed:
            raise PermissionDeniedError(
                "D phase must be completed before starting C phase evaluation"
            )

        user_result = await db.execute(
            select(User).where(
                User.id == goal.owner_user_id,
                User.status == UserStatus.active,
                User.deleted_at.is_(None),
            )
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise AppException(404, "CHECK_010", "Evaluation owner not found")

        is_admin = actor.role in _ADMIN_ROLES
        evaluator_id = actor.id if is_admin else user.manager_id
        if not evaluator_id:
            await db.commit()
            return []

        result = await db.execute(
            select(Indicator).where(
                Indicator.goal_id == goal_id,
                Indicator.deleted_at.is_(None),
                Indicator.redline.is_(False),
            )
        )
        indicators = result.scalars().all()

        tasks_created = []
        for indicator in indicators:
            existing_result = await db.execute(
                select(EvaluationTask)
                .where(
                    EvaluationTask.goal_id == goal_id,
                    EvaluationTask.indicator_id == indicator.id,
                    EvaluationTask.evaluator_user_id == evaluator_id,
                    EvaluationTask.deleted_at.is_(None),
                )
                .order_by(EvaluationTask.created_at.asc(), EvaluationTask.id.asc())
            )
            existing_tasks = list(existing_result.scalars().all())
            if existing_tasks:
                task = existing_tasks[0]
                for duplicate in existing_tasks[1:]:
                    duplicate.deleted_at = datetime.now(timezone.utc)
                tasks_created.append(task)
                continue

            now = datetime.now(timezone.utc)
            task = EvaluationTask(
                goal_id=goal_id,
                indicator_id=indicator.id,
                evaluator_user_id=evaluator_id,
                assigned_by=actor.id,
                assigned_at=now,
                due_at=now + timedelta(days=7),
                status="pending",
            )
            db.add(task)
            tasks_created.append(task)

        await db.commit()
        for task in tasks_created:
            await db.refresh(task)
        return tasks_created
    except Exception:
        await db.rollback()
        raise


# Evaluations
async def submit_evaluation(db: AsyncSession, current_user: User, task_id: str, indicator_id: str, score: float, comment: str | None = None):
    task = await get_evaluation_task(db, task_id)
    score = validate_score_value(score)
    evaluator_user_id = current_user.id

    if task.evaluator_user_id != evaluator_user_id:
        raise PermissionDeniedError("Only the assigned evaluator can submit this task")
    if task.status != "pending":
        raise _evaluation_conflict()
    if task.indicator_id != indicator_id:
        raise _invalid_evaluation("Evaluation indicator does not match the task")

    goal_result = await db.execute(
        select(Goal).where(
            Goal.id == task.goal_id,
            Goal.deleted_at.is_(None),
        )
    )
    goal = goal_result.scalar_one_or_none()
    if goal is None:
        raise AppException(404, "CHECK_010", "Evaluation goal not found")

    indicator_result = await db.execute(
        select(Indicator).where(
            Indicator.id == indicator_id,
            Indicator.deleted_at.is_(None),
        )
    )
    indicator = indicator_result.scalar_one_or_none()
    if indicator is None:
        raise AppException(404, "CHECK_011", "Evaluation indicator not found")
    if indicator.goal_id != goal.id:
        raise _invalid_evaluation("Evaluation indicator does not belong to the task goal")
    if indicator.redline:
        raise _invalid_evaluation("Redline indicators cannot be evaluated")

    query = select(SelfAssessment.id).where(
        SelfAssessment.goal_id == task.goal_id,
        SelfAssessment.status == "submitted",
        SelfAssessment.deleted_at.is_(None),
    ).limit(1)
    result = await db.execute(query)
    if result.scalar_one_or_none() is None:
        raise SelfAssessmentRequiredError()

    task_goal_id = task.goal_id
    await db.rollback()

    claim_result = await db.execute(
        update(EvaluationTask)
        .where(
            EvaluationTask.id == task_id,
            EvaluationTask.evaluator_user_id == evaluator_user_id,
            EvaluationTask.goal_id == task_goal_id,
            EvaluationTask.indicator_id == indicator_id,
            EvaluationTask.status == "pending",
            EvaluationTask.deleted_at.is_(None),
            exists(
                select(Goal.id).where(
                    Goal.id == task_goal_id,
                    Goal.deleted_at.is_(None),
                )
            ),
            exists(
                select(Indicator.id).where(
                    Indicator.id == indicator_id,
                    Indicator.goal_id == task_goal_id,
                    Indicator.redline.is_(False),
                    Indicator.deleted_at.is_(None),
                )
            ),
            exists(
                select(SelfAssessment.id).where(
                    SelfAssessment.goal_id == task_goal_id,
                    SelfAssessment.status == "submitted",
                    SelfAssessment.deleted_at.is_(None),
                )
            ),
            ~exists(
                select(Evaluation.id).where(
                    Evaluation.task_id == task_id,
                    Evaluation.deleted_at.is_(None),
                )
            ),
        )
        .values(status="completed")
    )
    if claim_result.rowcount != 1:
        await db.rollback()
        raise _evaluation_conflict()

    evaluation = Evaluation(
        task_id=task_id,
        goal_id=task_goal_id,
        indicator_id=indicator_id,
        evaluator_id=evaluator_user_id,
        score=score,
        comment=comment
    )
    db.add(evaluation)
    await db.commit()
    await db.refresh(evaluation)
    return evaluation


async def list_goal_evaluations(db: AsyncSession, current_user: User, goal_id: str):
    goal = await _get_active_goal(db, goal_id)
    await _assert_goal_access(db, current_user, goal)
    query = select(Evaluation).where(
        Evaluation.goal_id == goal_id,
        Evaluation.deleted_at.is_(None),
    ).order_by(Evaluation.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


# Final Results
def _validate_regular_indicator_weights(indicators: list[Indicator]) -> None:
    if not indicators:
        raise WeightValidationError("At least one non-redline indicator is required")

    weights = [indicator.weight for indicator in indicators]
    if any(
        weight is None
        or not math.isfinite(weight)
        or weight <= 0
        or weight > 1
        for weight in weights
    ):
        raise WeightValidationError(
            "Non-redline indicator weights must be finite values in (0, 1]"
        )

    total_weight = sum(weights)
    if not math.isclose(total_weight, 1.0, rel_tol=1e-9, abs_tol=1e-6):
        raise WeightValidationError(
            f"Non-redline indicator weight sum is {total_weight:g}, must be 1"
        )


def _stored_redline_count(actual_value: dict) -> int:
    if not isinstance(actual_value, dict) or "value" not in actual_value:
        raise AppException(422, "CHECK_013", "Stored redline check-in is invalid")
    if actual_value.get("value_type", "redline") != "redline":
        raise AppException(422, "CHECK_013", "Stored redline check-in is invalid")

    value = actual_value["value"]
    if isinstance(value, bool):
        raise AppException(422, "CHECK_013", "Stored redline check-in is invalid")
    if isinstance(value, int):
        count = value
    elif isinstance(value, float) and math.isfinite(value) and value.is_integer():
        count = int(value)
    else:
        raise AppException(422, "CHECK_013", "Stored redline check-in is invalid")
    if count < 0:
        raise AppException(422, "CHECK_013", "Stored redline check-in is invalid")
    return count


async def generate_final_result(db: AsyncSession, current_user: User, goal_id: str):
    from graphs.c_graph import run_c_stage
    from utils.calculations import calculate_c_stage

    goal = await _get_active_goal(db, goal_id)
    await _assert_goal_access(db, current_user, goal)

    query = select(Indicator).where(
        Indicator.goal_id == goal_id,
        Indicator.deleted_at.is_(None),
    )
    result = await db.execute(query)
    indicators = list(result.scalars().all())
    regular_indicators = [indicator for indicator in indicators if not indicator.redline]
    redline_indicators = [indicator for indicator in indicators if indicator.redline]
    _validate_regular_indicator_weights(regular_indicators)

    regular_ids = {indicator.id for indicator in regular_indicators}
    evaluation_result = await db.execute(
        select(Evaluation, EvaluationTask)
        .join(EvaluationTask, EvaluationTask.id == Evaluation.task_id)
        .where(
            Evaluation.goal_id == goal_id,
            Evaluation.indicator_id.in_(regular_ids),
            Evaluation.deleted_at.is_(None),
            EvaluationTask.goal_id == goal_id,
            EvaluationTask.indicator_id == Evaluation.indicator_id,
            EvaluationTask.evaluator_user_id == Evaluation.evaluator_id,
            EvaluationTask.status == "completed",
            EvaluationTask.deleted_at.is_(None),
        )
        .order_by(Evaluation.created_at.desc(), Evaluation.id.desc())
    )
    evaluations_by_indicator: dict[str, Evaluation] = {}
    for evaluation, _task in evaluation_result.all():
        if not math.isfinite(evaluation.score) or not 0 <= evaluation.score <= 100:
            continue
        evaluations_by_indicator.setdefault(evaluation.indicator_id, evaluation)

    missing_indicator_ids = regular_ids - evaluations_by_indicator.keys()
    if missing_indicator_ids:
        raise _final_result_incomplete(set(missing_indicator_ids))

    eval_scores = {
        indicator_id: evaluation.score
        for indicator_id, evaluation in evaluations_by_indicator.items()
    }

    redline_ids = {indicator.id for indicator in redline_indicators}
    latest_redline_checkins: dict[str, DataCheckin] = {}
    if redline_ids:
        redline_result = await db.execute(
            select(DataCheckin)
            .where(DataCheckin.indicator_id.in_(redline_ids))
            .order_by(
                DataCheckin.indicator_id,
                DataCheckin.submitted_at.desc(),
                DataCheckin.id.desc(),
            )
        )
        for checkin in redline_result.scalars().all():
            latest_redline_checkins.setdefault(checkin.indicator_id, checkin)

    redline_counts = {
        indicator.id: (
            _stored_redline_count(latest_redline_checkins[indicator.id].actual_value)
            if indicator.id in latest_redline_checkins
            else 0
        )
        for indicator in redline_indicators
    }
    redline_count = sum(redline_counts.values())
    redline_triggered = redline_count > 0

    indicator_results = []
    for ind in indicators:
        score = redline_counts.get(ind.id) if ind.redline else eval_scores[ind.id]
        indicator_results.append({
            "indicator_id": ind.id,
            "name": ind.name,
            "weight": ind.weight * 100,
            "score": score,
            "is_redline": ind.redline,
        })

    c_result = calculate_c_stage(
        indicator_results,
        eval_scores,
        redline_triggered,
        redline_count,
    )

    user_result = await db.execute(
        select(User).where(
            User.id == goal.owner_user_id,
            User.deleted_at.is_(None),
        )
    )
    user = user_result.scalar_one_or_none()
    position_name = user.full_name if user else "员工"

    supervisor_comments = [
        evaluation.comment
        for evaluation in evaluations_by_indicator.values()
        if evaluation.comment
    ]
    supervisor_comment = "; ".join(supervisor_comments) if supervisor_comments else "无"

    run_c_stage(
        indicator_results,
        eval_scores,
        supervisor_comment,
        redline_triggered,
        redline_count,
        position_name,
        "monthly"
    )

    score_agg_result = await db.execute(
        select(ScoreAggregate).where(
            ScoreAggregate.goal_id == goal_id,
            ScoreAggregate.deleted_at.is_(None),
        )
    )
    score_agg = score_agg_result.scalar_one_or_none()
    if score_agg:
        score_agg.final_score = c_result["total_score"]
        score_agg.breakdown = c_result
        score_agg.computed_at = datetime.now(timezone.utc)
    else:
        score_agg = ScoreAggregate(
            goal_id=goal_id,
            final_score=c_result["total_score"],
            breakdown=c_result,
            computed_at=datetime.now(timezone.utc)
        )
        db.add(score_agg)
        await db.flush()

    suggested_grade = c_result["grade"]

    final_result_result = await db.execute(
        select(FinalResult).where(
            FinalResult.goal_id == goal_id,
            FinalResult.deleted_at.is_(None),
        )
    )
    final_result = final_result_result.scalar_one_or_none()
    if final_result:
        final_result.computed_score_id = score_agg.id
        final_result.suggested_grade = suggested_grade
        final_result.final_grade = suggested_grade
        final_result.confirmed_by = current_user.id
        final_result.confirmed_at = datetime.now(timezone.utc)
        if final_result.status != "confirmed":
            final_result.status = "pending"
    else:
        final_result = FinalResult(
            goal_id=goal_id,
            computed_score_id=score_agg.id,
            suggested_grade=suggested_grade,
            final_grade=suggested_grade,
            confirmed_by=current_user.id,
            confirmed_at=datetime.now(timezone.utc),
            status="pending"
        )
        db.add(final_result)
    await db.commit()
    await db.refresh(final_result)
    return final_result


async def get_final_result_by_goal(db: AsyncSession, current_user: User, goal_id: str):
    goal = await _get_active_goal(db, goal_id)
    await _assert_goal_access(db, current_user, goal)
    query = select(FinalResult).where(
        FinalResult.goal_id == goal_id,
        FinalResult.deleted_at.is_(None),
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def confirm_final_result(db: AsyncSession, result_id: str, current_user: User):
    final_result = await db.get(FinalResult, result_id)
    if not final_result:
        raise FinalResultNotFoundError()
    goal = await _get_active_goal(db, final_result.goal_id)
    await _assert_goal_access(db, current_user, goal)
    final_result.status = "confirmed"
    final_result.confirmed_by = current_user.id
    final_result.confirmed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(final_result)
    return final_result


async def adjust_final_result(db: AsyncSession, result_id: str, final_grade: str, adjustment_reason: str, current_user: User):
    final_result = await db.get(FinalResult, result_id)
    if not final_result:
        raise FinalResultNotFoundError()
    goal = await _get_active_goal(db, final_result.goal_id)
    await _assert_goal_manager(db, current_user, goal)
    final_result.final_grade = final_grade
    final_result.adjustment_reason = adjustment_reason
    final_result.status = "adjusted"
    final_result.confirmed_by = current_user.id
    final_result.confirmed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(final_result)
    return final_result
