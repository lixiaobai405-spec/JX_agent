from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.check_phase import SelfAssessment, EvaluationTask, Evaluation, ScoreAggregate, FinalResult
from models.check_phase import Goal, Indicator
from models.user import User, UserRole
from core.exceptions import (
    SelfAssessmentNotFoundError,
    EvaluationTaskNotFoundError,
    SelfAssessmentRequiredError,
    SelfAssessmentAlreadySubmittedError,
    ScoreAggregateNotFoundError,
    FinalResultNotFoundError,
)


# Self Assessment
async def create_self_assessment(db: AsyncSession, current_user: User, goal_id: str, items: dict):
    assessment = SelfAssessment(
        goal_id=goal_id,
        user_id=current_user.id,
        items=items,
        status="draft"
    )
    db.add(assessment)
    await db.commit()
    await db.refresh(assessment)
    return assessment


async def get_self_assessment(db: AsyncSession, assessment_id: str):
    assessment = await db.get(SelfAssessment, assessment_id)
    if not assessment:
        raise SelfAssessmentNotFoundError()
    return assessment


async def update_self_assessment(db: AsyncSession, assessment_id: str, items: dict | None = None):
    assessment = await get_self_assessment(db, assessment_id)
    if assessment.status != "draft":
        raise SelfAssessmentAlreadySubmittedError()
    if items is not None:
        assessment.items = items
    await db.commit()
    await db.refresh(assessment)
    return assessment


async def submit_self_assessment(db: AsyncSession, assessment_id: str):
    assessment = await get_self_assessment(db, assessment_id)
    if assessment.status != "draft":
        raise SelfAssessmentAlreadySubmittedError()
    assessment.status = "submitted"
    assessment.submitted_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(assessment)
    return assessment


async def get_goal_self_assessment(db: AsyncSession, goal_id: str):
    query = select(SelfAssessment).where(SelfAssessment.goal_id == goal_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


# Evaluation Tasks
async def list_evaluation_tasks(db: AsyncSession, current_user: User, status: str | None = None):
    query = select(EvaluationTask).where(EvaluationTask.evaluator_user_id == current_user.id)
    if status:
        query = query.where(EvaluationTask.status == status)
    query = query.order_by(EvaluationTask.due_at)
    result = await db.execute(query)
    return result.scalars().all()


async def get_evaluation_task(db: AsyncSession, task_id: str):
    task = await db.get(EvaluationTask, task_id)
    if not task:
        raise EvaluationTaskNotFoundError()
    return task


async def get_my_pending_evaluation_tasks(db: AsyncSession, current_user: User):
    query = select(EvaluationTask).where(
        EvaluationTask.evaluator_user_id == current_user.id,
        EvaluationTask.status == "pending"
    ).order_by(EvaluationTask.due_at)
    result = await db.execute(query)
    return result.scalars().all()


async def generate_evaluation_tasks(db: AsyncSession, current_user: User, goal_id: str):
    from datetime import timedelta
    from models.period import Period

    goal = await db.get(Goal, goal_id)
    if not goal:
        return []

    # 检查D阶段是否完成
    period = await db.get(Period, goal.period_id)
    if not period or not period.d_phase_completed:
        from core.exceptions import PermissionDeniedError
        raise PermissionDeniedError("D phase must be completed before starting C phase evaluation")

    user = await db.get(User, goal.owner_user_id)
    if not user:
        return []

    # 确定评价者：如果当前用户是 admin，分配给当前用户；否则分配给员工的经理
    is_admin = current_user.role in (UserRole.hr_admin, UserRole.system_admin)
    evaluator_id = current_user.id if is_admin else user.manager_id

    if not evaluator_id:
        return []

    query = select(Indicator).where(Indicator.goal_id == goal_id)
    result = await db.execute(query)
    indicators = result.scalars().all()

    # 过滤红线指标，红线指标不进入评价阶段
    indicators = [i for i in indicators if not i.redline]

    tasks_created = []
    for indicator in indicators:
        task = EvaluationTask(
            goal_id=goal_id,
            indicator_id=indicator.id,
            evaluator_user_id=evaluator_id,
            assigned_by=current_user.id,
            assigned_at=datetime.now(timezone.utc),
            due_at=datetime.now(timezone.utc) + timedelta(days=7),
            status="pending"
        )
        db.add(task)
        tasks_created.append(task)

    await db.commit()
    for task in tasks_created:
        await db.refresh(task)

    return tasks_created


# Evaluations
async def submit_evaluation(db: AsyncSession, current_user: User, task_id: str, indicator_id: str, score: float, comment: str | None = None):
    task = await get_evaluation_task(db, task_id)

    query = select(SelfAssessment).where(SelfAssessment.goal_id == task.goal_id)
    result = await db.execute(query)
    self_assessment = result.scalar_one_or_none()
    if not self_assessment or self_assessment.status != "submitted":
        raise SelfAssessmentRequiredError()

    evaluation = Evaluation(
        task_id=task_id,
        goal_id=task.goal_id,
        indicator_id=indicator_id,
        evaluator_id=current_user.id,
        score=score,
        comment=comment
    )
    db.add(evaluation)
    task.status = "completed"
    await db.commit()
    await db.refresh(evaluation)
    return evaluation


async def list_goal_evaluations(db: AsyncSession, goal_id: str):
    query = select(Evaluation).where(Evaluation.goal_id == goal_id).order_by(Evaluation.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


# Final Results
async def generate_final_result(db: AsyncSession, current_user: User, goal_id: str):
    from graphs.c_graph import run_c_stage
    from utils.calculations import calculate_c_stage

    goal = await db.get(Goal, goal_id)
    query = select(Indicator).where(Indicator.goal_id == goal_id)
    result = await db.execute(query)
    indicators = result.scalars().all()

    query = select(Evaluation).where(Evaluation.goal_id == goal_id)
    result = await db.execute(query)
    evaluations = result.scalars().all()

    eval_scores = {}
    for ev in evaluations:
        ind = next((i for i in indicators if i.id == ev.indicator_id), None)
        if ind:
            eval_scores[ind.name] = ev.score

    indicator_results = []
    redline_triggered = False
    redline_count = 0
    for ind in indicators:
        score = eval_scores.get(ind.name, 0)
        indicator_results.append({
            "name": ind.name,
            "weight": ind.weight * 100,
            "score": score,
            "is_redline": ind.redline
        })
        if ind.redline and score < ind.target_value:
            redline_triggered = True
            redline_count += 1

    c_result = calculate_c_stage(
        [{"name": i.name, "weight": i.weight * 100} for i in indicators],
        eval_scores
    )

    user = await db.get(User, goal.owner_user_id)
    position_name = user.full_name if user else "员工"

    supervisor_comments = [ev.comment for ev in evaluations if ev.comment]
    supervisor_comment = "; ".join(supervisor_comments) if supervisor_comments else "无"

    ai_report = run_c_stage(
        indicator_results,
        eval_scores,
        supervisor_comment,
        redline_triggered,
        redline_count,
        position_name,
        "monthly"
    )

    score_agg = ScoreAggregate(
        goal_id=goal_id,
        final_score=c_result["total_score"],
        breakdown=c_result,
        computed_at=datetime.now(timezone.utc)
    )
    db.add(score_agg)
    await db.flush()

    suggested_grade = c_result.get("grade", "C")

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


async def get_final_result_by_goal(db: AsyncSession, goal_id: str):
    query = select(FinalResult).where(FinalResult.goal_id == goal_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def confirm_final_result(db: AsyncSession, result_id: str, current_user: User):
    final_result = await db.get(FinalResult, result_id)
    if not final_result:
        raise FinalResultNotFoundError()
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
    final_result.final_grade = final_grade
    final_result.adjustment_reason = adjustment_reason
    final_result.status = "adjusted"
    final_result.confirmed_by = current_user.id
    final_result.confirmed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(final_result)
    return final_result


