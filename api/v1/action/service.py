from datetime import datetime, timezone
import logging
import math
import time

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from models.action_phase import ReviewReport, DevelopmentPlan, InheritanceSuggestion
from models.check_phase import (
    Evaluation,
    EvaluationTask,
    EvaluationTaskStatus,
    FinalResult,
    Goal,
    Indicator,
    ScoreAggregate,
)
from models.period import Period
from models.plan_phase import AIGenerationLog
from models.user import User, UserRole, UserStatus
from core.exceptions import (
    ReviewReportNotFoundError,
    DevelopmentPlanNotFoundError,
    PlanAlreadySubmittedError,
    InheritanceSuggestionNotFoundError,
    FinalResultNotFoundError,
    PermissionDeniedError,
    ScoreAggregateNotFoundError,
    UserNotFoundError,
)
from graphs.a_graph import run_a_stage, review_plan


logger = logging.getLogger(__name__)
_ADMIN_ROLES = (UserRole.hr_admin, UserRole.system_admin)


async def _get_subordinate_ids(db: AsyncSession, manager_id: str) -> list[str]:
    direct_reports = (
        select(User.id.label("id"))
        .where(
            User.manager_id == manager_id,
            User.status == UserStatus.active,
            User.deleted_at.is_(None),
        )
        .cte("action_subordinate_ids", recursive=True)
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


async def _assert_user_access(
    db: AsyncSession,
    current_user: User,
    target_user_id: str,
) -> None:
    target_result = await db.execute(
        select(User.id).where(
            User.id == target_user_id,
            User.status == UserStatus.active,
            User.deleted_at.is_(None),
        )
    )
    if target_result.scalar_one_or_none() is None:
        raise UserNotFoundError()

    if current_user.id == target_user_id or current_user.role in _ADMIN_ROLES:
        return
    if current_user.role == UserRole.manager:
        subordinate_ids = await _get_subordinate_ids(db, current_user.id)
        if target_user_id in subordinate_ids:
            return
    raise PermissionDeniedError("Cannot access this user's action data")


def _assert_owner(current_user: User, owner_user_id: str) -> None:
    if current_user.id != owner_user_id:
        raise PermissionDeniedError("Only the owner can change this action data")


async def _assert_manager_access(
    db: AsyncSession,
    current_user: User,
    target_user_id: str,
) -> None:
    if current_user.role in _ADMIN_ROLES:
        await _assert_user_access(db, current_user, target_user_id)
        return
    if current_user.role == UserRole.manager:
        subordinate_ids = await _get_subordinate_ids(db, current_user.id)
        if target_user_id in subordinate_ids:
            return
    raise PermissionDeniedError("Only the assigned management chain can approve this plan")


def _execution_time_ms(started_at: float) -> int:
    return max(0, int((time.perf_counter() - started_at) * 1000))


async def _write_action_ai_failure_log(
    db: AsyncSession,
    *,
    job_type: str,
    user_id: str,
    error: Exception,
    started_at: float,
) -> None:
    bind = db.bind
    await db.rollback()

    if isinstance(bind, AsyncEngine):
        session_factory = async_sessionmaker(
            bind,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    else:
        from core.database import AsyncSessionLocal

        session_factory = AsyncSessionLocal

    try:
        async with session_factory() as log_db:
            log_db.add(
                AIGenerationLog(
                    job_type=job_type,
                    user_id=user_id,
                    job_analysis_id=None,
                    model_used="deepseek-chat",
                    success=False,
                    error_message=str(error),
                    execution_time_ms=_execution_time_ms(started_at),
                )
            )
            await log_db.commit()
    except Exception:
        logger.exception("Failed to persist action-stage AI failure log")


def _format_score(value: float | int | None) -> str:
    if value is None:
        return "0"
    return f"{value:g}"


def _build_fallback_review_sections(
    grade: str,
    total_score: float,
    indicator_scores: list[dict],
) -> tuple[str, list[dict], list[dict]]:
    summary = (
        f"本期综合得分为{_format_score(total_score)}分，考核等级为{grade}级。"
        "AI 复盘报告暂时不可用，系统已根据指标得分生成基础复盘，建议结合上级反馈补充具体原因和行动计划。"
    )

    strengths = [
        {
            "indicator": item["name"],
            "score": item["score"],
            "comment": f"该指标得分{_format_score(item['score'])}分，表现相对稳定，建议继续保持并沉淀有效做法。",
        }
        for item in indicator_scores
        if item.get("score", 0) >= 80
    ]

    if not strengths and indicator_scores:
        best_item = max(indicator_scores, key=lambda item: item.get("score", 0))
        strengths.append(
            {
                "indicator": best_item["name"],
                "score": best_item["score"],
                "comment": (
                    f"该指标得分{_format_score(best_item['score'])}分，"
                    "在当前指标中表现相对较好，可作为后续提升的基础。"
                ),
            }
        )

    improvements = [
        {
            "indicator": item["name"],
            "score": item["score"],
            "suggestion": (
                f"该指标得分{_format_score(item['score'])}分，建议复盘目标差距，"
                "明确下周期责任动作、资源支持和跟进节点。"
            ),
        }
        for item in indicator_scores
        if item.get("score", 0) < 80
    ]

    return summary, strengths, improvements


def _aggregate_scores_by_indicator(score_agg: ScoreAggregate) -> dict[str, float]:
    breakdown = score_agg.breakdown if isinstance(score_agg.breakdown, dict) else {}
    items = breakdown.get("indicator_scores")
    if not isinstance(items, list):
        return {}

    scores: dict[str, float] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        indicator_id = item.get("indicator_id")
        try:
            score = float(item.get("score"))
        except (TypeError, ValueError):
            continue
        if (
            isinstance(indicator_id, str)
            and indicator_id
            and indicator_id not in scores
            and math.isfinite(score)
            and 0 <= score <= 100
        ):
            scores[indicator_id] = score
    return scores


async def _legacy_evaluation_scores(
    db: AsyncSession,
    goal_id: str,
    indicator_ids: set[str],
) -> dict[str, float]:
    if not indicator_ids:
        return {}

    result = await db.execute(
        select(Evaluation)
        .join(
            EvaluationTask,
            and_(
                EvaluationTask.id == Evaluation.task_id,
                EvaluationTask.goal_id == Evaluation.goal_id,
            ),
        )
        .where(
            Evaluation.goal_id == goal_id,
            Evaluation.indicator_id.in_(indicator_ids),
            Evaluation.deleted_at.is_(None),
            EvaluationTask.status == EvaluationTaskStatus.completed,
            EvaluationTask.deleted_at.is_(None),
            or_(
                EvaluationTask.indicator_id.is_(None),
                EvaluationTask.indicator_id == Evaluation.indicator_id,
            ),
        )
        .order_by(Evaluation.created_at.desc(), Evaluation.id.desc())
    )
    scores: dict[str, float] = {}
    for evaluation in result.scalars().all():
        try:
            score = float(evaluation.score)
        except (TypeError, ValueError):
            continue
        if (
            evaluation.indicator_id not in scores
            and math.isfinite(score)
            and 0 <= score <= 100
        ):
            scores[evaluation.indicator_id] = score
    return scores


# Review Report Service
async def generate_review_report(db: AsyncSession, current_user: User, final_result_id: str):
    final_result_result = await db.execute(
        select(FinalResult).where(
            FinalResult.id == final_result_id,
            FinalResult.deleted_at.is_(None),
        )
    )
    final_result = final_result_result.scalar_one_or_none()
    if not final_result:
        raise FinalResultNotFoundError()

    goal_result = await db.execute(
        select(Goal).where(
            Goal.id == final_result.goal_id,
            Goal.deleted_at.is_(None),
        )
    )
    goal = goal_result.scalar_one_or_none()
    if not goal:
        raise FinalResultNotFoundError()
    await _assert_user_access(db, current_user, goal.owner_user_id)

    # 检查是否已存在报告
    query = select(ReviewReport).where(
        ReviewReport.final_result_id == final_result_id,
        ReviewReport.deleted_at.is_(None),
    )
    result = await db.execute(query)
    existing_report = result.scalar_one_or_none()
    if existing_report:
        return existing_report

    score_agg_result = await db.execute(
        select(ScoreAggregate).where(
            ScoreAggregate.id == final_result.computed_score_id,
            ScoreAggregate.deleted_at.is_(None),
        )
    )
    score_agg = score_agg_result.scalar_one_or_none()
    if score_agg is None:
        raise ScoreAggregateNotFoundError()

    query = select(Indicator).where(
        Indicator.goal_id == goal.id,
        Indicator.deleted_at.is_(None),
        Indicator.redline.is_(False),
    )
    result = await db.execute(query)
    indicators = list(result.scalars().all())

    scores_by_indicator = _aggregate_scores_by_indicator(score_agg)
    regular_indicator_ids = {indicator.id for indicator in indicators}
    missing_ids = regular_indicator_ids - scores_by_indicator.keys()
    scores_by_indicator.update(
        await _legacy_evaluation_scores(db, goal.id, missing_ids)
    )
    indicator_scores = [
        {
            "indicator_id": indicator.id,
            "name": indicator.name,
            "weight": indicator.weight * 100,
            "score": scores_by_indicator[indicator.id],
            "weighted_score": scores_by_indicator[indicator.id] * indicator.weight,
        }
        for indicator in indicators
        if indicator.id in scores_by_indicator
    ]

    user = await db.get(User, goal.owner_user_id)
    owner_user_id = goal.owner_user_id
    grade = final_result.final_grade
    total_score = score_agg.final_score
    position_name = user.full_name if user else "员工"
    report_type = "s_a" if grade in ["S", "A"] else grade.lower()
    development_suggestions = {}
    ai_generated = True
    started_at = time.perf_counter()
    try:
        ai_result = await run_a_stage(
            grade=grade,
            total_score=total_score,
            indicator_scores=indicator_scores,
            position_name=position_name,
            assessment_period="monthly"
        )
        strengths = [{"indicator": s.indicator, "score": s.score, "comment": s.comment}
                     for s in ai_result.strengths]
        improvements = [{"indicator": d.indicator, "score": d.score, "suggestion": d.suggestion}
                        for d in ai_result.development_areas]
        summary = ai_result.overall_summary
    except Exception as exc:
        await _write_action_ai_failure_log(
            db,
            job_type="review_report",
            user_id=owner_user_id,
            error=exc,
            started_at=started_at,
        )
        summary, strengths, improvements = _build_fallback_review_sections(
            grade,
            total_score,
            indicator_scores,
        )
        ai_generated = False
        development_suggestions = {
            "fallback": True,
            "fallback_source": "backend_review_report_fallback",
            "fallback_reason": "AI generation unavailable; deterministic review generated",
        }

    review_report = ReviewReport(
        final_result_id=final_result_id,
        user_id=owner_user_id,
        report_type=report_type,
        strengths_analysis={"strengths": strengths, "summary": summary},
        improvement_areas={"areas": improvements},
        development_suggestions=development_suggestions,
        ai_generated=ai_generated,
        generated_at=datetime.now(timezone.utc)
    )
    db.add(review_report)
    await db.commit()
    await db.refresh(review_report)
    return review_report


async def get_review_report(
    db: AsyncSession,
    current_user: User,
    report_id: str,
):
    result = await db.execute(
        select(ReviewReport).where(
            ReviewReport.id == report_id,
            ReviewReport.deleted_at.is_(None),
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise ReviewReportNotFoundError()
    await _assert_user_access(db, current_user, report.user_id)
    return report


async def submit_user_feedback(
    db: AsyncSession,
    current_user: User,
    report_id: str,
    user_feedback: str,
):
    report = await get_review_report(db, current_user, report_id)
    _assert_owner(current_user, report.user_id)
    report.user_feedback = user_feedback
    report.reviewed_by_user = True
    await db.commit()
    await db.refresh(report)
    return report


async def get_user_period_report(
    db: AsyncSession,
    current_user: User,
    user_id: str,
    period_id: str,
):
    await _assert_user_access(db, current_user, user_id)
    query = select(ReviewReport).join(FinalResult).join(Goal).where(
        Goal.owner_user_id == user_id,
        Goal.period_id == period_id,
        Goal.deleted_at.is_(None),
        FinalResult.deleted_at.is_(None),
        ReviewReport.deleted_at.is_(None),
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


# Development Plan Service
async def create_development_plan(db: AsyncSession, current_user: User, review_report_id: str, goals: dict, actions: dict, required_resources: dict | None = None, timeline: dict | None = None):
    report_result = await db.execute(
        select(ReviewReport).where(
            ReviewReport.id == review_report_id,
            ReviewReport.deleted_at.is_(None),
        )
    )
    report = report_result.scalar_one_or_none()
    if report is None:
        raise ReviewReportNotFoundError()
    _assert_owner(current_user, report.user_id)

    plan = DevelopmentPlan(
        review_report_id=review_report_id,
        user_id=current_user.id,
        goals=goals,
        actions=actions,
        required_resources=required_resources,
        timeline=timeline,
        status="draft"
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


async def _get_development_plan_record(
    db: AsyncSession,
    plan_id: str,
) -> DevelopmentPlan:
    result = await db.execute(
        select(DevelopmentPlan).where(
            DevelopmentPlan.id == plan_id,
            DevelopmentPlan.deleted_at.is_(None),
        )
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise DevelopmentPlanNotFoundError()
    return plan


async def get_development_plan(
    db: AsyncSession,
    current_user: User,
    plan_id: str,
):
    plan = await _get_development_plan_record(db, plan_id)
    await _assert_user_access(db, current_user, plan.user_id)
    return plan


async def update_development_plan(
    db: AsyncSession,
    current_user: User,
    plan_id: str,
    data: dict,
):
    plan = await _get_development_plan_record(db, plan_id)
    _assert_owner(current_user, plan.user_id)
    if plan.status != "draft":
        raise PlanAlreadySubmittedError()
    for field in ("goals", "actions", "required_resources", "timeline"):
        if field in data:
            setattr(plan, field, data[field])
    await db.commit()
    await db.refresh(plan)
    return plan


async def ai_review_plan(
    db: AsyncSession,
    current_user: User,
    plan_id: str,
    feedback: str | None = None,
):
    plan = await _get_development_plan_record(db, plan_id)
    _assert_owner(current_user, plan.user_id)
    if plan.status != "draft":
        raise PlanAlreadySubmittedError()

    review_report = await db.get(ReviewReport, plan.review_report_id)
    if not review_report:
        raise ReviewReportNotFoundError()

    final_result = await db.get(FinalResult, review_report.final_result_id)

    development_areas = review_report.improvement_areas.get("areas", []) if review_report.improvement_areas else []

    started_at = time.perf_counter()
    try:
        review_result = await review_plan(
            grade=final_result.final_grade,
            development_areas=development_areas,
            plan_goal=plan.goals.get("text", "") if isinstance(plan.goals, dict) else str(plan.goals),
            plan_actions=plan.actions.get("text", "") if isinstance(plan.actions, dict) else str(plan.actions),
            plan_resources=str(plan.required_resources) if plan.required_resources else "",
            plan_timeline=str(plan.timeline) if plan.timeline else "",
            feedback=feedback
        )
    except Exception as exc:
        from core.exceptions import AppException

        await _write_action_ai_failure_log(
            db,
            job_type="action_review",
            user_id=plan.user_id,
            error=exc,
            started_at=started_at,
        )
        raise AppException(
            502,
            "ACTION_AI_REVIEW_FAILED",
            "AI review failed; please retry later",
        ) from exc

    # 保存结构化结果
    plan.smart_evaluation = review_result.get("smart_evaluation")
    plan.ai_suggestions = {
        "polished_goals": review_result.get("polished_goals"),
        "polished_actions": review_result.get("polished_actions"),
        "overall_review": review_result.get("overall_review")
    }
    plan.ai_reviewed = True
    await db.commit()
    await db.refresh(plan)
    return plan


async def submit_plan(db: AsyncSession, current_user: User, plan_id: str):
    plan = await _get_development_plan_record(db, plan_id)
    _assert_owner(current_user, plan.user_id)
    if plan.status != "draft":
        raise PlanAlreadySubmittedError()
    plan.status = "reviewed"
    await db.commit()
    await db.refresh(plan)
    return plan


async def approve_plan(db: AsyncSession, current_user: User, plan_id: str, approved: bool, comment: str | None = None):
    plan = await _get_development_plan_record(db, plan_id)
    await _assert_manager_access(db, current_user, plan.user_id)
    plan.status = "approved" if approved else "draft"
    plan.approved_by = current_user.id
    plan.approved_at = datetime.now(timezone.utc)
    if not approved and comment:
        plan.carry_forward_reason = comment
    elif approved:
        plan.carry_forward_reason = None
    await db.commit()
    await db.refresh(plan)
    return plan


async def list_my_plans(db: AsyncSession, current_user: User):
    query = select(DevelopmentPlan).where(
        DevelopmentPlan.user_id == current_user.id,
        DevelopmentPlan.deleted_at.is_(None),
    ).order_by(DevelopmentPlan.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


async def list_team_plans(db: AsyncSession, current_user: User):
    if current_user.role in _ADMIN_ROLES:
        query = select(DevelopmentPlan).where(
            DevelopmentPlan.deleted_at.is_(None),
        ).order_by(DevelopmentPlan.created_at.desc())
    elif current_user.role == UserRole.manager:
        subordinate_ids = await _get_subordinate_ids(db, current_user.id)
        query = select(DevelopmentPlan).where(
            DevelopmentPlan.user_id.in_(subordinate_ids),
            DevelopmentPlan.deleted_at.is_(None),
        ).order_by(DevelopmentPlan.created_at.desc())
    else:
        return []
    result = await db.execute(query)
    return result.scalars().all()


# Inheritance Suggestion Service
def _dict_text(value: dict | str | None) -> str:
    if not value:
        return ""
    if isinstance(value, str):
        return value
    text = value.get("text")
    return text if isinstance(text, str) else ""


def _short_text(value: str, fallback: str, max_len: int = 24) -> str:
    text = " ".join(value.split())
    if not text:
        return fallback
    return text if len(text) <= max_len else f"{text[:max_len]}..."


def _build_inheritance_suggestions(dev_plan: DevelopmentPlan) -> dict:
    goal_text = _dict_text(dev_plan.goals)
    action_text = _dict_text(dev_plan.actions)
    focus = _short_text(goal_text, "本期 IDP 改进项")

    return {
        "summary": f"建议将「{focus}」延续为下周期发展目标，并设置过程完成度指标跟踪落地。",
        "recommendations": [
            {
                "name": f"{focus}完成度",
                "definition": "跟踪本期 IDP 改进动作在下周期的落地比例和里程碑完成情况",
                "target_display": "100%",
                "reason": "承接本期复盘和 IDP，确保改进项进入下周期正式跟踪。",
                "source_goal": goal_text,
                "source_actions": action_text,
            }
        ],
    }


async def generate_inheritance_suggestions(db: AsyncSession, current_user: User, user_id: str, from_period_id: str, to_period_id: str):
    await _assert_user_access(db, current_user, user_id)
    target_period_result = await db.execute(
        select(Period.id).where(
            Period.id == to_period_id,
            Period.user_id == user_id,
            Period.deleted_at.is_(None),
        )
    )
    if target_period_result.scalar_one_or_none() is None:
        raise InheritanceSuggestionNotFoundError()

    query = select(DevelopmentPlan).join(ReviewReport).join(FinalResult).join(Goal).where(
        DevelopmentPlan.user_id == user_id,
        Goal.period_id == from_period_id,
        DevelopmentPlan.status == "approved",
        DevelopmentPlan.deleted_at.is_(None),
        ReviewReport.deleted_at.is_(None),
        FinalResult.deleted_at.is_(None),
        Goal.deleted_at.is_(None),
    ).order_by(DevelopmentPlan.created_at.desc()).limit(1)
    result = await db.execute(query)
    dev_plan = result.scalar_one_or_none()

    if not dev_plan:
        raise InheritanceSuggestionNotFoundError()

    query = select(FinalResult).join(Goal).where(
        Goal.owner_user_id == user_id,
        Goal.period_id == from_period_id,
        Goal.deleted_at.is_(None),
        FinalResult.deleted_at.is_(None),
    )
    result = await db.execute(query)
    final_result = result.scalar_one_or_none()

    if not final_result:
        raise InheritanceSuggestionNotFoundError()

    suggestions_data = _build_inheritance_suggestions(dev_plan)

    suggestion = InheritanceSuggestion(
        user_id=user_id,
        previous_development_plan_id=dev_plan.id,
        previous_final_result_id=final_result.id,
        new_period_id=to_period_id,
        suggestion_type="new_indicator",
        suggestions=suggestions_data,
        status="pending"
    )
    db.add(suggestion)
    await db.commit()
    await db.refresh(suggestion)
    return suggestion


async def _get_inheritance_suggestion_record(
    db: AsyncSession,
    suggestion_id: str,
) -> InheritanceSuggestion:
    result = await db.execute(
        select(InheritanceSuggestion).where(
            InheritanceSuggestion.id == suggestion_id,
            InheritanceSuggestion.deleted_at.is_(None),
        )
    )
    suggestion = result.scalar_one_or_none()
    if not suggestion:
        raise InheritanceSuggestionNotFoundError()
    return suggestion


async def get_inheritance_suggestion(
    db: AsyncSession,
    current_user: User,
    suggestion_id: str,
):
    suggestion = await _get_inheritance_suggestion_record(db, suggestion_id)
    await _assert_user_access(db, current_user, suggestion.user_id)
    return suggestion


async def accept_suggestion(
    db: AsyncSession,
    current_user: User,
    suggestion_id: str,
):
    suggestion = await _get_inheritance_suggestion_record(db, suggestion_id)
    _assert_owner(current_user, suggestion.user_id)
    suggestion.status = "accepted"
    suggestion.accepted_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(suggestion)
    return suggestion


async def reject_suggestion(
    db: AsyncSession,
    current_user: User,
    suggestion_id: str,
    reason: str,
):
    suggestion = await _get_inheritance_suggestion_record(db, suggestion_id)
    _assert_owner(current_user, suggestion.user_id)
    suggestion.status = "rejected"
    suggestion.rejected_reason = reason
    await db.commit()
    await db.refresh(suggestion)
    return suggestion


async def get_user_period_suggestions(
    db: AsyncSession,
    current_user: User,
    user_id: str,
    period_id: str,
):
    await _assert_user_access(db, current_user, user_id)
    query = select(InheritanceSuggestion).where(
        InheritanceSuggestion.user_id == user_id,
        InheritanceSuggestion.new_period_id == period_id,
        InheritanceSuggestion.deleted_at.is_(None),
    ).order_by(InheritanceSuggestion.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()
