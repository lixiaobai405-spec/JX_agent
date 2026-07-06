"""
Mock LLM Client — 用于在无 API Key 或网络受限时做本地功能测试
接口与 LLMClient 完全相同
"""
import json
from typing import Optional, Callable, Dict, Any

# ===== Mock 响应数据 =====

MOCK_CLASSIFY_S = {
    "score_quantifiability": 9,
    "score_output_cycle": 9,
    "score_work_nature": 8,
    "position_type": "S",
    "position_type_name": "铁军型",
    "classification_reasoning": "该岗位（华东KA销售经理）以销售额、铺货率等强量化指标为主，考核周期为月度，工作性质属于执行型销售，具有高度可量化、短产出周期的特征，因此归类为S类（铁军型）。"
}

MOCK_INDICATORS_S = {
    "position_type": "S",
    "position_type_name": "铁军型",
    "suggested_position_name": "华东KA销售经理",
    "classification_reasoning": "以销售结果为核心，月度考核，强执行力导向，归类S类。",
    "assessment_period": "月度",
    "coaching_period": "每周五下午17:00提交《周销售复盘表》；次月5日前完成月度面谈",
    "result_application": "挂钩当月绩效奖金系数；连续3个月S级可获职级晋升提名",
    "indicators": [
        {
            "id": 1,
            "name": "区域净销售额",
            "definition": "华东区便利系统当月实际开票销售额",
            "type": "positive",
            "unit": "万元",
            "target": 800.0,
            "target_display": "800万元",
            "target_logic": "自上而下（年度目标分解）",
            "weight": 45,
            "scoring_rule": "(实际/目标)*100%，上限150%",
            "is_redline": False
        },
        {
            "id": 2,
            "name": "新品铺货率",
            "definition": "\"果气森林\"在目标门店的入柜比例",
            "type": "positive",
            "unit": "%",
            "target": 85.0,
            "target_display": "85%",
            "target_logic": "自上而下（公司战略推导）",
            "weight": 20,
            "scoring_rule": "100%达成满分，每低1%扣5分",
            "is_redline": False
        },
        {
            "id": 3,
            "name": "销售回款率",
            "definition": "实际到账回款 / 月度应收账款",
            "type": "positive",
            "unit": "%",
            "target": 98.0,
            "target_display": "98%",
            "target_logic": "历史推导（过去12月均值+5%）",
            "weight": 20,
            "scoring_rule": "(实际/目标)*100%",
            "is_redline": False
        },
        {
            "id": 4,
            "name": "巡店SOP执行",
            "definition": "督导抽查陈列、价签、物料的平均得分",
            "type": "qualitative",
            "unit": "分",
            "target": 92.0,
            "target_display": "92分",
            "target_logic": "外部标杆（对标行业Top企业）",
            "weight": 15,
            "scoring_rule": "优秀=100%, 良好=80%, 合格=60%, 不合格=0%",
            "is_redline": False
        },
        {
            "id": 5,
            "name": "乱价/串货行为",
            "definition": "擅自破价或跨区违规供货次数",
            "type": "redline",
            "unit": "次",
            "target": 0.0,
            "target_display": "0次",
            "target_logic": "红线设定",
            "weight": 0,
            "scoring_rule": "发生1起视为触发红线，整体扣20分",
            "is_redline": True
        }
    ]
}

MOCK_CLASSIFY_P = {
    "score_quantifiability": 5,
    "score_output_cycle": 3,
    "score_work_nature": 4,
    "position_type": "P",
    "position_type_name": "项目型",
    "classification_reasoning": "该岗位（气泡水研发高级工程师）以里程碑节点和研发成果为主要产出，考核周期为季度，工作性质偏研发创新，部分指标难以量化，归类为P类（项目型）。"
}

MOCK_INDICATORS_P = {
    "position_type": "P",
    "position_type_name": "项目型",
    "suggested_position_name": "气泡水研发高级工程师",
    "classification_reasoning": "以项目里程碑和研发成果为导向，季度考核，归类P类。",
    "assessment_period": "季度",
    "coaching_period": "每双周周三进行研发节点Review，跟进项目阻碍",
    "result_application": "挂钩季度项目专项奖金；考核B级以下取消新品署名权",
    "indicators": [
        {
            "id": 1,
            "name": "研发里程碑达成",
            "definition": "新口味中试投产的时间节点",
            "type": "positive",
            "unit": "完成率%",
            "target": 100.0,
            "target_display": "按期完成",
            "target_logic": "自我设定（依项目计划上报）",
            "weight": 20,
            "scoring_rule": "按期100%，延期按天折算",
            "is_redline": False
        },
        {
            "id": 2,
            "name": "配方成本压降",
            "definition": "单瓶气泡水原材料成本降低额",
            "type": "positive",
            "unit": "元",
            "target": 0.1,
            "target_display": "压降0.1元",
            "target_logic": "自上而下（财务利润分解）",
            "weight": 20,
            "scoring_rule": "(实际/目标)*100%",
            "is_redline": False
        },
        {
            "id": 3,
            "name": "口感盲测评分",
            "definition": "消费者盲测及评审团的主观评分",
            "type": "qualitative",
            "unit": "分",
            "target": 4.5,
            "target_display": "4.5分",
            "target_logic": "外部标杆（竞品爆款得分）",
            "weight": 20,
            "scoring_rule": "优秀=100%, 良好=80%, 合格=60%, 不合格=0%",
            "is_redline": False
        },
        {
            "id": 4,
            "name": "新专利申请数",
            "definition": "提交发明或实用新型专利数量",
            "type": "positive",
            "unit": "项",
            "target": 1.0,
            "target_display": "1项",
            "target_logic": "自我设定（员工自主规划）",
            "weight": 15,
            "scoring_rule": "达成计分，未达成计0分",
            "is_redline": False
        },
        {
            "id": 5,
            "name": "跨部门协作满意度",
            "definition": "生产部对转产技术支持的评价打分",
            "type": "qualitative",
            "unit": "分",
            "target": 90.0,
            "target_display": "90分",
            "target_logic": "历史推导（去年部门协作分）",
            "weight": 15,
            "scoring_rule": "优秀=100%, 良好=80%, 合格=60%, 不合格=0%",
            "is_redline": False
        },
        {
            "id": 6,
            "name": "技术文档规范度",
            "definition": "实验数据与SOP文档的合规性",
            "type": "qualitative",
            "unit": "等级",
            "target": 90.0,
            "target_display": "优(90+)",
            "target_logic": "自我设定（AI博弈建议标准）",
            "weight": 10,
            "scoring_rule": "优秀=100%, 良好=80%, 合格=60%, 不合格=0%",
            "is_redline": False
        },
        {
            "id": 7,
            "name": "食品安全/配方事故",
            "definition": "研发配方缺陷导致的质量事故",
            "type": "redline",
            "unit": "次",
            "target": 0.0,
            "target_display": "0次",
            "target_logic": "红线设定",
            "weight": 0,
            "scoring_rule": "发生即判定不合格，一票否决",
            "is_redline": True
        }
    ]
}

MOCK_FEEDBACK = """
## 根因分析

**🔴 区域净销售额（达成率 75%）**
- **根因**：华东区便利系统新品铺货节奏滞后，导致终端动销不足；竞争对手元气森林同期加大促销力度，抢占货架资源。
- **改进建议**：
  1. 本周内联系全家、罗森区域负责人，确认"果气森林"剩余铺货计划，争取月底前完成85%覆盖
  2. 申请市场部支持2场终端促销活动（买赠/第二件半价），提升动销速度
  3. 每日追踪TOP20门店销售数据，对低于均值门店进行重点拜访

**🟡 销售回款率（达成率 90%）**
- **根因**：部分经销商账期管控不严，月末集中开票影响回款节奏。
- **改进建议**：
  1. 每周二发送回款催收提醒，重点跟进5家逾期超7天的客户
  2. 与财务部确认下月账期条款调整可行性
"""

MOCK_RESULT_SHEET = """
# 绩效结果确认单

**员工姓名**：张XX
**考核周期**：2024年3月
**岗位**：华东KA销售经理
**考核等级**：**A级**

## 指标得分明细

| 指标名称 | 权重 | 得分 | 加权得分 |
|---------|------|------|---------|
| 区域净销售额 | 45% | 85 | 38.25 |
| 新品铺货率 | 20% | 90 | 18.00 |
| 销售回款率 | 20% | 88 | 17.60 |
| 巡店SOP执行 | 15% | 92 | 13.80 |
| **合计** | **100%** | - | **87.65** |

## 评价人评语

该员工本月在新品铺货方面表现积极，果气森林铺货率超额完成。销售回款稳健，SOP执行到位。建议在核心门店销售额冲刺方面加大资源投入，争取下月回到S级水平。

**评价人签字**：___________
**日期**：___________
"""

MOCK_REVIEW_REPORT = {
    "overall_summary": "本考核期整体表现良好（A级），在新品推广和SOP执行方面表现突出，核心销售指标有待进一步强化。",
    "strengths": [
        {"indicator": "新品铺货率", "score": 90.0, "comment": "果气森林铺货率达90%，超额完成公司战略目标，体现了强执行力和客户关系管理能力。"},
        {"indicator": "巡店SOP执行", "score": 92.0, "comment": "SOP执行严格规范，督导抽查得分优秀，为品牌形象维护做出贡献。"}
    ],
    "development_areas": [
        {"indicator": "区域净销售额", "score": 85.0, "suggestion": "建议聚焦TOP门店动销提升，联合市场部开展终端促销，在现有渠道基础上挖掘增量空间。"}
    ]
}


class MockLLMClient:
    """返回预定义响应，用于本地测试，接口与 LLMClient 完全相同"""

    def __init__(self):
        self.model = "mock-model"
        self._call_count = 0

    def call_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4000,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> str:
        """根据 prompt 关键词返回对应的 mock JSON 或文本"""
        self._call_count += 1

        # 模拟 token 回调
        if callback:
            callback({"type": "token_update", "total_tokens": 50, "speed": 120.0})

        # 分类节点
        if "归类" in prompt or "position_type" in prompt or "classify" in prompt.lower():
            if "研发" in prompt or "工程师" in prompt or "P类" in prompt:
                return json.dumps(MOCK_CLASSIFY_P, ensure_ascii=False)
            return json.dumps(MOCK_CLASSIFY_S, ensure_ascii=False)

        # 指标生成节点
        if "指标" in prompt or "indicators" in prompt or "Indicator" in prompt:
            if "P类" in prompt or "项目型" in prompt or "研发" in prompt:
                return json.dumps(MOCK_INDICATORS_P, ensure_ascii=False)
            return json.dumps(MOCK_INDICATORS_S, ensure_ascii=False)

        # 复盘报告
        if "review" in prompt.lower() or "复盘" in prompt or "ReviewReport" in prompt:
            return json.dumps(MOCK_REVIEW_REPORT, ensure_ascii=False)

        # 结果确认单
        if "结果确认单" in prompt or "result_sheet" in prompt.lower():
            return MOCK_RESULT_SHEET

        # 根因分析 & 改进建议
        if "根因" in prompt or "改进" in prompt or "feedback" in prompt.lower():
            return MOCK_FEEDBACK

        # 计划审核
        if "SMART" in prompt or "计划" in prompt:
            return """
## AI 计划审核反馈

**SMART 检验**：
- ✅ **具体性（S）**：目标描述清晰，聚焦核心销售指标
- ✅ **可衡量（M）**：有明确数字目标
- ⚠️ **可实现（A）**：建议结合历史数据评估目标难度
- ✅ **相关性（R）**：与岗位职责高度相关
- ✅ **时限性（T）**：有明确时间节点

**可行性评估**：计划整体可行，建议在行动措施中增加具体的周度检查点。

**资源建议**：可申请市场部支持1-2场终端促销活动，配合销售冲刺。

**关联度评估**：与本期考核短板（核心销售额）高度关联，方向正确。
"""

        # 默认返回
        return "Mock 响应：该场景暂无预定义内容，请检查 prompt 关键词。"
