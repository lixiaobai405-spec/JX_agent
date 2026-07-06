"""
C 阶段 LangGraph — 评估定级
节点：calculate_scores → determine_grade → generate_result_sheet → END
"""
from typing import List, Dict, Any, Optional, TypedDict
from langgraph.graph import StateGraph, END
from utils.calculations import calculate_c_stage
from utils.llm import get_llm_client


RESULT_SYSTEM = "你是一位专业的绩效管理顾问，擅长撰写绩效结果确认单。请使用正式、专业的中文，以 Markdown 格式输出。"

RESULT_FEW_SHOT = """
【结果确认单示例 — A级】

# 绩效结果确认单

**员工姓名**：（员工姓名）
**考核周期**：（考核周期）
**岗位**：（岗位名称）
**考核等级**：**A级**

## 指标得分明细

| 指标名称 | 权重 | 上级评分 | 加权得分 |
|---------|------|---------|---------|
| 区域净销售额 | 45% | 85 | 38.25 |
| 新品铺货率 | 20% | 90 | 18.00 |
| （其他指标） | ... | ... | ... |

## 综合评价

该员工本考核期整体表现良好，在新品推广和渠道维护方面表现突出，核心销售指标达成度较高。建议在以下方面继续努力：...

**评价人**：___________
**日期**：___________
"""


class CGraphState(TypedDict):
    indicator_results: List[Dict]
    supervisor_scores: Dict[str, float]
    supervisor_comment: str
    redline_triggered: bool
    redline_count: int
    position_name: str
    assessment_period: str
    c_result: Optional[Dict]
    result_sheet_text: Optional[str]
    error: Optional[str]
    ui_callback: Optional[Any]


def calculate_scores_node(state: CGraphState) -> CGraphState:
    """纯 Python 评分计算"""
    try:
        result = calculate_c_stage(
            state["indicator_results"],
            state["supervisor_scores"],
            state["redline_triggered"],
            state["redline_count"],
        )
        return {**state, "c_result": result}
    except Exception as e:
        return {**state, "error": str(e)}


def determine_grade_node(state: CGraphState) -> CGraphState:
    """等级判定（已在 calculate_c_stage 中完成，此节点确认无误）"""
    if state.get("error"):
        return state
    # Grade already determined in calculate_scores_node
    return state


def generate_result_sheet_node(state: CGraphState) -> CGraphState:
    """生成绩效结果确认单（LLM 流式）"""
    if state.get("error"):
        return state

    c_result = state["c_result"]

    # 构建指标得分明细字符串
    scores_table = "| 指标名称 | 权重 | 上级评分 | 加权得分 |\n|---------|------|---------|---------|"
    for ind in c_result["indicator_scores"]:
        scores_table += f"\n| {ind['name']} | {ind['weight']}% | {ind['score']} | {ind['weighted_score']} |"

    deduction_note = ""
    if c_result["deductions"] > 0:
        deduction_note = f"\n**红线扣分**：-{c_result['deductions']}分"

    prompt = f"""
{RESULT_FEW_SHOT}

---

请根据以下数据，生成一份专业的绩效结果确认单（Markdown格式）：

【考核信息】
- 岗位：{state['position_name']}
- 考核周期：{state['assessment_period']}
- 综合得分：{c_result['total_score']}分（原始分{c_result['raw_score']}分{deduction_note}）
- 考核等级：{c_result['grade']}级

【指标得分明细】
{scores_table}

【评价人评语】
{state['supervisor_comment']}

请输出完整的绩效结果确认单，包含：
1. 标题和基本信息
2. 指标得分明细表格
3. 综合得分和等级（突出显示）
4. 评价人评语（基于上方评语适当扩展，保持专业口吻）
5. 签字栏

语气：正式、客观、专业，避免空洞套话。
"""
    try:
        ui_callback = state.get("ui_callback")
        llm = get_llm_client()

        def token_cb(stats):
            if ui_callback:
                ui_callback({"type": "token_update", **stats})

        text = llm.call_stream(prompt, RESULT_SYSTEM, callback=token_cb)
        return {**state, "result_sheet_text": text}
    except Exception as e:
        return {**state, "error": str(e), "result_sheet_text": f"生成失败: {e}"}


def build_c_graph():
    graph = StateGraph(CGraphState)
    graph.add_node("calculate_scores", calculate_scores_node)
    graph.add_node("determine_grade", determine_grade_node)
    graph.add_node("generate_result_sheet", generate_result_sheet_node)
    graph.set_entry_point("calculate_scores")
    graph.add_edge("calculate_scores", "determine_grade")
    graph.add_edge("determine_grade", "generate_result_sheet")
    graph.add_edge("generate_result_sheet", END)
    return graph.compile()


c_graph = build_c_graph()


def run_c_stage(
    indicator_results: List[Dict],
    supervisor_scores: Dict[str, float],
    supervisor_comment: str,
    redline_triggered: bool,
    redline_count: int,
    position_name: str,
    assessment_period: str,
    ui_callback=None,
) -> Dict:
    """运行 C 阶段图"""
    initial_state = {
        "indicator_results": indicator_results,
        "supervisor_scores": supervisor_scores,
        "supervisor_comment": supervisor_comment,
        "redline_triggered": redline_triggered,
        "redline_count": redline_count,
        "position_name": position_name,
        "assessment_period": assessment_period,
        "c_result": None,
        "result_sheet_text": None,
        "error": None,
        "ui_callback": ui_callback,
    }
    final_state = c_graph.invoke(initial_state)
    if final_state.get("error"):
        raise Exception(final_state["error"])
    return {
        "c_result": final_state["c_result"],
        "result_sheet_text": final_state.get("result_sheet_text", ""),
    }
