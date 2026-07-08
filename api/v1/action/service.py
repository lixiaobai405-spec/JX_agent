from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.action_phase import ReviewReport, DevelopmentPlan, InheritanceSuggestion
from models.check_phase import FinalResult, ScoreAggregate, Goal, Indicator, Evaluation
from models.user import User
from core.exceptions import (
    ReviewReportNotFoundError,
    DevelopmentPlanNotFoundError,
    PlanAlreadySubmittedError,
    InheritanceSuggestionNotFoundError,
    FinalResultNotFoundError,
)
from graphs.a_graph import run_a_stage, review_plan


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


# Review Report Service
async def generate_review_report(db: AsyncSession, current_user: User, final_result_id: str):
    final_result = await db.get(FinalResult, final_result_id)
    if not final_result:
        raise FinalResultNotFoundError()

    # 检查是否已存在报告
    query = select(ReviewReport).where(ReviewReport.final_result_id == final_result_id)
    result = await db.execute(query)
    existing_report = result.scalar_one_or_none()
    if existing_report:
        return existing_report

    score_agg = await db.get(ScoreAggregate, final_result.computed_score_id)
    goal = await db.get(Goal, final_result.goal_id)

    query = select(Indicator).where(Indicator.goal_id == goal.id)
    result = await db.execute(query)
    indicators = result.scalars().all()

    query = select(Evaluation).where(Evaluation.goal_id == goal.id)
    result = await db.execute(query)
    evaluations = result.scalars().all()

    eval_scores = {}
    for ev in evaluations:
        ind = next((i for i in indicators if i.id == ev.indicator_id), None)
        if ind:
            eval_scores[ind.name] = ev.score

    indicator_scores = []
    for ind in indicators:
        score = eval_scores.get(ind.name, 0)
        indicator_scores.append({
            "name": ind.name,
            "weight": ind.weight * 100,
            "score": score,
            "weighted_score": score * ind.weight
        })

    user = await db.get(User, goal.owner_user_id)

    total_score = score_agg.final_score
    development_suggestions = {}
    ai_generated = True
    try:
        ai_result = run_a_stage(
            grade=final_result.final_grade,
            total_score=total_score,
            indicator_scores=indicator_scores,
            position_name=user.full_name if user else "员工",
            assessment_period="monthly"
        )
        strengths = [{"indicator": s.indicator, "score": s.score, "comment": s.comment}
                     for s in ai_result.strengths]
        improvements = [{"indicator": d.indicator, "score": d.score, "suggestion": d.suggestion}
                        for d in ai_result.development_areas]
        summary = ai_result.overall_summary
    except Exception as exc:
        summary, strengths, improvements = _build_fallback_review_sections(
            final_result.final_grade,
            total_score,
            indicator_scores,
        )
        ai_generated = False
        development_suggestions = {
            "fallback": True,
            "fallback_source": "backend_review_report_fallback",
            "fallback_error_type": type(exc).__name__,
            "fallback_reason": str(exc),
        }

    report_type = "s_a" if final_result.final_grade in ["S", "A"] else final_result.final_grade.lower()

    review_report = ReviewReport(
        final_result_id=final_result_id,
        user_id=goal.owner_user_id,
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


async def get_review_report(db: AsyncSession, report_id: str):
    report = await db.get(ReviewReport, report_id)
    if not report:
        raise ReviewReportNotFoundError()
    return report


async def submit_user_feedback(db: AsyncSession, report_id: str, user_feedback: str):
    report = await get_review_report(db, report_id)
    report.user_feedback = user_feedback
    report.reviewed_by_user = True
    await db.commit()
    await db.refresh(report)
    return report


async def get_user_period_report(db: AsyncSession, user_id: str, period_id: str):
    query = select(ReviewReport).join(FinalResult).join(Goal).where(
        Goal.owner_user_id == user_id,
        Goal.period_id == period_id
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


# Development Plan Service
async def create_development_plan(db: AsyncSession, current_user: User, review_report_id: str, goals: dict, actions: dict, required_resources: dict | None = None, timeline: dict | None = None):
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


async def get_development_plan(db: AsyncSession, plan_id: str):
    plan = await db.get(DevelopmentPlan, plan_id)
    if not plan:
        raise DevelopmentPlanNotFoundError()
    return plan


async def update_development_plan(db: AsyncSession, plan_id: str, data: dict):
    plan = await get_development_plan(db, plan_id)
    if plan.status != "draft":
        raise PlanAlreadySubmittedError()
    for field in ("goals", "actions", "required_resources", "timeline"):
        if field in data:
            setattr(plan, field, data[field])
    await db.commit()
    await db.refresh(plan)
    return plan


async def ai_review_plan(db: AsyncSession, plan_id: str, feedback: str | None = None):
    plan = await get_development_plan(db, plan_id)

    review_report = await db.get(ReviewReport, plan.review_report_id)
    if not review_report:
        raise ReviewReportNotFoundError()

    final_result = await db.get(FinalResult, review_report.final_result_id)

    development_areas = review_report.improvement_areas.get("areas", []) if review_report.improvement_areas else []

    review_result = review_plan(
        grade=final_result.final_grade,
        development_areas=development_areas,
        plan_goal=plan.goals.get("text", "") if isinstance(plan.goals, dict) else str(plan.goals),
        plan_actions=plan.actions.get("text", "") if isinstance(plan.actions, dict) else str(plan.actions),
        plan_resources=str(plan.required_resources) if plan.required_resources else "",
        plan_timeline=str(plan.timeline) if plan.timeline else "",
        feedback=feedback
    )

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


async def submit_plan(db: AsyncSession, plan_id: str):
    plan = await get_development_plan(db, plan_id)
    if plan.status != "draft":
        raise PlanAlreadySubmittedError()
    plan.status = "reviewed"
    await db.commit()
    await db.refresh(plan)
    return plan


async def approve_plan(db: AsyncSession, plan_id: str, current_user: User, approved: bool, comment: str | None = None):
    plan = await get_development_plan(db, plan_id)
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
    query = select(DevelopmentPlan).where(DevelopmentPlan.user_id == current_user.id).order_by(DevelopmentPlan.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


async def list_team_plans(db: AsyncSession, current_user: User):
    from models.user import UserRole
    if current_user.role in (UserRole.hr_admin, UserRole.system_admin):
        query = select(DevelopmentPlan).order_by(DevelopmentPlan.created_at.desc())
    else:
        query = select(DevelopmentPlan).join(User, DevelopmentPlan.user_id == User.id).where(User.manager_id == current_user.id).order_by(DevelopmentPlan.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


# Inheritance Suggestion Service
async def generate_inheritance_suggestions(db: AsyncSession, current_user: User, user_id: str, from_period_id: str, to_period_id: str):
    query = select(DevelopmentPlan).join(ReviewReport).join(FinalResult).join(Goal).where(
        DevelopmentPlan.user_id == user_id,
        Goal.period_id == from_period_id,
        DevelopmentPlan.status == "approved"
    ).order_by(DevelopmentPlan.created_at.desc())
    result = await db.execute(query)
    dev_plan = result.scalar_one_or_none()

    if not dev_plan:
        return []

    query = select(FinalResult).join(Goal).where(
        Goal.owner_user_id == user_id,
        Goal.period_id == from_period_id
    )
    result = await db.execute(query)
    final_result = result.scalar_one_or_none()

    if not final_result:
        return []

    suggestions_data = {
        "suggestion_type": "new_indicator",
        "recommendations": []
    }

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


async def get_inheritance_suggestion(db: AsyncSession, suggestion_id: str):
    suggestion = await db.get(InheritanceSuggestion, suggestion_id)
    if not suggestion:
        raise InheritanceSuggestionNotFoundError()
    return suggestion


async def accept_suggestion(db: AsyncSession, suggestion_id: str):
    suggestion = await get_inheritance_suggestion(db, suggestion_id)
    suggestion.status = "accepted"
    suggestion.accepted_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(suggestion)
    return suggestion


async def reject_suggestion(db: AsyncSession, suggestion_id: str, reason: str):
    suggestion = await get_inheritance_suggestion(db, suggestion_id)
    suggestion.status = "rejected"
    suggestion.rejected_reason = reason
    await db.commit()
    await db.refresh(suggestion)
    return suggestion


async def get_user_period_suggestions(db: AsyncSession, user_id: str, period_id: str):
    query = select(InheritanceSuggestion).where(
        InheritanceSuggestion.user_id == user_id,
        InheritanceSuggestion.new_period_id == period_id
    ).order_by(InheritanceSuggestion.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()
