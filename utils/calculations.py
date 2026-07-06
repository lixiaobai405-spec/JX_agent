"""
D/C 阶段计算逻辑
"""
from typing import List, Dict, Any, Optional


def calc_achievement_rate(
    indicator_type: str,
    target: float,
    actual: float
) -> float:
    """
    计算单个指标达成率（百分比，0-150）
    - positive（正向）：越大越好
    - negative（反向）：越小越好
    - qualitative（定性）：文字评级
    - redline（红线）：次数
    """
    if indicator_type == "positive":
        if target == 0:
            return 100.0
        return min((actual / target) * 100, 150.0)

    elif indicator_type == "negative":
        if actual <= target:
            return 100.0
        if target == 0:
            return 0.0
        return max(0.0, (1 - (actual - target) / target) * 100)

    elif indicator_type == "qualitative":
        # actual 传入字符串评级，这里转为数字处理
        # 调用方传 actual 为 0-100 的分数（已在上层转换）
        return min(actual, 100.0)

    elif indicator_type == "redline":
        # actual = 发生次数
        return 100.0 if actual == 0 else 0.0

    return 0.0


def qualitative_to_score(level: str) -> float:
    """定性评级 → 达成率分数"""
    mapping = {
        "优秀": 100.0,
        "良好": 80.0,
        "合格": 60.0,
        "不合格": 0.0,
    }
    return mapping.get(level, 0.0)


def get_indicator_status(rate: float, is_redline: bool, redline_triggered: bool) -> str:
    """灯号判定"""
    if is_redline and redline_triggered:
        return "red"
    if rate >= 100:
        return "green"
    elif rate >= 80:
        return "yellow"
    else:
        return "red"


def calculate_d_stage(indicators: List[Dict], actuals: Dict[str, Any]) -> Dict:
    """
    D 阶段核心计算

    Args:
        indicators: List of indicator dicts from PStageResult
        actuals: {indicator_name: actual_value_or_level}

    Returns:
        {
            "indicator_results": [...],
            "weighted_achievement": float,
            "deviation": float,
            "overall_status": str,
            "redline_triggered": bool,
        }
    """
    indicator_results = []
    total_weight = 0.0
    weighted_sum = 0.0
    redline_triggered = False

    for ind in indicators:
        name = ind["name"]
        ind_type = ind["type"]
        target = ind.get("target", 0)
        weight = ind.get("weight", 0)
        is_redline = ind.get("is_redline", False)

        actual_raw = actuals.get(name)
        if actual_raw is None:
            actual_raw = 0

        # 转换定性评级
        if ind_type == "qualitative":
            if isinstance(actual_raw, str):
                actual_score = qualitative_to_score(actual_raw)
            else:
                actual_score = float(actual_raw)
            rate = calc_achievement_rate("qualitative", 100, actual_score)
            actual_display = actual_raw if isinstance(actual_raw, str) else str(actual_raw)
        else:
            actual_score = float(actual_raw)
            rate = calc_achievement_rate(ind_type, target, actual_score)
            actual_display = str(actual_raw)

        # 红线判定
        ind_redline_triggered = False
        if is_redline:
            ind_redline_triggered = actual_score > 0
            if ind_redline_triggered:
                redline_triggered = True
            rate = 0.0 if ind_redline_triggered else 100.0

        status = get_indicator_status(rate, is_redline, ind_redline_triggered)

        result = {
            "name": name,
            "type": ind_type,
            "target": target,
            "target_display": ind.get("target_display", str(target)),
            "actual": actual_display,
            "actual_value": actual_score,
            "weight": weight,
            "achievement_rate": round(rate, 1),
            "status": status,
            "is_redline": is_redline,
            "redline_triggered": ind_redline_triggered,
        }
        indicator_results.append(result)

        # 加权计算（排除红线指标）
        if not is_redline and weight > 0:
            total_weight += weight
            weighted_sum += rate * weight

    # 加权达成率
    if total_weight > 0:
        weighted_achievement = weighted_sum / total_weight
    else:
        weighted_achievement = 0.0

    # 综合偏差（时间进度固定 80%）
    time_progress = 80.0
    deviation = weighted_achievement - time_progress

    # 整体灯号
    if redline_triggered or weighted_achievement < 80:
        overall_status = "red"
    elif weighted_achievement >= 100:
        overall_status = "green"
    else:
        overall_status = "yellow"

    return {
        "indicator_results": indicator_results,
        "weighted_achievement": round(weighted_achievement, 1),
        "deviation": round(deviation, 1),
        "overall_status": overall_status,
        "redline_triggered": redline_triggered,
    }


def calculate_c_stage(
    indicator_results: List[Dict],
    supervisor_scores: Dict[str, float],
    redline_triggered: bool = False,
    redline_count: int = 0
) -> Dict:
    """
    C 阶段评分计算

    Args:
        indicator_results: D 阶段指标结果
        supervisor_scores: {indicator_name: supervisor_score (0-100)}
        redline_triggered: 是否触发红线
        redline_count: 红线触发次数

    Returns:
        {total_score, grade, deductions, indicator_scores}
    """
    total_score = 0.0
    indicator_scores = []
    deductions = 0.0

    # 红线扣分（每次 -20）
    if redline_triggered and redline_count > 0:
        deductions = redline_count * 20.0

    for result in indicator_results:
        name = result["name"]
        weight = result.get("weight", 0)
        is_redline = result.get("is_redline", False)

        if is_redline:
            continue  # 红线不参与正式评分，单独扣分

        score = supervisor_scores.get(name, result.get("achievement_rate", 0))
        score = min(100.0, max(0.0, float(score)))
        weighted_score = score * weight / 100.0
        total_score += weighted_score

        indicator_scores.append({
            "name": name,
            "weight": weight,
            "score": round(score, 1),
            "weighted_score": round(weighted_score, 1),
        })

    final_score = max(0.0, total_score - deductions)

    # 绝对评价
    if final_score >= 90:
        grade = "S"
    elif final_score >= 80:
        grade = "A"
    elif final_score >= 70:
        grade = "B"
    else:
        grade = "C"

    return {
        "total_score": round(final_score, 1),
        "raw_score": round(total_score, 1),
        "deductions": round(deductions, 1),
        "grade": grade,
        "indicator_scores": indicator_scores,
    }
