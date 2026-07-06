"""
D 阶段 LangGraph — 追踪反馈
节点：calculate_achievements → generate_feedback → END
"""
from typing import List, Dict, Any, Optional, TypedDict
from langgraph.graph import StateGraph, END
from utils.calculations import calculate_d_stage
from utils.llm import get_llm_client


FEEDBACK_SYSTEM = """你是一位专业的绩效管理顾问，擅长绩效数据分析和辅导反馈。
请根据员工的指标达成情况，提供专业、具体、可操作的根因分析和改进建议。
语言：中文，简洁专业，每条建议都要具体可操作。"""

FEEDBACK_FEW_SHOT = """
【Few-shot 示例】

场景1: S类销售岗，量化达成够但质量不够（巡店SOP评级"合格"）
根因分析: 周末巡店覆盖率不足，高峰期陈列被竞品占据，价格签更新滞后。
改进建议:
1. 每周三、五各增加1次重点门店专项巡查，重点检查陈列面积和价格签
2. 与门店店长建立微信群，实时获取陈列异常反馈
3. 申请增加2名理货员配合周末高峰期陈列维护

场景2: P类项目岗，研发节点延期（里程碑达成率80%）
根因分析: 中试阶段与生产部协调周期超预期，设备调试时间压缩了配方验证时间。
改进建议:
1. 下周与生产部门提前预约中试设备，锁定时间窗口
2. 建立双周进度同步机制，提前2周预警可能的节点风险
3. 将剩余验证任务拆解为日级别计划，每日更新进度看板

场景3: O类运营岗，质量红线触发（配方事故1次）
根因分析: 原材料批次检验流程存在漏洞，新员工操作规范培训不足。
改进建议:
1. 立即组织全组配方操作规范复训，确保100%通过考核
2. 对本次事故进行根因五问分析，输出改进报告（本周内完成）
3. 增加生产前双人复核检查点，修订现有SOP文档
"""


class DGraphState(TypedDict):
    indicators: List[Dict]
    actuals: Dict[str, Any]
    feedback: Optional[str]
    d_result: Optional[Dict]
    feedback_text: Optional[str]
    error: Optional[str]
    ui_callback: Optional[Any]


def calculate_achievements_node(state: DGraphState) -> DGraphState:
    """纯 Python 计算节点"""
    try:
        result = calculate_d_stage(state["indicators"], state["actuals"])
        return {**state, "d_result": result}
    except Exception as e:
        return {**state, "error": str(e)}


def generate_feedback_node(state: DGraphState) -> DGraphState:
    """AI 反馈生成节点（流式）"""
    if state.get("error"):
        return state

    d_result = state["d_result"]
    indicator_results = d_result["indicator_results"]

    # 汇总问题指标
    problem_indicators = [
        r for r in indicator_results
        if r["status"] in ("red", "yellow") and not r["is_redline"]
    ]
    redline_indicators = [
        r for r in indicator_results
        if r["is_redline"] and r.get("redline_triggered")
    ]

    # 构建 prompt
    problem_desc = ""
    for ind in problem_indicators:
        emoji = "🔴" if ind["status"] == "red" else "🟡"
        problem_desc += f"\n{emoji} **{ind['name']}**: 目标={ind['target_display']}，实际={ind['actual']}，达成率={ind['achievement_rate']}%"

    for ind in redline_indicators:
        problem_desc += f"\n🔴 **【红线触发】{ind['name']}**: 发生次数={ind['actual']}次"

    if not problem_desc:
        problem_desc = "所有指标均达标，表现优秀。"

    prompt = f"""
{FEEDBACK_FEW_SHOT}

---

【当前员工绩效数据】

综合加权达成率：{d_result['weighted_achievement']}%
综合偏差：{d_result['deviation']:+.1f}%（相对于80%时间进度）
整体状态：{'🔴 预警' if d_result['overall_status'] == 'red' else ('🟡 关注' if d_result['overall_status'] == 'yellow' else '🟢 良好')}

【问题指标】
{problem_desc}

【用户补充说明】
{state.get('feedback') or '无'}

请针对以上问题指标，提供：
1. 根因分析（每个问题指标单独分析，分析要具体，结合快消行业背景）
2. 改进建议（3-5条具体可操作的行动计划，包含时间节点）

格式要求：使用 Markdown，先根因分析，再改进建议，语言专业简洁。
"""
    try:
        ui_callback = state.get("ui_callback")
        llm = get_llm_client()

        def token_cb(stats):
            if ui_callback:
                ui_callback({"type": "token_update", **stats})

        full_text = llm.call_stream(prompt, FEEDBACK_SYSTEM, callback=token_cb)
        return {**state, "feedback_text": full_text}
    except Exception as e:
        return {**state, "error": str(e), "feedback_text": f"AI 反馈生成失败: {e}"}


def build_d_graph():
    graph = StateGraph(DGraphState)
    graph.add_node("calculate_achievements", calculate_achievements_node)
    graph.add_node("generate_feedback", generate_feedback_node)
    graph.set_entry_point("calculate_achievements")
    graph.add_edge("calculate_achievements", "generate_feedback")
    graph.add_edge("generate_feedback", END)
    return graph.compile()


d_graph = build_d_graph()


def run_d_stage(indicators: List[Dict], actuals: Dict[str, Any], feedback: str | None = None, ui_callback=None) -> Dict:
    """运行 D 阶段图"""
    initial_state = {
        "indicators": indicators,
        "actuals": actuals,
        "feedback": feedback,
        "d_result": None,
        "feedback_text": None,
        "error": None,
        "ui_callback": ui_callback,
    }
    final_state = d_graph.invoke(initial_state)
    if final_state.get("error"):
        raise Exception(final_state["error"])
    return {
        "d_result": final_state["d_result"],
        "feedback_text": final_state.get("feedback_text", ""),
    }
