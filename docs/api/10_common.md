# 通用工具模块 API

## 模块概述

通用工具模块提供跨模块的通用功能，包括仪表板、报表导出、评论、审计日志等。

## 涉及数据表

- `comments` - 评论
- `audit_logs` - 审计日志
- `progress_records` - 进度记录

---

## 仪表板

### 1. 我的概览

**端点**: `GET /api/v1/common/dashboard/my-overview`

**功能**: 获取当前用户的绩效概览

**成功响应** (200):
```json
{
  "user": {
    "id": "user-001",
    "name": "张三"
  },
  "current_period": {
    "id": "period-001",
    "name": "2026年第一季度"
  },
  "goals_summary": {
    "total": 3,
    "in_progress": 2,
    "completed": 1
  },
  "pending_tasks": {
    "checkins": 2,
    "self_assessments": 1,
    "evaluations": 0
  },
  "recent_activities": [
    {
      "type": "checkin",
      "description": "提交了架构文档进度",
      "timestamp": "2026-03-18T09:00:00Z"
    }
  ]
}
```

---

### 2. 团队概览

**端点**: `GET /api/v1/common/dashboard/team-overview`

**权限**: Manager

**成功响应** (200):
```json
{
  "manager": {
    "id": "manager-001",
    "name": "李四"
  },
  "team_size": 5,
  "completion_rates": {
    "contracts": 0.8,
    "self_assessments": 0.6,
    "evaluations": 0.4
  },
  "team_members": [
    {
      "id": "user-001",
      "name": "张三",
      "goals_count": 3,
      "pending_tasks": 2
    }
  ]
}
```

---

### 3. 公司概览

**端点**: `GET /api/v1/common/dashboard/company-overview`

**权限**: HR Admin

**成功响应** (200):
```json
{
  "total_employees": 100,
  "current_period": {
    "id": "period-001",
    "name": "2026年第一季度"
  },
  "completion_rates": {
    "contracts": 0.95,
    "self_assessments": 0.90,
    "evaluations": 0.85
  },
  "department_stats": [
    {
      "department_name": "技术部",
      "employee_count": 25,
      "completion_rate": 0.92
    }
  ]
}
```

---

## 报表导出

### 4. 导出报表

**端点**: `POST /api/v1/common/reports/export`

**请求体**:
```json
{
  "report_type": "performance_summary",
  "period_id": "period-001",
  "format": "excel",
  "filters": {
    "department_id": "dept-001"
  }
}
```

**成功响应** (202):
```json
{
  "report_id": "report-001",
  "status": "processing",
  "estimated_time": 30
}
```

---

### 5. 下载报表

**端点**: `GET /api/v1/common/reports/{id}/download`

**成功响应** (200):
- Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
- 返回文件流

---

## 评论

### 6. 添加评论

**端点**: `POST /api/v1/common/comments`

**请求体**:
```json
{
  "entity_type": "goal",
  "entity_id": "goal-001",
  "content": "进度不错，继续保持"
}
```

**成功响应** (201):
```json
{
  "id": "comment-001",
  "author_id": "user-001",
  "author_name": "张三",
  "content": "进度不错，继续保持",
  "created_at": "2026-03-18T10:00:00Z"
}
```

---

### 7. 获取评论列表

**端点**: `GET /api/v1/common/comments`

**查询参数**:
- `entity_type`: 实体类型
- `entity_id`: 实体 ID

---

### 8. 更新评论

**端点**: `PUT /api/v1/common/comments/{id}`

**权限**: 评论作者

---

### 9. 删除评论

**端点**: `DELETE /api/v1/common/comments/{id}`

**权限**: 评论作者或管理员

---

## 审计日志

### 10. 获取审计日志

**端点**: `GET /api/v1/common/audit-logs`

**权限**: HR Admin/System Admin

**查询参数**:
- `user_id`: 操作人过滤
- `action_type`: 操作类型过滤
- `entity_type`: 实体类型过滤
- `start_date`, `end_date`: 时间范围

**成功响应** (200):
```json
{
  "total": 100,
  "data": [
    {
      "id": "log-001",
      "user_id": "user-001",
      "user_name": "张三",
      "action_type": "update",
      "entity_type": "goal",
      "entity_id": "goal-001",
      "changes": {
        "before": {"status": "draft"},
        "after": {"status": "active"}
      },
      "timestamp": "2026-03-18T10:00:00Z"
    }
  ]
}
```

---

### 11. 获取日志详情

**端点**: `GET /api/v1/common/audit-logs/{id}`

---

## 进度记录

### 12. 获取进度记录

**端点**: `GET /api/v1/common/progress-records`

**查询参数**:
- `indicator_id`: 指标过滤

---

### 13. 获取指标的进度记录

**端点**: `GET /api/v1/common/progress-records/indicator/{indicator_id}`

**成功响应** (200):
```json
{
  "indicator_id": "indicator-001",
  "indicator_name": "架构文档完成度",
  "target_value": 100,
  "records": [
    {
      "date": "2026-03-01",
      "actual_value": 30
    },
    {
      "date": "2026-03-15",
      "actual_value": 70
    }
  ]
}
```

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| COMMON_001 | 报表生成失败 |
| COMMON_002 | 评论不存在 |
| COMMON_003 | 无权修改评论 |
