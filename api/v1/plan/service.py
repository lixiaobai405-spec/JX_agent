from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.plan_phase import JobPrototype, JobAnalysis, PerformanceContract, IndicatorTemplate, AIGenerationLog
from models.user import User, UserRole


async def create_job_analysis(db: AsyncSession, current_user: User, user_id: str, jd_text: str) -> JobAnalysis:
    from core.exceptions import PermissionDeniedError, JobAnalysisFailedError

    if current_user.role == UserRole.employee and current_user.id != user_id:
        raise PermissionDeniedError("Can only create analysis for yourself")

    try:
        from graphs.p_graph import run_classify_only
        classify_result = await run_classify_only(jd_text)

        analysis = JobAnalysis(
            user_id=user_id,
            jd_text=jd_text,
            job_prototype_code=classify_result.position_type,
            quantifiability_score=classify_result.score_quantifiability,
            output_cycle_score=classify_result.score_output_cycle,
            work_nature_score=classify_result.score_work_nature,
            confidence=classify_result.confidence,
            analysis_result={"classify_result": classify_result.model_dump()}
        )
        db.add(analysis)

        log = AIGenerationLog(
            job_type="analysis",
            user_id=user_id,
            job_analysis_id=analysis.id,
            model_used="deepseek-chat",
            success=True
        )
        db.add(log)

        await db.commit()
        await db.refresh(analysis)
        return analysis
    except Exception as e:
        raise JobAnalysisFailedError(str(e))


async def get_job_analysis(db: AsyncSession, analysis_id: str) -> JobAnalysis:
    from core.exceptions import JobAnalysisFailedError
    analysis = await db.get(JobAnalysis, analysis_id)
    if not analysis:
        raise JobAnalysisFailedError("Analysis not found")
    return analysis


async def list_job_analyses(db: AsyncSession, current_user: User, user_id: str | None = None) -> list[JobAnalysis]:
    query = select(JobAnalysis)

    if current_user.role == UserRole.employee:
        query = query.where(JobAnalysis.user_id == current_user.id)
    elif user_id:
        query = query.where(JobAnalysis.user_id == user_id)

    query = query.order_by(JobAnalysis.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


async def get_prototype(db: AsyncSession, code: str) -> JobPrototype:
    from core.exceptions import PrototypeNotFoundError
    result = await db.execute(select(JobPrototype).where(JobPrototype.code == code))
    prototype = result.scalar_one_or_none()
    if not prototype:
        raise PrototypeNotFoundError()
    return prototype


async def list_prototypes(db: AsyncSession) -> list[JobPrototype]:
    result = await db.execute(select(JobPrototype))
    return result.scalars().all()


async def get_prototype_by_id(db: AsyncSession, prototype_id: str) -> JobPrototype:
    from core.exceptions import PrototypeNotFoundError
    prototype = await db.get(JobPrototype, prototype_id)
    if not prototype:
        raise PrototypeNotFoundError()
    return prototype


async def update_prototype(db: AsyncSession, current_user: User, prototype_id: str, data: dict) -> JobPrototype:
    from core.exceptions import PermissionDeniedError

    if current_user.role not in (UserRole.hr_admin, UserRole.system_admin):
        raise PermissionDeniedError("Only admins can update prototypes")

    prototype = await get_prototype_by_id(db, prototype_id)

    for key, value in data.items():
        if value is not None:
            setattr(prototype, key, value)

    await db.commit()
    await db.refresh(prototype)
    return prototype


async def delete_prototype(db: AsyncSession, current_user: User, prototype_id: str) -> None:
    from core.exceptions import PermissionDeniedError

    if current_user.role != UserRole.system_admin:
        raise PermissionDeniedError("Only system admins can delete prototypes")

    prototype = await get_prototype_by_id(db, prototype_id)
    await db.delete(prototype)
    await db.commit()


def validate_contract_indicators(contract_data: dict, prototype: JobPrototype) -> None:
    from core.exceptions import IndicatorWeightError, ContractGenerationFailedError

    indicators = contract_data.get('indicators', [])
    regular = [i for i in indicators if i.get('is_special') == 'none']

    total_weight = sum(i.get('weight', 0) for i in regular)
    if abs(total_weight - 1.0) > 0.001:
        raise IndicatorWeightError(f"Weight sum is {total_weight}, must be 1.0")

    count = len(indicators)
    if not (prototype.indicator_count_min <= count <= prototype.indicator_count_max):
        raise ContractGenerationFailedError(
            f"Indicator count {count} outside range [{prototype.indicator_count_min}, {prototype.indicator_count_max}]"
        )

    quantitative = [i for i in regular if i.get('indicator_attribute') == 'quantitative']
    ratio = len(quantitative) / len(regular) if regular else 0
    if not (prototype.quantitative_ratio_min <= ratio <= prototype.quantitative_ratio_max):
        raise ContractGenerationFailedError(
            f"Quantitative ratio {ratio:.2f} outside range [{prototype.quantitative_ratio_min}, {prototype.quantitative_ratio_max}]"
        )


async def generate_contract(db: AsyncSession, current_user: User, period_id: str, user_id: str, job_analysis_id: str, feedback: str | None = None) -> PerformanceContract:
    from core.exceptions import PermissionDeniedError, ContractGenerationFailedError
    import uuid

    if current_user.role == UserRole.employee and current_user.id != user_id:
        raise PermissionDeniedError("Can only generate contract for yourself")

    analysis = await get_job_analysis(db, job_analysis_id)
    classify_result_dict = analysis.analysis_result.get("classify_result", {})

    try:
        from graphs.p_graph import run_generate_indicators, ClassifyResult
        classify_result = ClassifyResult(**classify_result_dict)
        p_result = await run_generate_indicators(analysis.jd_text, classify_result, db, feedback)

        contract_data = {
            "indicators": [ind.model_dump() for ind in p_result.indicators],
            "period_id": period_id,
            "assessment_period": p_result.assessment_period,
            "coaching_period": p_result.coaching_period,
            "result_application": p_result.result_application
        }

        contract = PerformanceContract(
            goal_id=None,
            job_prototype_code=analysis.job_prototype_code,
            strategy_config={},
            contract_data=contract_data,
            ai_generated=True
        )
        db.add(contract)
        await db.commit()
        await db.refresh(contract)
        return contract
    except Exception as e:
        raise ContractGenerationFailedError(str(e))


async def get_contract(db: AsyncSession, contract_id: str) -> PerformanceContract:
    from core.exceptions import ContractNotFoundError
    contract = await db.get(PerformanceContract, contract_id)
    if not contract:
        raise ContractNotFoundError()
    return contract


async def confirm_contract(db: AsyncSession, current_user: User, contract_id: str, confirmed_by: str) -> PerformanceContract:
    from core.exceptions import ContractConfirmedError, GoalAlreadyExistsError
    from models.check_phase import Goal, Indicator, IndicatorDirection, ScoreMethod

    contract = await get_contract(db, contract_id)

    if contract.confirmed_at:
        raise ContractConfirmedError()

    # 创建 Goal
    period_id = contract.contract_data.get("period_id")

    # Guard: prevent duplicate goals for same user+period
    existing = await db.execute(select(Goal).where(Goal.owner_user_id == confirmed_by, Goal.period_id == period_id))
    if existing.scalars().first():
        raise GoalAlreadyExistsError()
    goal = Goal(
        owner_user_id=confirmed_by,
        period_id=period_id,
        title=f"绩效目标-{contract.job_prototype_code}",
        created_by=current_user.id,
        ai_generated=contract.ai_generated,
        performance_contract_id=contract.id
    )
    db.add(goal)
    await db.flush()

    # 创建 Indicators
    indicators_data = contract.contract_data.get("indicators", [])
    for ind_data in indicators_data:
        indicator = Indicator(
            goal_id=goal.id,
            name=ind_data.get("name"),
            definition=ind_data.get("definition"),
            direction=IndicatorDirection.positive if ind_data.get("type") == "positive" else IndicatorDirection.negative,
            weight=ind_data.get("weight", 0) / 100.0,
            target_value=ind_data.get("target"),
            score_method=ScoreMethod.ratio,
            redline=ind_data.get("is_redline", False)
        )
        db.add(indicator)

    # 更新 contract
    contract.goal_id = goal.id
    contract.confirmed_at = datetime.now(timezone.utc)
    contract.confirmed_by = current_user.id

    # 自动将周期状态更新为 open（同一用户不能有多个 open 周期）
    from models.period import Period, PeriodStatus
    from sqlalchemy import and_ as _and
    period = await db.get(Period, period_id)
    if period and period.status == PeriodStatus.draft:
        dup = await db.execute(
            select(Period).where(
                _and(Period.user_id == confirmed_by, Period.status == PeriodStatus.open, Period.id != period_id)
            )
        )
        if not dup.scalars().first():
            period.status = PeriodStatus.open

    await db.commit()
    await db.refresh(contract)
    return contract


async def list_templates(db: AsyncSession, prototype_code: str | None = None) -> list[IndicatorTemplate]:
    query = select(IndicatorTemplate)
    if prototype_code:
        query = query.where(IndicatorTemplate.job_prototype_code == prototype_code)
    result = await db.execute(query)
    return result.scalars().all()
