# C阶段 - 考核评估 API

## 模块概述

C阶段（Check）负责考核评估，包括自评、他评、分数计算、AI报告生成、结果确认等功能。

**核心流程**：
1. 自评 - 员工提交自我评价
2. 他评 - 上级提交评价打分
3. 算分 - 系统计算加权总分
4. AI报告 - 生成结果确认单
5. 结果确认 - 员工确认或HR调整

## 涉及数据表

- `goals` - 目标（复用P阶段创建的）
- `indicators` - 指标（复用P阶段创建的）
- `self_assessments` - 自评
- `evaluation_tasks` - 评价任务
- `evaluations` - 评价记录
- `score_aggregates` - 分数汇总
- `final_results` - 最终结果

## 集成 LangGraph

- AI报告生成：调用 `graphs/c_graph.py` 的 `run_c_stage()` - 生成结果确认单
- 分数计算：调用 `utils/calculations.py` 的 `calculate_c_stage()` - 计算加权分数

---

## 目标和指标查询（复用D阶段接口）

### 1. 获取当前目标

**端点**: `GET /api/v1/do/goals/current`

**查询参数**:
- `period_id`: 周期ID（必填）

**成功响应** (200):
```json
{
  "id": "goal-001",
  "owner_user_id": "user-001",
  "period_id": "period-001",
  "title": "绩效目标-S",
  "description": null,
  "created_at": "2026-03-01T00:00:00Z"
}
```

---

### 2. 获取目标的指标列表

**端点**: `GET /api/v1/do/goals/{goal_id}/indicators`

**成功响应** (200):
```json
[
  {
    "id": "indicator-001",
    "goal_id": "goal-001",
    "name": "月度销售额",
    "definition": "华东区便利系统当月实际开票销售额",
    "direction": "positive",
    "weight": 0.45,
    "target_value": 8000000,
    "score_method": "ratio",
    "redline": false,
    "created_at": "2026-03-01T00:00:00Z"
  }
]
```

---

## 自评

### 3. 创建自评

**端点**: `POST /api/v1/check/self-assessments`

**请求体**:
```json
{
  "goal_id": "goal-001",
  "items": {
    "indicator-001": {
      "score": 85,
      "comment": "完成目标"
    },
    "indicator-002": {
      "score": 90,
      "comment": "超额完成"
    }
  }
}
```

**成功响应** (201):
```json
{
  "id": "assessment-001",
  "goal_id": "goal-001",
  "user_id": "user-001",
  "items": {
    "indicator-001": {"score": 85, "comment": "完成目标"}
  },
  "status": "draft",
  "submitted_at": null,
  "created_at": "2026-03-18T10:00:00Z",
  "updated_at": "2026-03-18T10:00:00Z"
}
```

---

### 4. 获取自评详情

**端点**: `GET /api/v1/check/self-assessments/{assessment_id}`

---

### 5. 更新自评

**端点**: `PUT /api/v1/check/self-assessments/{assessment_id}`

**请求体**:
```json
{
  "items": {
    "indicator-001": {"score": 88, "comment": "更新后的评价"}
  }
}
```

**业务规则**: 只能更新 draft 状态的自评

---

### 6. 提交自评

**端点**: `POST /api/v1/check/self-assessments/{assessment_id}/submit`

**成功响应** (200):
```json
{
  "id": "assessment-001",
  "status": "submitted",
  "submitted_at": "2026-03-18T10:00:00Z"
}
```

---

### 7. 获取目标的自评

**端点**: `GET /api/v1/check/self-assessments/goal/{goal_id}`

---

## 评价任务

### 8. 获取我的待评价任务

**端点**: `GET /api/v1/check/evaluation-tasks/my-pending`

**成功响应** (200):
```json
[
  {
    "id": "task-001",
    "goal_id": "goal-001",
    "indicator_id": "indicator-001",
    "evaluator_user_id": "manager-001",
    "assigned_by": "manager-001",
    "status": "pending",
    "assigned_at": "2026-03-18T10:00:00Z",
    "due_at": "2026-03-25T10:00:00Z",
    "created_at": "2026-03-18T10:00:00Z"
  }
]
```

---

### 9. 生成评价任务

**端点**: `POST /api/v1/check/evaluation-tasks/generate`

**请求体**:
```json
{
  "goal_id": "goal-001"
}
```

**功能**: 为目标的所有指标生成评价任务，分配给员工的直接上级

**成功响应** (200):
```json
[
  {
    "id": "task-001",
    "goal_id": "goal-001",
    "indicator_id": "indicator-001",
    "evaluator_user_id": "manager-001",
    "status": "pending"
  }
]
```

---

### 10. 获取评价任务列表

**端点**: `GET /api/v1/check/evaluation-tasks`

**查询参数**:
- `status`: 状态过滤（pending/completed）

---

## 评价打分

### 11. 提交评价

**端点**: `POST /api/v1/check/evaluations`

**请求体**:
```json
{
  "task_id": "task-001",
  "indicator_id": "indicator-001",
  "score": 88,
  "comment": "表现良好"
}
```

**业务规则**: 员工必须先提交自评

**成功响应** (201):
```json
{
  "id": "eval-001",
  "task_id": "task-001",
  "goal_id": "goal-001",
  "indicator_id": "indicator-001",
  "evaluator_id": "manager-001",
  "score": 88,
  "comment": "表现良好",
  "created_at": "2026-03-18T10:00:00Z"
}
```

---

### 12. 获取目标的所有评价

**端点**: `GET /api/v1/check/evaluations/goal/{goal_id}`

---

## 最终结果

### 13. 生成最终结果

**端点**: `POST /api/v1/check/final-results/generate`

**功能**: 计算加权分数并生成AI结果确认单

**请求体**:
```json
{
  "goal_id": "goal-001"
}
```

**集成**:
- 调用 `utils/calculations.py` 的 `calculate_c_stage()` 计算分数
- 调用 `graphs/c_graph.py` 的 `run_c_stage()` 生成AI报告

**成功响应** (201):
```json
{
  "id": "result-001",
  "goal_id": "goal-001",
  "computed_score_id": "score-001",
  "suggested_grade": "B",
  "final_grade": "B",
  "confirmed_by": "user-001",
  "confirmed_at": "2026-03-18T10:00:00Z",
  "adjustment_reason": null,
  "status": "pending",
  "created_at": "2026-03-18T10:00:00Z"
}
```

---

### 14. 获取目标的最终结果

**端点**: `GET /api/v1/check/final-results/goal/{goal_id}`

---

### 15. 确认结果

**端点**: `PUT /api/v1/check/final-results/{result_id}/confirm`

**成功响应** (200):
```json
{
  "id": "result-001",
  "status": "confirmed",
  "confirmed_at": "2026-03-18T10:00:00Z"
}
```

---

### 16. 调整结果

**端点**: `PUT /api/v1/check/final-results/{result_id}/adjust`

**权限**: HR Admin

**请求体**:
```json
{
  "final_grade": "A",
  "adjustment_reason": "考虑到特殊贡献，上调等级"
}
```

**成功响应** (200):
```json
{
  "id": "result-001",
  "final_grade": "A",
  "adjustment_reason": "考虑到特殊贡献，上调等级",
  "status": "adjusted"
}
```

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| CHECK_001 | 自评不存在 |
| CHECK_002 | 评价任务不存在 |
| CHECK_003 | 必须先提交自评才能进行他评 |
| CHECK_004 | 自评已提交，不可修改 |
| CHECK_005 | 分数汇总不存在 |
| CHECK_006 | 最终结果不存在 |
| CHECK_007 | 指标权重验证失败 |
