import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import AsyncSessionLocal, init_db
from graphs.p_graph import run_classify_only, run_generate_indicators
from scripts.seed_demo_data import JD_CASES


EXPECTED = {
    "S": {"indicator_min": 3, "indicator_max": 5, "period_keywords": ("月度",)},
    "P": {"indicator_min": 5, "indicator_max": 7, "period_keywords": ("季度",)},
    "O": {"indicator_min": 4, "indicator_max": 6, "period_keywords": ("月度",)},
    "F": {"indicator_min": 5, "indicator_max": 7, "period_keywords": ("月度",)},
    "M": {"indicator_min": 5, "indicator_max": 7, "period_keywords": ("半年度", "半年")},
}


def _assert_mock_mode() -> None:
    use_mock = os.getenv("USE_MOCK", "").lower()
    assert use_mock == "true", "Run with USE_MOCK=true before importing graph modules"


def _assert_result(case_code: str, result) -> None:
    expected = EXPECTED[case_code]
    indicators = result.indicators
    regular = [indicator for indicator in indicators if not indicator.is_redline]
    redlines = [indicator for indicator in indicators if indicator.is_redline]
    weight_sum = sum(indicator.weight for indicator in regular)

    assert result.position_type == case_code, f"{case_code}: result position_type mismatch"
    assert expected["indicator_min"] <= len(indicators) <= expected["indicator_max"], (
        f"{case_code}: indicator count {len(indicators)} outside expected range"
    )
    assert weight_sum == 100, f"{case_code}: non-redline weight sum is {weight_sum}"
    assert len(redlines) >= 1, f"{case_code}: missing redline indicator"
    assert any(keyword in result.assessment_period for keyword in expected["period_keywords"]), (
        f"{case_code}: unexpected assessment period {result.assessment_period}"
    )


async def verify_mock_llm_cases() -> None:
    _assert_mock_mode()
    await init_db()

    async with AsyncSessionLocal() as session:
        for case_code, case in JD_CASES.items():
            classification = await run_classify_only(case["jd"])
            assert classification.position_type == case_code, (
                f"{case_code}: classified as {classification.position_type}"
            )

            p_result = await run_generate_indicators(case["jd"], classification, session)
            _assert_result(case_code, p_result)

            print(
                "MOCK_CASE "
                f"{case_code} {case['label']} "
                f"indicators={len(p_result.indicators)} "
                f"period={p_result.assessment_period}"
            )

    print("MOCK_LLM_CASES_OK")


if __name__ == "__main__":
    asyncio.run(verify_mock_llm_cases())
