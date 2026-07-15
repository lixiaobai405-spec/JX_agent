"""
P 阶段 LangGraph — 智能定标
节点：classify_node → generate_indicators_node → END
"""
import json
from typing import List, Literal, Optional, TypedDict
from pydantic import BaseModel
from langgraph.graph import StateGraph, END
from utils.llm import retry_and_validate, run_sync_llm
from sqlalchemy.ext.asyncio import AsyncSession
from graphs.db_helper import get_prototype_config


# ===== Pydantic 模型 =====

class ClassifyResult(BaseModel):
    score_quantifiability: int       # 1-10，量化可得性，仅展示
    score_output_cycle: int          # 1-10，产出周期，仅展示
    score_work_nature: int           # 1-10，工作性质，仅展示
    position_type: Literal["S", "P", "O", "F", "M"]
    position_type_name: str
    classification_reasoning: str
    confidence: float = 0.9          # 置信度，默认0.9


class Indicator(BaseModel):
    id: int
    name: str
    definition: str
    type: Literal["positive", "negative", "qualitative", "redline"]
    unit: str
    target: float
    target_display: str
    target_logic: str
    weight: int
    scoring_rule: str
    is_redline: bool
    source_suggestion_id: Optional[str] = None


class PStageResult(BaseModel):
    position_type: Literal["S", "P", "O", "F", "M"]
    position_type_name: str
    suggested_position_name: str
    classification_reasoning: str
    assessment_period: str
    indicators: List[Indicator]
    coaching_period: str
    result_application: str


# # ===== 策略配置 =====

# STRATEGY_CONFIG = {
#     "S": {
#         "name": "S类（铁军型）",
#         "description": "销售、渠道、门店等强结果导向岗位，产出高度可量化",
#         "assessment_period": "月度",
#         "indicator_count": "3-5个",
#         "quantitative_ratio": "定量指标 > 80%",
#         "coaching": "每周复盘+月度面谈",
#         "result_application": "挂钩当月绩效奖金系数；连续3个月S级可获职级晋升提名",
#         "redline_required": True,
#     },
#     "P": {
#         "name": "P类（项目型）",
#         "description": "研发、项目管理等以里程碑为主要产出的岗位",
#         "assessment_period": "季度",
#         "indicator_count": "5-7个",
#         "quantitative_ratio": "定性指标占比40%-60%",
#         "coaching": "双周节点Review",
#         "result_application": "挂钩季度项目专项奖金；考核B级以下取消新品署名权",
#         "redline_required": True,
#     },
#     "O": {
#         "name": "O类（运营型）",
#         "description": "运营、供应链等持续性、流程化工作岗位",
#         "assessment_period": "月度",
#         "indicator_count": "3-5个",
#         "quantitative_ratio": "定量指标 > 80%",
#         "coaching": "月度绩效面谈",
#         "result_application": "挂钩月度绩效奖金",
#         "redline_required": True,
#     },
#     "F": {
#         "name": "F类（职能型）",
#         "description": "HR、财务、法务等职能支持岗位",
#         "assessment_period": "季度",
#         "indicator_count": "5-7个",
#         "quantitative_ratio": "定性指标占比40%-60%，含内部客户满意度",
#         "coaching": "季度绩效面谈",
#         "result_application": "挂钩季度绩效奖金",
#         "redline_required": True,
#     },
#     "M": {
#         "name": "M类（管理型）",
#         "description": "团队负责人、部门总监等管理岗位",
#         "assessment_period": "半年度/年度",
#         "indicator_count": "5-7个，含团队指标",
#         "quantitative_ratio": "含团队整体目标达成+个人管理效能",
#         "coaching": "季度高管复盘",
#         "result_application": "挂钩年终绩效奖金及期权激励",
#         "redline_required": True,
#     },
# }

# ===== Few-shot 示例 =====

CLASSIFY_FEW_SHOT = """
【分类示例 — Few-shot】

示例1（S类）:
JD: 负责华东区便利系统销售目标达成、铺货率提升、回款管控及SOP执行
分类: S类（铁军型）
理由: 销售结果强量化，月度考核，执行导向

示例2（P类）:
JD: 负责气泡水新口味研发，从实验室到中试，以项目里程碑为主要产出，季度考核
分类: P类（项目型）
理由: 产出以里程碑为主，周期长，部分指标难以量化

示例3（O类）:
JD: 负责仓储物流调度，日常运营KPI（出库准时率、库存周转率），每日数据看板
分类: O类（运营型）
理由: 持续性流程化工作，可量化，无明确项目里程碑

示例4（F类）:
JD: 负责招聘、培训、员工关系，以内部客户满意度和HR SLA为考核维度
分类: F类（职能型）
理由: 职能支持性工作，定性指标占比较高，内部客户导向

示例5（M类）:
JD: 负责华东大区整体销售目标，管理5名销售经理，制定区域策略，对标年度OKR
分类: M类（管理型）
理由: 有明确团队管理职责，含团队指标，半年/年度考核
"""

CLASSIFY_SYSTEM = "你是一位专业的人力资源顾问，擅长岗位绩效设计。请以 JSON 格式返回分析结果。"

INDICATORS_SYSTEM = "你是一位专业的绩效指标设计专家。请严格按照指定格式返回 JSON 结果，确保权重合计=100（红线指标权重=0），至少包含1个红线指标。"


# ===== LangGraph State =====

class PGraphState(TypedDict):
    jd_text: str
    classify_result: Optional[ClassifyResult]
    p_stage_result: Optional[PStageResult]
    error: Optional[str]
    ui_callback: Optional[object]
    db: Optional[AsyncSession]


# ===== 节点函数 =====

@retry_and_validate(
    response_model=ClassifyResult,
    max_attempts=3,
    system_prompt=CLASSIFY_SYSTEM,
    use_stream=True
)
def _classify_llm(jd_text: str) -> str:
    return f"""
{CLASSIFY_FEW_SHOT}

请根据以下岗位职责描述（JD），对岗位进行分类。

【岗位职责描述】
{jd_text}

请返回 JSON 格式，包含以下字段：
- score_quantifiability: 量化可得性评分（1-10，仅供参考展示）
- score_output_cycle: 产出周期评分（1-10，周期越短分越高，仅供参考展示）
- score_work_nature: 工作性质评分（1-10，执行性越强分越高，仅供参考展示）
- position_type: 类型代码（"S"/"P"/"O"/"F"/"M"之一）
- position_type_name: 中文类型名称（如"铁军型"）
- classification_reasoning: 分类理由（2-3句话）

注意：三维评分仅用于图表展示，分类依据来自你对岗位特征的直接判断（参考上方示例）。
"""


@retry_and_validate(
    response_model=PStageResult,
    max_attempts=3,
    system_prompt=INDICATORS_SYSTEM,
    use_stream=True
)
def _generate_indicators_llm(
    jd_text: str,
    position_type: str,
    classify_result: ClassifyResult,
    strategy: dict,
    feedback: str | None = None,
    inherited_suggestions: List[dict] | None = None,
) -> str:

    prompt = f"""
你需要根据岗位职责和类型策略，为该岗位设计绩效考核指标体系。

【岗位职责描述】
{jd_text}

【岗位归类结果】
- 类型：{classify_result.position_type_name}（{position_type}类）
- 分类理由：{classify_result.classification_reasoning}

【策略配置要求】
- 考核周期：{strategy['assessment_period']}
- 指标数量：{strategy['indicator_count']}
- 量化比例：{strategy['quantitative_ratio']}
- 辅导周期：{strategy['coaching']}
- 结果应用：{strategy['result_application']}
- 必须包含红线指标：是

【强制规则】
1. 至少包含1个 type="redline" 的红线指标，is_redline=true，weight=0
2. 非红线指标的 weight 之和必须等于100
3. 指标类型：positive（正向量化）/ negative（反向量化）/ qualitative（定性）/ redline（红线）
4. target 字段为数字，target_display 为人类可读字符串
5. 结合JD内容，指标名称和定义要具体（引用JD中的产品/区域/系统名称）
"""

    if inherited_suggestions:
        suggestion_json = json.dumps(
            inherited_suggestions,
            ensure_ascii=False,
            sort_keys=True,
        )
        prompt += f"""

【已接受且尚未承接的上一周期建议】
{suggestion_json}

必须为上面每个建议生成且仅生成一个承接指标，并把建议的 id 原样写入该指标的
source_suggestion_id。不得遗漏、重复或虚构 source_suggestion_id。
"""

    if feedback:
        prompt += f"\n【用户反馈】\n{feedback}\n\n请根据用户反馈调整指标设计。\n"

    prompt += """
【参考示例 — S类华东KA销售经理】
指标1: 区域净销售额, type=positive, target=800, weight=45
指标2: 新品铺货率, type=positive, target=85, weight=20
指标3: 销售回款率, type=positive, target=98, weight=20
指标4: 巡店SOP执行, type=qualitative, target=92, weight=15
指标5: 乱价/串货行为, type=redline, is_redline=true, weight=0

【参考示例 — P类研发工程师】
指标1: 研发里程碑达成, type=positive, target=100, weight=20
指标2: 配方成本压降, type=positive, target=0.1, weight=20
指标3: 口感盲测评分, type=qualitative, target=4.5, weight=20
指标4: 新专利申请数, type=positive, target=1, weight=15
指标5: 跨部门协作满意度, type=qualitative, target=90, weight=15
指标6: 技术文档规范度, type=qualitative, target=90, weight=10
指标7: 食品安全/配方事故, type=redline, is_redline=true, weight=0

请返回完整的 JSON（PStageResult 格式），包含 position_type, position_type_name, suggested_position_name,
classification_reasoning, assessment_period, indicators（List），coaching_period, result_application 字段。
    indicators 中每个指标包含：id, name, definition, type, unit, target, target_display, target_logic, weight, scoring_rule, is_redline，
    以及可选的 source_suggestion_id（仅承接上述建议的指标填写）。
"""
    return prompt


async def classify_node(state: PGraphState) -> PGraphState:
    """分类节点"""
    try:
        ui_callback = state.get("ui_callback")
        kwargs = {}
        if ui_callback:
            kwargs["ui_callback"] = ui_callback

        result = await run_sync_llm(_classify_llm, state["jd_text"], **kwargs)
        return {**state, "classify_result": result}
    except Exception as e:
        return {**state, "error": str(e)}


async def generate_indicators_node(state: PGraphState) -> PGraphState:
    """指标生成节点"""
    if state.get("error"):
        return state
    try:
        ui_callback = state.get("ui_callback")
        kwargs = {}
        if ui_callback:
            kwargs["ui_callback"] = ui_callback

        classify_result = state["classify_result"]
        db = state.get("db")

        strategy = await get_prototype_config(db, classify_result.position_type)

        result = await run_sync_llm(
            _generate_indicators_llm,
            state["jd_text"],
            classify_result.position_type,
            classify_result,
            strategy,
            **kwargs
        )
        return {**state, "p_stage_result": result}
    except Exception as e:
        return {**state, "error": str(e)}


# ===== 构建图 =====

def build_p_graph():
    graph = StateGraph(PGraphState)
    graph.add_node("classify", classify_node)
    graph.add_node("generate_indicators", generate_indicators_node)
    graph.set_entry_point("classify")
    graph.add_edge("classify", "generate_indicators")
    graph.add_edge("generate_indicators", END)
    return graph.compile()


p_graph = build_p_graph()


async def run_p_stage(jd_text: str, db: AsyncSession = None, ui_callback=None) -> PStageResult:
    """运行 P 阶段图，返回 PStageResult"""
    initial_state = {
        "jd_text": jd_text,
        "classify_result": None,
        "p_stage_result": None,
        "error": None,
        "ui_callback": ui_callback,
        "db": db,
    }
    final_state = await p_graph.ainvoke(initial_state)
    if final_state.get("error"):
        raise Exception(final_state["error"])
    return final_state["p_stage_result"], final_state.get("classify_result")


async def run_classify_only(jd_text: str) -> ClassifyResult:
    """只运行分类，不生成指标"""
    classify_result = await run_sync_llm(_classify_llm, jd_text)
    return classify_result


async def run_generate_indicators(
    jd_text: str,
    classify_result: ClassifyResult,
    db: AsyncSession,
    feedback: str | None = None,
    inherited_suggestions: List[dict] | None = None,
) -> PStageResult:
    """根据分类结果生成指标"""
    strategy = await get_prototype_config(db, classify_result.position_type)
    p_result = await run_sync_llm(
        _generate_indicators_llm,
        jd_text,
        classify_result.position_type,
        classify_result,
        strategy,
        feedback,
        inherited_suggestions,
    )
    return p_result
