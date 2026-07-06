# A阶段 - 复盘发展 API

## 模块概述

A阶段（Action）负责复盘发展，包括复盘报告生成、发展计划制定、目标继承等功能。

## 涉及数据表

- `review_reports` - 复盘报告
- `development_plans` - 发展计划
- `inheritance_suggestions` - 目标继承建议

## 集成 LangGraph

- 复盘报告生成：调用 `graphs/a_graph.py` 的复盘 agent
- 发展计划审查：调用 `graphs/a_graph.py` 的 SMART 审查 agent
- 继承建议生成：调用 `graphs/a_graph.py` 的继承分析 agent

---

## 复盘报告

### 1. 生成复盘报告

**端点**: `POST /api/v1//review-reports/generactionate`

**功能**: 基于周期数据生成 AI 复盘报告

**请求体**:
```json
{
  "user_id": "user-001",
  "period_id": "period-001"
}
```

**成功响应** (201):
```json
{
  "id": "review-001",
  "user_id": "user-001",
  "period_id": "period-001",
  "achievements": [
    "完成系统架构升级",
    "提升团队技术能力"
  ],
  "challenges": [
    "时间管理需要改进"
  ],
  "lessons_learned": [
    "提前规划技术评审"
  ],
  "improvement_areas": [
    "项目管理能力"
  ],
  "created_at": "2026-03-18T10:00:00Z"
}
```

**集成**: 调用 `graphs/a_graph.py` 的复盘 agent

---

### 2. 获取报告详情

**端点**: `GET /api/v1/action/review-reports/{id}`

---

### 3. 提交用户反馈

**端点**: `PUT /api/v1/action/review-reports/{id}/feedback`

**请求体**:
```json
{
  "user_feedback": "报告准确，建议增加具体案例"
}
```

---

### 4. 获取用户在指定周期的复盘报告

**端点**: `GET /api/v1/action/review-reports/user/{user_id}/period/{period_id}`

---

## 发展计划

### 5. 创建发展计划

**端点**: `POST /api/v1/action/development-plans`

**请求体**:
```json
{
  "user_id": "user-001",
  "period_id": "period-001",
  "development_goals": [
    {
      "area": "技术能力",
      "goal": "掌握微服务架构",
      "actions": [
        "学习Spring Cloud",
        "完成实战项目"
      ],
      "timeline": "3个月",
      "success_criteria": "能够独立设计微服务架构"
    }
  ]
}
```

**成功响应** (201):
```json
{
  "id": "plan-001",
  "user_id": "user-001",
  "status": "draft",
  "created_at": "2026-03-18T10:00:00Z"
}
```

---

### 6. 获取计划详情

**端点**: `GET /api/v1/action/development-plans/{id}`

---

### 7. 更新计划

**端点**: `PUT /api/v1/action/development-plans/{id}`

---

### 8. AI 审查计划

**端点**: `POST /api/v1/action/development-plans/{id}/ai-review`

**功能**: 使用 AI 审查计划是否符合 SMART 原则

**成功响应** (200):
```json
{
  "plan_id": "plan-001",
  "smart_analysis": {
    "specific": {
      "score": 8,
      "feedback": "目标明确"
    },
    "measurable": {
      "score": 7,
      "feedback": "建议增加量化指标"
    },
    "achievable": {
      "score": 8,
      "feedback": "目标可实现"
    },
    "relevant": {
      "score": 9,
      "feedback": "与岗位高度相关"
    },
    "time_bound": {
      "score": 8,
      "feedback": "时间规划合理"
    }
  },
  "overall_score": 8.0,
  "suggestions": [
    "建议增加具体的学习时长"
  ]
}
```

**集成**: 调用 `graphs/a_graph.py` 的 SMART 审查 agent

---

### 9. 提交计划

**端点**: `POST /api/v1/action/development-plans/{id}/submit`

**业务规则**: 提交后状态变为 pending_approval

---

### 10. 审批计划

**端点**: `POST /api/v1/action/development-plans/{id}/approve`

**权限**: Manager

**请求体**:
```json
{
  "approved": true,
  "comment": "计划合理，支持执行"
}
```

---

### 11. 获取我的发展计划

**端点**: `GET /api/v1/action/development-plans/my-plans`

---

### 12. 获取团队的发展计划

**端点**: `GET /api/v1/action/development-plans/my-team`

**权限**: Manager

---

## 目标继承

### 13. 生成继承建议

**端点**: `POST /api/v1/action/inheritance-suggestions/generate`

**功能**: 基于上周期数据生成新周期目标继承建议

**请求体**:
```json
{
  "user_id": "user-001",
  "from_period_id": "period-001",
  "to_period_id": "period-002"
}
```

**成功响应** (201):
```json
{
  "id": "suggestion-001",
  "user_id": "user-001",
  "suggestions": [
    {
      "source_goal_id": "goal-001",
      "source_goal_name": "系统架构优化",
      "suggestion_type": "continue",
      "reasoning": "目标未完全达成，建议继续",
      "recommended_adjustments": [
        "增加代码重构指标"
      ]
    }
  ],
  "created_at": "2026-03-18T10:00:00Z"
}
```

**集成**: 调用 `graphs/a_graph.py` 的继承分析 agent

---

### 14. 获取建议详情

**端点**: `GET /api/v1/action/inheritance-suggestions/{id}`

---

### 15. 接受建议

**端点**: `POST /api/v1/action/inheritance-suggestions/{id}/accept`

**功能**: 接受建议并自动创建新周期目标

---

### 16. 拒绝建议

**端点**: `POST /api/v1/action/inheritance-suggestions/{id}/reject`

**请求体**:
```json
{
  "reason": "目标已完成，不需要继承"
}
```

---

### 17. 获取用户在新周期的继承建议

**端点**: `GET /api/v1/action/inheritance-suggestions/user/{user_id}/period/{period_id}`

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| ACTION_001 | 复盘报告生成失败 |
| ACTION_002 | 发展计划不存在 |
| ACTION_003 | 计划已提交，不可修改 |
| ACTION_004 | 继承建议生成失败 |
