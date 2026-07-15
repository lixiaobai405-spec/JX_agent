from datetime import datetime, timezone
import copy
from collections import Counter
import logging
import math
import time
from types import SimpleNamespace

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from models.plan_phase import JobPrototype, JobAnalysis, PerformanceContract, IndicatorTemplate, AIGenerationLog
from models.period import Period, PeriodStatus
from models.action_phase import InheritanceSuggestion, SuggestionStatus
from models.user import User, UserRole, UserStatus


logger = logging.getLogger(__name__)


async def _get_subordinate_ids(db: AsyncSession, manager_id: str) -> list[str]:
    direct_reports = (
        select(User.id.label("id"))
        .where(
            User.manager_id == manager_id,
            User.status == UserStatus.active,
            User.deleted_at.is_(None),
        )
        .cte("plan_subordinate_ids", recursive=True)
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
    *,
    lock_target: bool = False,
) -> None:
    from core.exceptions import PermissionDeniedError, UserNotFoundError

    target_query = select(User.id).where(
        User.id == target_user_id,
        User.status == UserStatus.active,
        User.deleted_at.is_(None),
    )
    if lock_target:
        target_query = target_query.with_for_update()
    target_result = await db.execute(target_query)
    if target_result.scalar_one_or_none() is None:
        raise UserNotFoundError()

    if current_user.id == target_user_id:
        return
    if current_user.role in (UserRole.hr_admin, UserRole.system_admin):
        return
    if current_user.role == UserRole.manager:
        subordinate_ids = await _get_subordinate_ids(db, current_user.id)
        if target_user_id in subordinate_ids:
            return
    raise PermissionDeniedError("Cannot access this user's plan data")


async def _get_period_record(
    db: AsyncSession,
    period_id: str,
    *,
    for_update: bool = False,
) -> Period:
    from core.exceptions import PeriodNotFoundError

    query = select(Period).where(
        Period.id == period_id,
        Period.deleted_at.is_(None),
    )
    if for_update:
        query = query.with_for_update()
    result = await db.execute(query)
    period = result.scalar_one_or_none()
    if not period:
        raise PeriodNotFoundError()
    return period


async def _get_job_analysis_record(
    db: AsyncSession,
    analysis_id: str,
) -> JobAnalysis:
    from core.exceptions import JobAnalysisFailedError

    analysis = await db.get(JobAnalysis, analysis_id)
    if not analysis:
        raise JobAnalysisFailedError("Analysis not found")
    return analysis


async def _get_contract_record(
    db: AsyncSession,
    contract_id: str,
) -> PerformanceContract:
    from core.exceptions import ContractNotFoundError

    contract = await db.get(PerformanceContract, contract_id)
    if not contract:
        raise ContractNotFoundError()
    return contract


async def _authorize_contract(
    db: AsyncSession,
    current_user: User,
    contract: PerformanceContract,
    *,
    lock_period: bool = False,
) -> Period:
    from core.exceptions import ContractGenerationFailedError, PermissionDeniedError

    contract_data = contract.contract_data or {}
    period_id = contract_data.get("period_id")
    if not period_id:
        raise ContractGenerationFailedError("Contract has no period")
    period = await _get_period_record(db, period_id, for_update=lock_period)

    embedded_user_id = contract_data.get("user_id")
    if embedded_user_id is not None and embedded_user_id != period.user_id:
        raise PermissionDeniedError("Contract owner does not match period owner")

    analysis_id = contract_data.get("job_analysis_id")
    if analysis_id:
        analysis = await _get_job_analysis_record(db, analysis_id)
        if analysis.user_id != period.user_id:
            raise PermissionDeniedError("Contract analysis does not match period owner")

    await _assert_user_access(db, current_user, period.user_id)
    return period


def _execution_time_ms(started_at: float) -> int:
    return max(0, int((time.perf_counter() - started_at) * 1000))


async def _write_ai_failure_log(
    db: AsyncSession,
    *,
    job_type: str,
    user_id: str,
    job_analysis_id: str | None,
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
                    job_analysis_id=job_analysis_id,
                    model_used="deepseek-chat",
                    success=False,
                    error_message=str(error),
                    execution_time_ms=_execution_time_ms(started_at),
                )
            )
            await log_db.commit()
    except Exception:
        logger.exception("Failed to persist AI generation failure log")


async def create_job_analysis(db: AsyncSession, current_user: User, user_id: str, jd_text: str) -> JobAnalysis:
    from core.exceptions import JobAnalysisFailedError

    await _assert_user_access(db, current_user, user_id)

    started_at = time.perf_counter()
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
        await db.flush()

        log = AIGenerationLog(
            job_type="analysis",
            user_id=user_id,
            job_analysis_id=analysis.id,
            model_used="deepseek-chat",
            success=True,
            execution_time_ms=_execution_time_ms(started_at),
        )
        db.add(log)

        await db.commit()
        await db.refresh(analysis)
        return analysis
    except Exception as e:
        await _write_ai_failure_log(
            db,
            job_type="analysis",
            user_id=user_id,
            job_analysis_id=None,
            error=e,
            started_at=started_at,
        )
        raise JobAnalysisFailedError(str(e))


async def get_job_analysis(
    db: AsyncSession,
    current_user: User,
    analysis_id: str,
) -> JobAnalysis:
    analysis = await _get_job_analysis_record(db, analysis_id)
    await _assert_user_access(db, current_user, analysis.user_id)
    return analysis


async def list_job_analyses(db: AsyncSession, current_user: User, user_id: str | None = None) -> list[JobAnalysis]:
    query = select(JobAnalysis)

    if user_id is not None:
        await _assert_user_access(db, current_user, user_id)
        query = query.where(JobAnalysis.user_id == user_id)
    elif current_user.role == UserRole.manager:
        allowed_ids = await _get_subordinate_ids(db, current_user.id)
        allowed_ids.append(current_user.id)
        query = query.where(JobAnalysis.user_id.in_(allowed_ids))
    elif current_user.role == UserRole.employee:
        query = query.where(JobAnalysis.user_id == current_user.id)

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


def _is_redline_indicator(ind_data: dict) -> bool:
    return bool(ind_data.get("is_redline")) or ind_data.get("type") == "redline"


def _indicator_direction(ind_data: dict):
    from models.check_phase import IndicatorDirection

    if ind_data.get("type") in ("negative", "redline"):
        return IndicatorDirection.negative
    return IndicatorDirection.positive


def _indicator_score_method(ind_data: dict):
    from models.check_phase import ScoreMethod

    if ind_data.get("type") == "redline":
        return ScoreMethod.binary
    if ind_data.get("type") == "qualitative":
        return ScoreMethod.manual
    return ScoreMethod.ratio


def _indicator_definition(ind_data: dict) -> str:
    definition = ind_data.get("definition") or ""
    details = []
    if ind_data.get("target_display"):
        details.append(f"目标：{ind_data['target_display']}")
    if ind_data.get("target_logic"):
        details.append(f"目标依据：{ind_data['target_logic']}")
    if ind_data.get("scoring_rule"):
        details.append(f"评分：{ind_data['scoring_rule']}")
    if not details:
        return definition
    suffix = "；".join(details)
    if suffix in definition:
        return definition
    return f"{definition}；{suffix}" if definition else suffix


def validate_contract_indicators(
    contract_data: dict,
    prototype: JobPrototype,
    *,
    require_stable_ids: bool = True,
) -> None:
    from core.exceptions import IndicatorWeightError, ContractGenerationFailedError

    indicators = contract_data.get('indicators', [])
    if not isinstance(indicators, list):
        raise ContractGenerationFailedError("Contract indicators are invalid")
    for indicator in indicators:
        if not isinstance(indicator, dict):
            raise ContractGenerationFailedError("Contract indicators are invalid")
        weight = indicator.get("weight")
        target = indicator.get("target")
        if (
            isinstance(weight, bool)
            or not isinstance(weight, (int, float))
            or not math.isfinite(weight)
        ):
            raise IndicatorWeightError("Indicator weights must be finite numbers")
        if (
            isinstance(target, bool)
            or not isinstance(target, (int, float))
            or not math.isfinite(target)
        ):
            raise ContractGenerationFailedError(
                "Indicator targets must be finite numbers"
            )

    indicator_ids = [
        str(indicator["id"])
        for indicator in indicators
        if indicator.get("id") is not None
    ]
    if require_stable_ids and len(indicator_ids) != len(indicators):
        raise ContractGenerationFailedError("Every indicator must have a stable ID")
    if len(indicator_ids) != len(set(indicator_ids)):
        raise ContractGenerationFailedError("Indicator IDs must be unique")

    regular = [i for i in indicators if not _is_redline_indicator(i)]

    total_weight = sum(i.get('weight', 0) for i in regular)
    if abs(total_weight - 100) > 0.001:
        raise IndicatorWeightError(f"Weight sum is {total_weight}, must be 100")

    count = len(indicators)
    if not (prototype.indicator_count_min <= count <= prototype.indicator_count_max):
        raise ContractGenerationFailedError(
            f"Indicator count {count} outside range [{prototype.indicator_count_min}, {prototype.indicator_count_max}]"
        )

    quantitative_weight = sum(
        i.get('weight', 0)
        for i in regular
        if i.get('type') in ('positive', 'negative')
    )
    ratio = quantitative_weight / total_weight if total_weight else 0
    if not (prototype.quantitative_ratio_min <= ratio <= prototype.quantitative_ratio_max):
        raise ContractGenerationFailedError(
            f"Quantitative ratio {ratio:.2f} outside range [{prototype.quantitative_ratio_min}, {prototype.quantitative_ratio_max}]"
        )


def _validate_inheritance_mapping(indicators: list, expected_ids: list[str]) -> None:
    from core.exceptions import ContractGenerationFailedError

    actual_ids = [
        str(indicator.source_suggestion_id)
        for indicator in indicators
        if indicator.source_suggestion_id is not None
    ]
    if Counter(actual_ids) != Counter(expected_ids):
        raise ContractGenerationFailedError(
            "Generated indicators do not exactly map all inherited suggestions"
        )


async def generate_contract(db: AsyncSession, current_user: User, period_id: str, user_id: str, job_analysis_id: str, feedback: str | None = None) -> PerformanceContract:
    from core.exceptions import PermissionDeniedError, ContractGenerationFailedError

    period = await _get_period_record(db, period_id)
    analysis = await _get_job_analysis_record(db, job_analysis_id)
    if period.user_id != user_id or analysis.user_id != user_id:
        raise PermissionDeniedError(
            "Period owner, analysis owner, and requested user must match"
        )
    await _assert_user_access(db, current_user, user_id)
    classify_result_dict = (analysis.analysis_result or {}).get("classify_result", {})

    suggestion_result = await db.execute(
        select(InheritanceSuggestion)
        .where(
            InheritanceSuggestion.user_id == user_id,
            InheritanceSuggestion.new_period_id == period_id,
            InheritanceSuggestion.status == SuggestionStatus.accepted,
            InheritanceSuggestion.adopted_goal_id.is_(None),
            InheritanceSuggestion.adopted_indicator_id.is_(None),
            InheritanceSuggestion.deleted_at.is_(None),
        )
        .order_by(InheritanceSuggestion.id)
    )
    inherited_suggestions = suggestion_result.scalars().all()
    inherited_payload = [
        {
            "id": suggestion.id,
            "suggestion_type": (
                suggestion.suggestion_type.value
                if hasattr(suggestion.suggestion_type, "value")
                else suggestion.suggestion_type
            ),
            "suggestions": suggestion.suggestions,
        }
        for suggestion in inherited_suggestions
    ]
    expected_suggestion_ids = [suggestion.id for suggestion in inherited_suggestions]

    started_at = time.perf_counter()
    try:
        from graphs.p_graph import run_generate_indicators, ClassifyResult
        classify_result = ClassifyResult(**classify_result_dict)
        p_result = await run_generate_indicators(
            analysis.jd_text,
            classify_result,
            db,
            feedback=feedback,
            inherited_suggestions=inherited_payload,
        )
        _validate_inheritance_mapping(
            p_result.indicators,
            expected_suggestion_ids,
        )

        contract_data = {
            "indicators": [ind.model_dump() for ind in p_result.indicators],
            "period_id": period_id,
            "user_id": user_id,
            "job_analysis_id": analysis.id,
            "position_type": p_result.position_type,
            "position_type_name": p_result.position_type_name,
            "suggested_position_name": p_result.suggested_position_name,
            "classification_reasoning": p_result.classification_reasoning,
            "assessment_period": p_result.assessment_period,
            "coaching_period": p_result.coaching_period,
            "result_application": p_result.result_application
        }
        prototype = await get_prototype(db, analysis.job_prototype_code)
        validate_contract_indicators(contract_data, prototype)

        contract = PerformanceContract(
            goal_id=None,
            job_prototype_code=analysis.job_prototype_code,
            strategy_config={},
            contract_data=contract_data,
            ai_generated=True
        )
        db.add(contract)
        db.add(
            AIGenerationLog(
                job_type="contract",
                user_id=user_id,
                job_analysis_id=analysis.id,
                model_used="deepseek-chat",
                success=True,
                execution_time_ms=_execution_time_ms(started_at),
            )
        )
        await db.commit()
        await db.refresh(contract)
        return contract
    except Exception as e:
        await _write_ai_failure_log(
            db,
            job_type="contract",
            user_id=user_id,
            job_analysis_id=analysis.id,
            error=e,
            started_at=started_at,
        )
        raise ContractGenerationFailedError(str(e))


async def get_contract(
    db: AsyncSession,
    current_user: User,
    contract_id: str,
) -> PerformanceContract:
    contract = await _get_contract_record(db, contract_id)
    await _authorize_contract(db, current_user, contract)
    return contract


async def update_contract_targets(
    db: AsyncSession,
    current_user: User,
    contract_id: str,
    targets: list[dict],
) -> PerformanceContract:
    from core.exceptions import ContractConfirmedError, ContractGenerationFailedError

    actor = SimpleNamespace(id=current_user.id, role=current_user.role)
    await _begin_contract_write_transaction(db)

    try:
        contract_result = await db.execute(
            select(PerformanceContract)
            .where(PerformanceContract.id == contract_id)
            .with_for_update()
        )
        contract = contract_result.scalar_one_or_none()
        if contract is None:
            from core.exceptions import ContractNotFoundError

            raise ContractNotFoundError()

        period = await _authorize_contract(
            db,
            actor,
            contract,
            lock_period=True,
        )
        if contract.confirmed_at is not None:
            raise ContractConfirmedError()
        if period.status not in (PeriodStatus.draft, PeriodStatus.open):
            raise ContractGenerationFailedError(
                "Targets can only be changed in a draft or open period"
            )

        contract_data = copy.deepcopy(contract.contract_data or {})
        indicators = contract_data.get("indicators")
        if not isinstance(indicators, list):
            raise ContractGenerationFailedError("Contract indicators are invalid")

        indicator_index: dict[str, dict] = {}
        for indicator in indicators:
            if not isinstance(indicator, dict) or indicator.get("id") is None:
                continue
            key = str(indicator["id"])
            if key in indicator_index:
                raise ContractGenerationFailedError("Contract indicator IDs are not unique")
            indicator_index[key] = indicator

        pending_updates: list[tuple[dict, float]] = []
        seen_ids: set[str] = set()
        for target_update in targets:
            key = str(target_update.get("indicator_id"))
            target = target_update.get("target")
            if key in seen_ids:
                raise ContractGenerationFailedError("indicator_id values must be unique")
            seen_ids.add(key)
            if (
                isinstance(target, bool)
                or not isinstance(target, (int, float))
                or not math.isfinite(target)
            ):
                raise ContractGenerationFailedError("Target must be a finite number")
            indicator = indicator_index.get(key)
            if indicator is None:
                raise ContractGenerationFailedError(f"Unknown indicator ID: {key}")
            if _is_redline_indicator(indicator):
                raise ContractGenerationFailedError("Redline targets cannot be changed")
            pending_updates.append((indicator, float(target)))

        for indicator, target in pending_updates:
            indicator["target"] = target
            indicator["target_display"] = _updated_target_display(indicator, target)

        contract.contract_data = contract_data
        await db.commit()
        await db.refresh(contract)
        return contract
    except Exception:
        await db.rollback()
        raise


def _updated_target_display(indicator: dict, target: float) -> str:
    formatted_target = f"{target:g}"
    unit = indicator.get("unit")
    if not isinstance(unit, str):
        return formatted_target
    display_unit = {
        "percent": "%",
        "percentage": "%",
        "count": "",
    }.get(unit.strip().lower(), unit)
    return f"{formatted_target}{display_unit}"


async def _begin_contract_write_transaction(db: AsyncSession) -> None:
    bind = db.bind
    dialect_name = bind.dialect.name if bind is not None else db.get_bind().dialect.name

    if dialect_name == "sqlite":
        if db.in_transaction():
            if db.new or db.dirty or db.deleted:
                raise RuntimeError(
                    "Cannot start a contract write while the session has pending changes"
                )
            await db.commit()
        await db.execute(text("BEGIN IMMEDIATE"))
    elif not db.in_transaction():
        await db.begin()


async def confirm_contract(
    db: AsyncSession,
    current_user: User,
    contract_id: str,
    confirmed_by: str | None = None,
) -> PerformanceContract:
    from core.exceptions import (
        ContractConfirmedError,
        ContractGenerationFailedError,
        ContractNotFoundError,
        GoalAlreadyExistsError,
        PermissionDeniedError,
    )
    from models.action_phase import InheritanceSuggestion, SuggestionStatus
    from models.check_phase import Goal, Indicator

    actor_id = current_user.id
    actor_role = current_user.role
    actor = SimpleNamespace(id=actor_id, role=actor_role)
    await _begin_contract_write_transaction(db)

    try:
        contract_result = await db.execute(
            select(PerformanceContract)
            .where(PerformanceContract.id == contract_id)
            .with_for_update()
        )
        contract = contract_result.scalar_one_or_none()
        if contract is None:
            raise ContractNotFoundError()
        if contract.confirmed_at is not None:
            raise ContractConfirmedError()

        contract_data = contract.contract_data or {}
        period_id = contract_data.get("period_id")
        if not period_id:
            raise ContractGenerationFailedError("Contract has no period")

        period_result = await db.execute(
            select(Period)
            .where(
                Period.id == period_id,
                Period.deleted_at.is_(None),
            )
            .with_for_update()
        )
        period = period_result.scalar_one_or_none()
        if period is None:
            from core.exceptions import PeriodNotFoundError

            raise PeriodNotFoundError()
        if period.status not in (PeriodStatus.draft, PeriodStatus.open):
            raise ContractGenerationFailedError(
                "Contracts can only be confirmed in a draft or open period"
            )

        embedded_user_id = contract_data.get("user_id")
        if embedded_user_id is not None and embedded_user_id != period.user_id:
            raise PermissionDeniedError("Contract owner does not match period owner")

        analysis_id = contract_data.get("job_analysis_id")
        if analysis_id:
            analysis = await _get_job_analysis_record(db, analysis_id)
            if analysis.user_id != period.user_id:
                raise PermissionDeniedError("Contract analysis does not match period owner")

        await _assert_user_access(
            db,
            actor,
            period.user_id,
            lock_target=True,
        )

        prototype = await get_prototype(db, contract.job_prototype_code)
        validate_contract_indicators(
            contract_data,
            prototype,
            require_stable_ids=False,
        )

        existing_result = await db.execute(
            select(Goal)
            .where(
                Goal.owner_user_id == period.user_id,
                Goal.period_id == period.id,
                Goal.deleted_at.is_(None),
            )
            .with_for_update()
        )
        if existing_result.scalars().first() is not None:
            raise GoalAlreadyExistsError()

        title = contract_data.get("suggested_position_name")
        if not isinstance(title, str) or not title.strip():
            title = f"绩效目标-{contract.job_prototype_code}"
        goal = Goal(
            owner_user_id=period.user_id,
            period_id=period.id,
            title=title[:200],
            created_by=actor_id,
            ai_generated=contract.ai_generated,
            performance_contract_id=contract.id,
        )
        db.add(goal)
        await db.flush()

        source_indicators: dict[str, Indicator] = {}
        indicators_data = contract_data.get("indicators", [])
        for ind_data in indicators_data:
            indicator = Indicator(
                goal_id=goal.id,
                name=ind_data.get("name"),
                definition=_indicator_definition(ind_data),
                direction=_indicator_direction(ind_data),
                weight=ind_data.get("weight", 0) / 100.0,
                target_value=ind_data.get("target"),
                score_method=_indicator_score_method(ind_data),
                redline=_is_redline_indicator(ind_data),
            )
            db.add(indicator)
            source_suggestion_id = ind_data.get("source_suggestion_id")
            if source_suggestion_id is not None:
                source_key = str(source_suggestion_id)
                if source_key in source_indicators:
                    raise ContractGenerationFailedError(
                        "Each inheritance suggestion must map to one indicator"
                    )
                source_indicators[source_key] = indicator

        await db.flush()

        for source_suggestion_id, indicator in source_indicators.items():
            adoption_result = await db.execute(
                update(InheritanceSuggestion)
                .where(
                    InheritanceSuggestion.id == source_suggestion_id,
                    InheritanceSuggestion.status == SuggestionStatus.accepted,
                    InheritanceSuggestion.user_id == period.user_id,
                    InheritanceSuggestion.new_period_id == period.id,
                    InheritanceSuggestion.adopted_goal_id.is_(None),
                    InheritanceSuggestion.adopted_indicator_id.is_(None),
                    InheritanceSuggestion.deleted_at.is_(None),
                )
                .values(
                    adopted_goal_id=goal.id,
                    adopted_indicator_id=indicator.id,
                )
            )
            if adoption_result.rowcount != 1:
                raise ContractGenerationFailedError(
                    f"Inheritance suggestion {source_suggestion_id} is no longer adoptable"
                )

        contract.goal_id = goal.id
        contract.confirmed_at = datetime.now(timezone.utc)
        contract.confirmed_by = actor_id

        if period.status == PeriodStatus.draft:
            duplicate_open_result = await db.execute(
                select(Period.id).where(
                    Period.user_id == period.user_id,
                    Period.status == PeriodStatus.open,
                    Period.id != period.id,
                    Period.deleted_at.is_(None),
                )
            )
            if duplicate_open_result.scalar_one_or_none() is None:
                period.status = PeriodStatus.open

        await db.commit()
        await db.refresh(contract)
        return contract
    except Exception:
        await db.rollback()
        raise


async def list_templates(db: AsyncSession, prototype_code: str | None = None) -> list[IndicatorTemplate]:
    query = select(IndicatorTemplate)
    if prototype_code:
        query = query.where(IndicatorTemplate.job_prototype_code == prototype_code)
    result = await db.execute(query)
    return result.scalars().all()
