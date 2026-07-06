# P阶段 - 智能定标 API

## 模块概述

P阶段（Plan）负责智能定标，包括岗位分析、绩效合约生成等功能。

**核心流程**：
1. 岗位分析 - AI 分类岗位类型（S/P/O/F/M）
2. 合约生成 - 基于分析结果生成绩效指标
3. 合约确认 - 用户确认合约后创建目标和指标

## 涉及数据表

- `job_prototypes` - 岗位原型（S/P/O/F/M）
- `job_analyses` - 岗位分析结果
- `performance_contracts` - 绩效合约
- `indicator_templates` - 指标模板
- `goals` - 绩效目标（确认后创建）
- `indicators` - 绩效指标（确认后创建）

## 集成 LangGraph

- 岗位分析：调用 `graphs/p_graph.py` 的 `run_classify_only()` - 仅分类
- 合约生成：调用 `graphs/p_graph.py` 的 `run_generate_indicators()` - 生成指标

---

## 岗位分析

### 1. 创建岗位分析

**端点**: `POST /api/v1/plan/job-analysis`

**功能**: 使用 AI 分析岗位职责描述（JD），分类到 S/P/O/F/M 原型

**请求体**:
```json
{
  "user_id": "user-001",
  "jd_text": "负责华东区便利系统销售目标达成、铺货率提升、回款管控及SOP执行"
}
```

**成功响应** (200):
```json
{
  "id": "analysis-001",
  "user_id": "user-001",
  "jd_text": "负责华东区便利系统销售目标达成...",
  "job_prototype_code": "S",
  "quantifiability_score": 9,
  "output_cycle_score": 8,
  "work_nature_score": 9,
  "confidence": 0.9,
  "analysis_result": {
    "classify_result": {
      "position_type": "S",
      "position_type_name": "铁军型",
      "classification_reasoning": "该岗位职责明确聚焦销售结果..."
    }
  },
  "created_at": "2026-03-25T10:00:00Z"
}
```

**业务规则**:
- Employee 只能为自己创建分析
- Manager/HR Admin 可为团队成员创建

---

### 2. 获取岗位分析详情

**端点**: `GET /api/v1/plan/job-analysis/{analysis_id}`

---

### 3. 获取岗位分析列表

**端点**: `GET /api/v1/plan/job-analysis`

**查询参数**:
- `user_id`: 用户ID过滤（可选）

**权限过滤**:
- Employee: 仅返回自己的分析
- Manager: 返回自己和团队成员的分析
- HR Admin: 返回所有分析

---

## 绩效合约

### 4. 生成绩效合约

**端点**: `POST /api/v1/plan/contracts/generate`

**功能**: 基于岗位分析结果，使用 AI 生成绩效指标

**请求体**:
```json
{
  "period_id": "period-001",
  "user_id": "user-001",
  "job_analysis_id": "analysis-001",
  "feedback": "希望增加客户满意度指标，销售额权重降到40%"
}
```

**字段说明**:
- `feedback`: 可选，用户反馈用于调整生成结果
- 可多次调用生成不同版本的合约

**成功响应** (200):
```json
{
  "id": "contract-001",
  "goal_id": "goal-user-001-period-001-a1b2c3d4",
  "job_prototype_code": "S",
  "contract_data": {
    "indicators": [
      {
        "id": 1,
        "name": "华东区便利系统净销售额",
        "definition": "考核周期内实际完成的净销售额",
        "type": "positive",
        "unit": "万元",
        "target": 120.0,
        "target_display": "120万元",
        "weight": 40,
        "scoring_rule": "实际完成率=实际/目标*100%",
        "is_redline": false
      },
      {
        "id": 5,
        "name": "渠道乱价/串货行为",
        "type": "redline",
        "weight": 0,
        "is_redline": true
      }
    ],
    "period_id": "period-001",
    "assessment_period": "monthly",
    "coaching_period": "weekly",
    "result_application": "挂钩绩效奖金"
  },
  "ai_generated": true,
  "created_at": "2026-03-25T10:00:00Z"
}
```

**业务规则**:
- 非红线指标权重之和必须为 100
- 至少包含 1 个红线指标（weight=0）
- 每次生成的 goal_id 唯一，支持多次生成

---

### 5. 获取合约详情

**端点**: `GET /api/v1/plan/contracts/{contract_id}`

---

### 6. 确认合约

**端点**: `POST /api/v1/plan/contracts/{contract_id}/confirm`

**请求体**:
```json
{
  "confirmed_by": "user-001"
}
```

**业务规则**:
- 合约确认后不可再次确认

---

## 岗位原型管理

### 7. 获取原型列表

**端点**: `GET /api/v1/plan/prototypes`

---

### 8. 获取原型详情

**端点**: `GET /api/v1/plan/prototypes/{prototype_id}`

---

### 9. 更新原型

**端点**: `PUT /api/v1/plan/prototypes/{prototype_id}`

**权限**: HR Admin/System Admin

---

### 10. 删除原型

**端点**: `DELETE /api/v1/plan/prototypes/{prototype_id}`

**权限**: System Admin

---

## 指标模板

### 11. 获取模板列表

**端点**: `GET /api/v1/plan/templates`

**查询参数**:
- `prototype_code`: 原型代码（可选）

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| PLAN_001 | 岗位分析失败 |
| PLAN_002 | 合约生成失败 |
| PLAN_003 | 合约已确认，不可修改 |
| PLAN_004 | 指标权重之和必须为1.0 |
