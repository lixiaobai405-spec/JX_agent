# AI 服务模块 API

## 模块概述

AI 服务模块提供统一的 AI 功能接口，封装各阶段的 LangGraph agents。

## 涉及数据表

- `ai_generation_logs` - AI 生成日志

## 集成 LangGraph

所有端点调用对应的 LangGraph agents：
- P阶段：`graphs/p_graph.py`
- D阶段：`graphs/d_graph.py`
- C阶段：`graphs/c_graph.py`
- A阶段：`graphs/a_graph.py`

---

## 端点列表

### 1. 岗位分析

**端点**: `POST /api/v1/ai/job-analysis`

**功能**: 调用 P graph 进行岗位分析

**请求体**:
```json
{
  "position_id": "pos-001",
  "job_description": "负责系统架构设计"
}
```

**成功响应** (200):
```json
{
  "prototype_code": "P",
  "scores": {
    "strategic": 7,
    "complexity": 8,
    "uncertainty": 6
  },
  "reasoning": "该岗位需要高度专业技能",
  "log_id": "log-001"
}
```

---

### 2. 生成绩效合约

**端点**: `POST /api/v1/ai/generate-contract`

**功能**: 调用 P graph 生成绩效合约

**请求体**:
```json
{
  "user_id": "user-001",
  "period_id": "period-001",
  "job_analysis_id": "analysis-001"
}
```

---

### 3. 生成诊断报告

**端点**: `POST /api/v1/ai/generate-diagnostic`

**功能**: 调用 D graph 生成诊断报告

**请求体**:
```json
{
  "goal_id": "goal-001"
}
```

---

### 4. 计算分数

**端点**: `POST /api/v1/ai/compute-score`

**功能**: 调用 C graph 计算加权分数

**请求体**:
```json
{
  "goal_id": "goal-001"
}
```

---

### 5. 生成复盘报告

**端点**: `POST /api/v1/ai/generate-review`

**功能**: 调用 A graph 生成复盘报告

**请求体**:
```json
{
  "user_id": "user-001",
  "period_id": "period-001"
}
```

---

### 6. 审查发展计划

**端点**: `POST /api/v1/ai/review-plan`

**功能**: 调用 A graph 审查发展计划（SMART）

**请求体**:
```json
{
  "plan_id": "plan-001"
}
```

---

### 7. 获取 AI 生成日志

**端点**: `GET /api/v1/ai/generation-logs`

**权限**: HR Admin/System Admin

**查询参数**:
- `user_id`: 用户过滤
- `agent_type`: agent 类型过滤
- `page`, `limit`: 分页

---

### 8. 获取日志详情

**端点**: `GET /api/v1/ai/generation-logs/{id}`

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| AI_001 | AI 服务调用失败 |
| AI_002 | AI 响应超时 |
| AI_003 | AI 响应格式错误 |
