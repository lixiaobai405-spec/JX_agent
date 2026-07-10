from utils.calculations import calculate_c_stage


def test_calculate_c_stage_skips_redline_weight_and_applies_deduction():
    result = calculate_c_stage(
        [
            {"name": "销售额", "weight": 80, "is_redline": False},
            {"name": "重大事故", "weight": 20, "is_redline": True},
        ],
        {"销售额": 100},
        redline_triggered=True,
        redline_count=1,
    )

    assert result["raw_score"] == 80
    assert result["deductions"] == 20
    assert result["total_score"] == 60
    assert result["grade"] == "C"
