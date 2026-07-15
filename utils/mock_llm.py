"""
Mock LLM Client — 用于在无 API Key 或网络受限时做本地功能测试。
接口与 LLMClient 保持一致。
"""

import json
from typing import Any, Callable, Dict, Optional


MOCK_CLASSIFICATIONS = {
    "S": {
        "score_quantifiability": 9,
        "score_output_cycle": 9,
        "score_work_nature": 7,
        "position_type": "S",
        "position_type_name": "铁军型",
        "classification_reasoning": "该岗位负责华东便利系统销售额、铺货率和回款目标，结果高度量化且按月推进；销售过程存在策略空间，但核心产出必须兑现，因此归类为S类铁军型。",
        "features": ["高量化销售结果", "月度短周期", "渠道执行与客户谈判并重"],
        "confidence": 0.96,
    },
    "P": {
        "score_quantifiability": 3,
        "score_output_cycle": 3,
        "score_work_nature": 2,
        "position_type": "P",
        "position_type_name": "项目型",
        "classification_reasoning": "该岗位围绕气泡水新口味研发、中试生产、专利和转产协作展开，产出以里程碑和研发成果为主，周期较长且创造性强，因此归类为P类项目型。",
        "features": ["研发里程碑", "季度长周期", "创新探索和跨部门协作"],
        "confidence": 0.95,
    },
    "O": {
        "score_quantifiability": 9,
        "score_output_cycle": 9,
        "score_work_nature": 10,
        "position_type": "O",
        "position_type_name": "运营型",
        "classification_reasoning": "该岗位负责灌装线产量、次品率、停机时长和生产SOP执行，数据高频可得且流程标准化，因此归类为O类运营型。",
        "features": ["高频生产数据", "月度短周期", "SOP标准化作业"],
        "confidence": 0.96,
    },
    "F": {
        "score_quantifiability": 4,
        "score_output_cycle": 8,
        "score_work_nature": 7,
        "position_type": "F",
        "position_type_name": "职能型",
        "classification_reasoning": "该岗位以招聘响应、入职手续、候选人体验和业务部门满意度为核心，属于高频服务支持工作，定性评价占比较高，因此归类为F类职能型。",
        "features": ["职能支持", "高频响应", "内部客户和候选人体验"],
        "confidence": 0.94,
    },
    "M": {
        "score_quantifiability": 4,
        "score_output_cycle": 2,
        "score_work_nature": 2,
        "position_type": "M",
        "position_type_name": "管理型",
        "classification_reasoning": "该岗位统筹供应链战略、仓储自动化、供应商管理和团队梯队建设，目标具有组织战略分解和长周期管理特征，因此归类为M类管理型。",
        "features": ["战略规划", "半年度长周期", "团队赋能与组织结果"],
        "confidence": 0.95,
    },
}


MOCK_INDICATORS = {
    "S": {
        "position_type": "S",
        "position_type_name": "铁军型",
        "suggested_position_name": "华东KA销售经理",
        "classification_reasoning": MOCK_CLASSIFICATIONS["S"]["classification_reasoning"],
        "assessment_period": "月度",
        "coaching_period": "每周五下午17:00提交《周销售复盘表》；次月5日前完成月度面谈",
        "result_application": "挂钩当月绩效奖金系数；连续3个月S级可获职级晋升提名",
        "indicators": [
            {"id": 1, "name": "区域净销售额", "definition": "华东区便利系统当月实际开票销售额", "type": "positive", "unit": "万元", "target": 800.0, "target_display": "800万元", "target_logic": "自上而下（年度目标分解）", "weight": 45, "scoring_rule": "(实际/目标)*100%", "is_redline": False},
            {"id": 2, "name": "新品铺货率", "definition": "“果气森林”在目标门店的入柜比例", "type": "positive", "unit": "%", "target": 85.0, "target_display": "85%", "target_logic": "自上而下（公司战略推导）", "weight": 20, "scoring_rule": "100%达成满分，每低1%扣5分", "is_redline": False},
            {"id": 3, "name": "销售回款率", "definition": "实际到账回款 / 月度应收账款", "type": "positive", "unit": "%", "target": 98.0, "target_display": "98%", "target_logic": "历史推导（过去12月均值+5%）", "weight": 20, "scoring_rule": "(实际/目标)*100%", "is_redline": False},
            {"id": 4, "name": "巡店SOP执行", "definition": "督导抽查陈列、价签、物料的平均得分", "type": "qualitative", "unit": "分", "target": 92.0, "target_display": "92分", "target_logic": "外部标杆（对标行业Top企业）", "weight": 15, "scoring_rule": "实际得分即为该项得分", "is_redline": False},
            {"id": 5, "name": "乱价/串货行为", "definition": "擅自破价或跨区违规供货", "type": "redline", "unit": "起", "target": 0.0, "target_display": "0起", "target_logic": "红线设定", "weight": 0, "scoring_rule": "发生1起扣20分", "is_redline": True},
        ],
    },
    "P": {
        "position_type": "P",
        "position_type_name": "项目型",
        "suggested_position_name": "气泡水研发高级工程师",
        "classification_reasoning": MOCK_CLASSIFICATIONS["P"]["classification_reasoning"],
        "assessment_period": "季度",
        "coaching_period": "每双周周三进行研发节点Review，跟进项目阻碍",
        "result_application": "挂钩季度项目专项奖金；考核B级以下取消新品署名权",
        "indicators": [
            {"id": 1, "name": "研发里程碑达成", "definition": "新口味中试投产的时间节点", "type": "positive", "unit": "完成率%", "target": 100.0, "target_display": "10月15日", "target_logic": "自我设定（依项目计划上报）", "weight": 20, "scoring_rule": "按期100%，延期按天折算", "is_redline": False},
            {"id": 2, "name": "配方成本压降", "definition": "单瓶气泡水原材料成本降低额", "type": "positive", "unit": "元", "target": 0.1, "target_display": "压降0.1元", "target_logic": "自上而下（财务利润分解）", "weight": 20, "scoring_rule": "(实际/目标)*100%", "is_redline": False},
            {"id": 3, "name": "口感盲测评分", "definition": "消费者盲测及评审团的主观评分", "type": "qualitative", "unit": "分", "target": 4.5, "target_display": "4.5分", "target_logic": "外部标杆（竞品爆款得分）", "weight": 20, "scoring_rule": "专家与消费者打分加权平均", "is_redline": False},
            {"id": 4, "name": "新专利申请数", "definition": "提交发明或实用新型专利数量", "type": "positive", "unit": "项", "target": 1.0, "target_display": "1项", "target_logic": "自我设定（员工自主规划）", "weight": 15, "scoring_rule": "达成计分，未达成计0分", "is_redline": False},
            {"id": 5, "name": "跨部门协作满意度", "definition": "生产部对转产技术支持的评价打分", "type": "qualitative", "unit": "分", "target": 90.0, "target_display": "90分", "target_logic": "历史推导（去年部门协作分）", "weight": 15, "scoring_rule": "360度内部客户问卷打分", "is_redline": False},
            {"id": 6, "name": "技术文档规范度", "definition": "实验数据与SOP文档的合规性", "type": "qualitative", "unit": "等级", "target": 90.0, "target_display": "优(90+)", "target_logic": "自我设定（AI博弈建议标准）", "weight": 10, "scoring_rule": "上级抽查评估等级", "is_redline": False},
            {"id": 7, "name": "食品安全/配方事故", "definition": "研发配方缺陷导致的质量事故", "type": "redline", "unit": "起", "target": 0.0, "target_display": "0起", "target_logic": "红线设定", "weight": 0, "scoring_rule": "发生即判定不合格，一票否决", "is_redline": True},
        ],
    },
    "O": {
        "position_type": "O",
        "position_type_name": "运营型",
        "suggested_position_name": "饮料灌装线线长",
        "classification_reasoning": MOCK_CLASSIFICATIONS["O"]["classification_reasoning"],
        "assessment_period": "月度",
        "coaching_period": "每日早班会通报昨日产量与次品率；每周进行周度效率复盘",
        "result_application": "全额挂钩计件与产线效率奖金；连续优胜获“标杆线长”称号",
        "indicators": [
            {"id": 1, "name": "产量计划达成率", "definition": "实际完工入库量 / 周排产计划量", "type": "positive", "unit": "%", "target": 100.0, "target_display": "100%", "target_logic": "自上而下（依据总订单排产）", "weight": 40, "scoring_rule": "(实际/目标)*100%", "is_redline": False},
            {"id": 2, "name": "生产次品率", "definition": "质检不合格数 / 总产出量", "type": "negative", "unit": "%", "target": 0.5, "target_display": "<0.5%", "target_logic": "历史推导（过去12月均值改善）", "weight": 30, "scoring_rule": "低于目标计满分，超标扣分", "is_redline": False},
            {"id": 3, "name": "非计划停机时长", "definition": "设备故障导致的意外停机总小时数", "type": "negative", "unit": "小时", "target": 10.0, "target_display": "<10小时", "target_logic": "历史推导（设备年度维保数据）", "weight": 20, "scoring_rule": "偏差值判定，超出目标比例扣分", "is_redline": False},
            {"id": 4, "name": "现场6S抽查得分", "definition": "质监部对车间整理、清洁的随机打分", "type": "positive", "unit": "分", "target": 95.0, "target_display": "95分", "target_logic": "自上而下（工厂统一管理标准）", "weight": 10, "scoring_rule": "实际得分即为该项得分", "is_redline": False},
            {"id": 5, "name": "重大安全生产事故", "definition": "人身伤亡或重大设备损坏事故", "type": "redline", "unit": "起", "target": 0.0, "target_display": "0起", "target_logic": "红线设定", "weight": 0, "scoring_rule": "发生即判定不合格，一票否决", "is_redline": True},
        ],
    },
    "F": {
        "position_type": "F",
        "position_type_name": "职能型",
        "suggested_position_name": "华东区招聘专员",
        "classification_reasoning": MOCK_CLASSIFICATIONS["F"]["classification_reasoning"],
        "assessment_period": "月度",
        "coaching_period": "每周五下午进行招聘漏斗数据盘点；每半月与用人部门对齐画像",
        "result_application": "挂钩职能序列月度绩效奖金；年终等级作为调薪核心依据",
        "indicators": [
            {"id": 1, "name": "招聘到岗达成率", "definition": "实际报到人数 / 当月核批需求人数", "type": "positive", "unit": "%", "target": 85.0, "target_display": "85%", "target_logic": "自我设定（月底与主管确认排期）", "weight": 25, "scoring_rule": "(实际/目标)*100%", "is_redline": False},
            {"id": 2, "name": "业务部门满意度", "definition": "用人部门对推介简历精准度的主观打分", "type": "qualitative", "unit": "分", "target": 90.0, "target_display": "90分", "target_logic": "自我设定（目标值由员工填报申请）", "weight": 20, "scoring_rule": "内部客户评价打分", "is_redline": False},
            {"id": 3, "name": "人均招聘费用控制", "definition": "渠道支出费 / 实际入职人数", "type": "negative", "unit": "元", "target": 2000.0, "target_display": "<2000元", "target_logic": "历史推导（去年同岗位平均成本）", "weight": 15, "scoring_rule": "低于目标加分，超出扣分", "is_redline": False},
            {"id": 4, "name": "候选人体验评分", "definition": "面试者对应聘流程和态度的问卷反馈", "type": "qualitative", "unit": "分", "target": 4.5, "target_display": "4.5分", "target_logic": "外部标杆（互联网标杆招聘体验分）", "weight": 15, "scoring_rule": "问卷加权平均分", "is_redline": False},
            {"id": 5, "name": "入职手续办理合规率", "definition": "劳动合约、档案收集的准确度", "type": "qualitative", "unit": "%", "target": 100.0, "target_display": "100%", "target_logic": "自上而下（审计与风控要求）", "weight": 15, "scoring_rule": "抽查1份错漏扣5分", "is_redline": False},
            {"id": 6, "name": "简历库沉淀数", "definition": "每月新增入库备用人才简历数量", "type": "positive", "unit": "份", "target": 200.0, "target_display": "200份", "target_logic": "自我设定（AI建议参考值）", "weight": 10, "scoring_rule": "绝对数值计分", "is_redline": False},
            {"id": 7, "name": "隐私数据泄露", "definition": "未经授权泄露候选人薪资/隐私信息", "type": "redline", "unit": "起", "target": 0.0, "target_display": "0起", "target_logic": "红线设定", "weight": 0, "scoring_rule": "发现1起扣30分", "is_redline": True},
        ],
    },
    "M": {
        "position_type": "M",
        "position_type_name": "管理型",
        "suggested_position_name": "供应链总监",
        "classification_reasoning": MOCK_CLASSIFICATIONS["M"]["classification_reasoning"],
        "assessment_period": "半年度",
        "coaching_period": "每月与CEO进行一次经营分析会；每季度召开供应商大会",
        "result_application": "挂钩公司半年度利润分红池；影响高管长期股权激励解禁比例",
        "indicators": [
            {"id": 1, "name": "端到端单件履约成本", "definition": "采购+制造成本+物流均摊的总降本率", "type": "positive", "unit": "%", "target": 8.0, "target_display": "压降8%", "target_logic": "自上而下（公司年度经营预算表）", "weight": 30, "scoring_rule": "降本达成率计算", "is_redline": False},
            {"id": 2, "name": "总体库存周转天数", "definition": "原物料与成品在库的平均流转天数", "type": "negative", "unit": "天", "target": 28.0, "target_display": "28天", "target_logic": "外部标杆（快消行业Top级周转标准）", "weight": 20, "scoring_rule": "低于目标值计满分", "is_redline": False},
            {"id": 3, "name": "战略规划：仓储自动化", "definition": "无人仓一期工程落地及试运行通过率", "type": "qualitative", "unit": "%", "target": 100.0, "target_display": "100%", "target_logic": "自上而下（公司战略级项目任务）", "weight": 20, "scoring_rule": "CEO对里程碑验收评价", "is_redline": False},
            {"id": 4, "name": "供应商交付达标率", "definition": "核心供应商半年度OTIF(按时全量交付)", "type": "positive", "unit": "%", "target": 95.0, "target_display": "95%", "target_logic": "历史推导（去年均值提升设定）", "weight": 15, "scoring_rule": "数据拉取计算", "is_redline": False},
            {"id": 5, "name": "管理层梯队建设", "definition": "供应链体系经理级储备人才培养数量", "type": "qualitative", "unit": "人", "target": 3.0, "target_display": "3人", "target_logic": "自我设定（总监年度述职承诺）", "weight": 15, "scoring_rule": "人力资源盘点认定", "is_redline": False},
            {"id": 6, "name": "重大廉洁/合规事件", "definition": "采购招标或物流寻源中的贪腐违规", "type": "redline", "unit": "起", "target": 0.0, "target_display": "0起", "target_logic": "红线设定", "weight": 0, "scoring_rule": "发生即开除并移交法务", "is_redline": True},
        ],
    },
}


MOCK_CLASSIFY_S = MOCK_CLASSIFICATIONS["S"]
MOCK_CLASSIFY_P = MOCK_CLASSIFICATIONS["P"]
MOCK_CLASSIFY_O = MOCK_CLASSIFICATIONS["O"]
MOCK_CLASSIFY_F = MOCK_CLASSIFICATIONS["F"]
MOCK_CLASSIFY_M = MOCK_CLASSIFICATIONS["M"]

MOCK_INDICATORS_S = MOCK_INDICATORS["S"]
MOCK_INDICATORS_P = MOCK_INDICATORS["P"]
MOCK_INDICATORS_O = MOCK_INDICATORS["O"]
MOCK_INDICATORS_F = MOCK_INDICATORS["F"]
MOCK_INDICATORS_M = MOCK_INDICATORS["M"]


MOCK_FEEDBACK = """
## 根因分析

**🔴 区域净销售额（达成率 75%）**
- **根因**：华东区便利系统新品铺货节奏滞后，导致终端动销不足；竞争对手同期加大促销力度，抢占货架资源。
- **改进建议**：
  1. 本周内联系全家、罗森区域负责人，确认“果气森林”剩余铺货计划。
  2. 申请市场部支持终端促销活动，提升动销速度。
  3. 每日追踪TOP20门店销售数据，对低于均值门店进行重点拜访。
"""


MOCK_RESULT_SHEET = """
# 绩效结果确认单

**员工姓名**：王强
**岗位**：华东KA销售经理
**考核等级**：B级
"""


MOCK_REVIEW_REPORT = {
    "overall_summary": "本考核期整体符合预期，但核心便利系统转化和新品铺货仍需强化。",
    "strengths": [
        {"indicator": "销售回款率", "score": 92.0, "comment": "大客户回款稳定，体现了较好的过程跟进。"}
    ],
    "development_areas": [
        {"indicator": "区域净销售额", "score": 76.0, "suggestion": "建议聚焦TOP门店动销提升，联合市场部开展终端促销。"},
        {"indicator": "新品铺货率", "score": 80.0, "suggestion": "建议按便利系统分层推进谈判，缩短重点门店入柜周期。"},
    ],
}


MOCK_PLAN_REVIEW = {
    "smart_evaluation": {
        "specific": {"status": "✅", "comment": "目标聚焦重点便利系统客户转化和新品铺货，对象明确。"},
        "measurable": {"status": "✅", "comment": "以新品铺货率达到85%以上作为验收标准，可量化追踪。"},
        "achievable": {"status": "⚠️", "comment": "目标可实现，但需要上级协助复盘关键客户谈判策略。"},
        "relevant": {"status": "✅", "comment": "计划直接对应区域净销售额和新品铺货率短板。"},
        "time_bound": {"status": "✅", "comment": "已设置8月底和9月底两个明确时间节点。"},
    },
    "polished_goals": "提升重点便利系统客户转化率，2026年8月底前将华东区核心门店新品铺货率提升到85%以上。",
    "polished_actions": "每周复盘3个失败谈判案例，形成客户类型、异议点和报价话术记录；每周五向李娜提交铺货推进清单，并同步下周重点门店计划。",
    "overall_review": "该发展计划与本期绩效短板关联清晰，建议补充每周过程数据和上级辅导记录，便于后续复盘继承。",
}


KEYWORDS = {
    "S": ("华东区全家", "便利系统", "新品铺货"),
    "P": ("气泡水新口味", "中试生产", "产品专利"),
    "O": ("灌装线", "生产SOP", "次品率"),
    "F": ("招聘", "候选人", "入职手续"),
    "M": ("供应链", "仓储自动化", "供应商"),
}


def _extract_jd(prompt: str) -> str:
    marker = "【岗位职责描述】"
    if marker not in prompt:
        return prompt
    text = prompt.split(marker, 1)[1]
    for end_marker in ("【岗位归类结果】", "【策略配置要求】", "请返回 JSON", "请返回完整的 JSON"):
        if end_marker in text:
            text = text.split(end_marker, 1)[0]
    return text


def _case_code(prompt: str) -> str:
    jd_text = _extract_jd(prompt)
    for code, keywords in KEYWORDS.items():
        if any(keyword in jd_text for keyword in keywords):
            return code
    for code in ("S", "P", "O", "F", "M"):
        if f"{code}类" in prompt or MOCK_CLASSIFICATIONS[code]["position_type_name"] in prompt:
            return code
    return "S"


class MockLLMClient:
    """返回预定义响应，用于本地测试，接口与 LLMClient 完全相同。"""

    def __init__(self):
        self.model = "mock-model"
        self._call_count = 0

    def call_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4000,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> str:
        self._call_count += 1

        if callback:
            callback({"type": "token_update", "total_tokens": 50, "speed": 120.0})

        if (
            "请返回完整的 JSON" in prompt
            or "coaching_period" in prompt
            or "result_application" in prompt
            or "indicators" in prompt
            or "Indicator" in prompt
        ):
            return json.dumps(MOCK_INDICATORS[_case_code(prompt)], ensure_ascii=False)

        if "归类" in prompt or "position_type" in prompt or "classify" in prompt.lower():
            return json.dumps(MOCK_CLASSIFICATIONS[_case_code(prompt)], ensure_ascii=False)

        if "smart_evaluation" in prompt or "polished_goals" in prompt:
            return json.dumps(MOCK_PLAN_REVIEW, ensure_ascii=False)

        if "overall_summary" in prompt and "development_areas" in prompt:
            return json.dumps(MOCK_REVIEW_REPORT, ensure_ascii=False)

        if "结果确认单" in prompt or "result_sheet" in prompt.lower():
            return MOCK_RESULT_SHEET

        if "根因" in prompt or "改进" in prompt or "feedback" in prompt.lower():
            return MOCK_FEEDBACK

        return "Mock 响应：该场景暂无预定义内容，请检查 prompt 关键词。"
