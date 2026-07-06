# D阶段 - 执行追踪 API

## 模块概述

D阶段（Do）负责执行追踪，包括数据填报、诊断报告生成、辅导请求等功能。

## 涉及数据表

- `goals` - 绩效目标
- `indicators` - 绩效指标
- `checkin_tasks` - 填报任务
- `data_checkins` - 数据填报记录
- `diagnostic_reports` - 诊断报告
- `coaching_requests` - 辅导请求

## 集成 LangGraph

- 诊断报告生成：调用 `graphs/d_graph.py` 的诊断 agent

---

## 目标和指标

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

## 填报任务

### 1. 获取填报任务列表

**端点**: `GET /api/v1/do/checkin-tasks`

**查询参数**:
- `user_id`: 用户过滤
- `status`: 状态过滤（pending/completed）
- `period_id`: 周期过滤

**成功响应** (200):
```json
{
  "total": 10,
  "data": [
    {
      "id": "task-001",
      "goal_id": "goal-001",
      "goal_name": "系统架构优化",
      "user_id": "user-001",
      "due_date": "2026-03-31",
      "status": "pending",
      "created_at": "2026-03-01T00:00:00Z"
    }
  ]
}
```

---

### 2. 获取任务详情

**端点**: `GET /api/v1/do/checkin-tasks/{id}`

---

### 3. 生成填报任务

**端点**: `POST /api/v1/do/checkin-tasks/generate`

**权限**: System（定时任务调用）

**功能**: 根据策略矩阵的频率自动生成填报任务

---

### 4. 获取我的待填报任务

**端点**: `GET /api/v1/do/checkin-tasks/my-pending`

**成功响应** (200):
```json
{
  "tasks": [
    {
      "id": "task-001",
      "goal_name": "系统架构优化",
      "due_date": "2026-03-31",
      "days_remaining": 13
    }
  ],
  "total": 1
}
```

---

## 数据填报

### 5. 提交填报数据

**端点**: `POST /api/v1/do/checkins`

**请求体**:
```json
{
  "task_id": "task-001",
  "indicator_id": "indicator-001",
  "actual_value": 85,
  "progress_description": "已完成架构文档初稿",
  "issues": "需要更多时间进行技术评审"
}
```

**成功响应** (201):
```json
{
  "id": "checkin-001",
  "task_id": "task-001",
  "indicator_id": "indicator-001",
  "actual_value": 85,
  "submitted_at": "2026-03-18T10:00:00Z"
}
```

**业务规则**:
- 只能在周期 open 状态时提交
- 一个任务可以多次填报（更新进度）

---

### 6. 获取填报记录

**端点**: `GET /api/v1/do/checkins/{id}`

---

### 7. 更新填报数据

**端点**: `PUT /api/v1/do/checkins/{id}`

---

### 8. 获取任务的所有填报记录

**端点**: `GET /api/v1/do/checkins/task/{task_id}`

**成功响应** (200):
```json
{
  "task_id": "task-001",
  "checkins": [
    {
      "id": "checkin-001",
      "indicator_name": "架构文档完成度",
      "actual_value": 85,
      "submitted_at": "2026-03-18T10:00:00Z"
    }
  ]
}
```

---

## 诊断报告

### 9. 生成诊断报告

**端点**: `POST /api/v1/do/diagnostic-reports/generate`

**功能**: 基于填报数据生成 AI 诊断报告

**请求体**:
```json
{
  "goal_id": "goal-001",
  "feedback": "重点关注销售策略，考虑市场竞争因素"
}
```

**字段说明**:
- `goal_id`: 目标ID（必填）
- `feedback`: 用户补充说明，用于指导 AI 生成更针对性的建议（可选）

**成功响应** (201):
```json
{
  "id": "report-001",
  "goal_id": "goal-001",
  "overall_status": "yellow",
  "progress_rate": 0.75,
  "insights": [
    "进度略有延迟，建议加快技术评审"
  ],
  "recommendations": [
    "增加评审会议频率",
    "寻求技术专家支持"
  ],
  "created_at": "2026-03-18T10:00:00Z"
}
```

**集成**: 调用 `graphs/d_graph.py` 的诊断 agent

---

### 10. 获取报告详情

**端点**: `GET /api/v1/do/diagnostic-reports/{id}`

---

### 11. 获取目标的诊断报告列表

**端点**: `GET /api/v1/do/diagnostic-reports/goal/{goal_id}`

---

### 12. 获取最新诊断报告

**端点**: `GET /api/v1/do/diagnostic-reports/goal/{goal_id}/latest`

---

## 辅导请求

### 13. 创建辅导请求

**端点**: `POST /api/v1/do/coaching-requests`

**请求体**:
```json
{
  "diagnostic_report_id": "report-001",
  "request_reason": "需要帮助提升销售业绩",
  "urgency_level": "high"
}
```

**成功响应** (201):
```json
{
  "id": "coaching-001",
  "diagnostic_report_id": "report-001",
  "requester_user_id": "user-001",
  "coach_user_id": "manager-001",
  "request_reason": "需要帮助提升销售业绩",
  "urgency_level": "high",
  "status": "pending",
  "created_at": "2026-03-18T10:00:00Z"
}
```

---

### 14. 获取请求详情

**端点**: `GET /api/v1/do/coaching-requests/{id}`

---

### 15. 更新请求状态

**端点**: `PUT /api/v1/do/coaching-requests/{id}/status`

**请求体**:
```json
{
  "status": "in_progress",
  "response": "已安排技术评审会议"
}
```

---

### 16. 获取我的辅导请求

**端点**: `GET /api/v1/do/coaching-requests/my-requests`

---

### 17. 获取团队的辅导请求

**端点**: `GET /api/v1/do/coaching-requests/my-team`

**权限**: Manager

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| DO_001 | 填报任务不存在 |
| DO_002 | 周期未开放，不能填报 |
| DO_003 | 诊断报告生成失败 |
| DO_004 | 辅导请求不存在 |
