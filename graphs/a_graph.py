"""
A 阶段 LangGraph — 复盘发展
节点：generate_review → END
独立函数：review_plan（计划审核）
"""
from typing import List, Dict, Any, Optional, TypedDict
from pydantic import BaseModel
from langgraph.graph import StateGraph, END
from utils.llm import retry_and_validate, run_sync_llm


# ===== Pydantic 模型 =====

class StrengthItem(BaseModel):
    indicator: str
    score: float
    comment: str


class DevelopmentItem(BaseModel):
    indicator: str
    score: float
    suggestion: str


class ReviewReport(BaseModel):
    overall_summary: str
    strengths: List[StrengthItem]
    development_areas: List[DevelopmentItem]


class SMARTDimension(BaseModel):
    status: str  # ✅, ⚠️, or ❌
    comment: str


class PlanReviewResult(BaseModel):
    smart_evaluation: Dict[str, SMARTDimension]  # specific, measurable, achievable, relevant, time_bound
    polished_goals: str  # markdown format
    polished_actions: str  # markdown format
    overall_review: str  # markdown format


# ===== Few-shot =====

REVIEW_SYSTEM = "你是一位专业的绩效复盘顾问，擅长绩效反馈和员工发展辅导。请以 JSON 格式返回复盘报告。"

REVIEW_FEW_SHOT = """
【Few-shot 复盘报告示例】

等级S — 激励强化风格:
overall_summary: "本考核期表现卓越（S级），全面超额完成核心指标，尤其在销售冲刺和新品推广方面展现出极强的执行力。"
strengths: [{"indicator":"区域净销售额","score":115,"comment":"超额完成15%，渠道拓展策略执行有力"}]
development_areas: []（或少量精进方向）

等级A — 正向引导风格:
overall_summary: "本考核期整体表现良好（A级），在部分核心指标上展现出较强实力，仍有进一步提升空间。"
strengths: [{"indicator":"新品铺货率","score":90,"comment":"超额完成目标，渠道拓展能力强"}]
development_areas: [{"indicator":"区域净销售额","score":75,"suggestion":"聚焦TOP门店动销提升，配合市场部终端活动"}]

等级B — 建设性反馈风格:
overall_summary: "本考核期表现达标（B级），在执行层面有所成长，但在结果达成方面与目标存在差距，需要聚焦重点改进。"

等级C — 直接改进风格:
overall_summary: "本考核期整体表现未达预期（C级），多项核心指标显著低于目标，需要深入分析原因并制定系统性改进计划。"
"""

PLAN_REVIEW_SYSTEM = "你是一位专业的绩效辅导顾问，擅长个人发展计划审核。请提供专业、建设性的 SMART 检验和改进建议。"

PLAN_REVIEW_FEW_SHOT = """
【计划审核示例】

SMART检验:
- 具体性（S）: ✅/⚠️/❌ + 评价
- 可衡量（M）: ✅/⚠️/❌ + 评价
- 可实现（A）: ✅/⚠️/❌ + 评价
- 相关性（R）: ✅/⚠️/❌ + 评价
- 时限性（T）: ✅/⚠️/❌ + 评价

资源建议: [具体可申请的内部/外部资源]
关联度评估: [计划与短板指标的关联程度分析]
综合评价: [1-2句总结性建议]
"""


# ===== LangGraph State =====

class AGraphState(TypedDict):
    grade: str
    total_score: float
    indicator_scores: List[Dict]
    position_name: str
    assessment_period: str
    review_report: Optional[ReviewReport]
    error: Optional[str]
    ui_callback: Optional[Any]


# ===== 节点 =====

@retry_and_validate(
    response_model=ReviewReport,
    max_attempts=3,
    system_prompt=REVIEW_SYSTEM,
    use_stream=True
)
def _generate_review_llm(
    grade: str,
    total_score: float,
    indicator_scores: List[Dict],
    position_name: str,
    assessment_period: str
) -> str:
    # 构建指标摘要
    scores_desc = ""
    for ind in indicator_scores:
        scores_desc += f"\n- {ind['name']}（权重{ind['weight']}%）：得分{ind['score']}，加权{ind['weighted_score']}"

    return f"""
{REVIEW_SYSTEM}

{REVIEW_FEW_SHOT}

---

请为以下员工生成专业的绩效复盘报告：

【基本信息】
- 岗位：{position_name}
- 考核周期：{assessment_period}
- 综合得分：{total_score}分
- 考核等级：{grade}级

【指标得分】
{scores_desc}

请返回 JSON 格式的复盘报告，包含：
- overall_summary: 整体评价（2-3句，风格与等级匹配）
- strengths: 优势指标列表（得分>=80的指标，每项含indicator/score/comment）
- development_areas: 待发展领域（得分<80的指标，每项含indicator/score/suggestion）

注意：风格要与等级匹配（S=激励强化，A=正向引导，B=建设性，C=直接改进）。
"""


async def generate_review_node(state: AGraphState) -> AGraphState:
    """复盘报告生成节点"""
    try:
        ui_callback = state.get("ui_callback")
        kwargs = {}
        if ui_callback:
            kwargs["ui_callback"] = ui_callback

        report = await run_sync_llm(
            _generate_review_llm,
            state["grade"],
            state["total_score"],
            state["indicator_scores"],
            state["position_name"],
            state["assessment_period"],
            **kwargs
        )
        return {**state, "review_report": report}
    except Exception as e:
        return {**state, "error": str(e)}


def build_a_graph():
    graph = StateGraph(AGraphState)
    graph.add_node("generate_review", generate_review_node)
    graph.set_entry_point("generate_review")
    graph.add_edge("generate_review", END)
    return graph.compile()


a_graph = build_a_graph()


async def run_a_stage(
    grade: str,
    total_score: float,
    indicator_scores: List[Dict],
    position_name: str,
    assessment_period: str,
    ui_callback=None,
) -> ReviewReport:
    """运行 A 阶段图"""
    initial_state = {
        "grade": grade,
        "total_score": total_score,
        "indicator_scores": indicator_scores,
        "position_name": position_name,
        "assessment_period": assessment_period,
        "review_report": None,
        "error": None,
        "ui_callback": ui_callback,
    }
    final_state = await a_graph.ainvoke(initial_state)
    if final_state.get("error"):
        raise Exception(final_state["error"])
    return final_state["review_report"]


@retry_and_validate(
    response_model=PlanReviewResult,
    max_attempts=3,
    system_prompt=PLAN_REVIEW_SYSTEM,
    use_stream=False
)
def _review_plan_llm(
    grade: str,
    development_areas: List[Dict],
    plan_goal: str,
    plan_actions: str,
    plan_resources: str,
    plan_timeline: str,
    feedback: str | None = None,
) -> str:
    """LLM 调用函数，返回 JSON 格式的计划审核结果"""
    dev_desc = "\n".join([
        f"- {d.get('indicator', '')}：{d.get('suggestion', '')}"
        for d in development_areas
    ]) or "无明显短板"

    prompt = f"""
{PLAN_REVIEW_FEW_SHOT}

---

请审核以下个人发展计划：

【背景】
- 本期考核等级：{grade}级
- 主要待发展领域：
{dev_desc}

【员工填写的发展计划】
- 目标：{plan_goal}
- 行动措施：{plan_actions}
- 需要资源：{plan_resources}
- 时间节点：{plan_timeline}
"""

    if feedback:
        prompt += f"\n【用户补充说明】\n{feedback}\n\n请在审核时特别关注用户提出的问题。\n"

    prompt += """
请返回 JSON 格式的审核结果，包含：

1. smart_evaluation: 对象，包含5个维度
   - specific: {{status: "✅/⚠️/❌", comment: "评价"}}
   - measurable: {{status: "✅/⚠️/❌", comment: "评价"}}
   - achievable: {{status: "✅/⚠️/❌", comment: "评价"}}
   - relevant: {{status: "✅/⚠️/❌", comment: "评价"}}
   - time_bound: {{status: "✅/⚠️/❌", comment: "评价"}}

2. polished_goals: 润色后的目标（Markdown 格式，保持原意但更具体、可衡量）
   - 不要使用 ** 加粗语法
   - 需要列举时只使用 1.、2.、3. 形式的有序列表，不要使用 - 开头的无序列表

3. polished_actions: 润色后的行动计划（Markdown 格式，补充时间节点和可衡量的里程碑）
   - 不要使用 ** 加粗语法
   - 需要列举时只使用 1.、2.、3. 形式的有序列表，不要使用 - 开头的无序列表

4. overall_review: 综合评价和建议（Markdown 格式，1-2段）

注意：润色时保持员工原意，只是让表述更符合 SMART 原则。
"""
    return prompt


async def review_plan(
    grade: str,
    development_areas: List[Dict],
    plan_goal: str,
    plan_actions: str,
    plan_resources: str,
    plan_timeline: str,
    feedback: str | None = None,
    ui_callback=None,
) -> Dict:
    """
    独立函数：AI 审核个人发展计划（非 LangGraph 节点）
    返回结构化的 SMART 评估和润色建议
    """
    result = await run_sync_llm(
        _review_plan_llm,
        grade=grade,
        development_areas=development_areas,
        plan_goal=plan_goal,
        plan_actions=plan_actions,
        plan_resources=plan_resources,
        plan_timeline=plan_timeline,
        feedback=feedback,
    )
    return {
        "smart_evaluation": {k: {"status": v.status, "comment": v.comment} for k, v in result.smart_evaluation.items()},
        "polished_goals": result.polished_goals,
        "polished_actions": result.polished_actions,
        "overall_review": result.overall_review,
    }
