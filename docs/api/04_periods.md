# 考核周期模块 API

## 模块概述

考核周期模块负责绩效考核周期的管理，包括周期创建、状态流转、统计数据等。

**重要说明**：每个周期对应一个用户（user_id），管理员/Manager 可以为团队成员创建周期。

## 涉及数据表

- `periods` - 考核周期（每个周期对应一个用户）

详细数据表结构请参考：[数据库文档 - Periods](../database/03_periods.md)

## 权限规则

- **Employee**: 只能查看自己的周期
- **Manager**: 可为自己和下属创建周期，可查看自己和团队成员的周期
- **HR Admin**: 可为任何用户创建和管理周期，可查看所有周期
- **System Admin**: 完全权限

## 周期状态流转

```
draft (草稿) → open (开放) → closed (关闭) → archived (归档)
```

---

## 端点列表

### 1. 获取周期列表

**端点**: `GET /api/v1/periods/`

**权限**: 所有已认证用户

**数据过滤规则**:
- **Employee**: 仅返回自己的周期（user_id = 当前用户）
- **Manager**: 返回自己和团队成员的周期
- **HR Admin/System Admin**: 返回所有周期

**查询参数**:
- `page`: 页码（默认 1）
- `limit`: 每页数量（默认 20，最大 100）
- `status`: 状态过滤（可选）

**成功响应** (200):
```json
{
  "items": [
    {
      "id": "period-001",
      "user_id": "user-001",
      "name": "2026年第一季度",
      "start_date": "2026-01-01T00:00:00Z",
      "end_date": "2026-03-31T23:59:59Z",
      "status": "open",
      "description": null,
      "created_at": "2025-12-01T00:00:00Z",
      "updated_at": "2026-01-01T00:00:00Z"
    }
  ],
  "total": 10,
  "page": 1,
  "page_size": 20
}
```

---

### 2. 获取周期详情

**端点**: `GET /api/v1/periods/{id}`

**成功响应** (200):
```json
{
  "id": "period-001",
  "user_id": "user-001",
  "name": "2026年第一季度",
  "start_date": "2026-01-01T00:00:00Z",
  "end_date": "2026-03-31T23:59:59Z",
  "status": "open",
  "description": "2026年Q1绩效考核",
  "created_at": "2025-12-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z"
}
```

---

### 3. 创建周期

**端点**: `POST /api/v1/periods/`

**权限**: Manager/HR Admin/System Admin

**请求体**:
```json
{
  "user_id": "user123",
  "name": "2026年第二季度",
  "start_date": "2026-04-01",
  "end_date": "2026-06-30",
  "description": "2026年Q2绩效考核"
}
```

**字段说明**:
- `user_id`: 可选，不指定则默认为当前用户
- Manager 只能为自己或下属创建周期
- HR Admin/System Admin 可为任何用户创建周期

**成功响应** (201):
```json
{
  "id": "period-002",
  "user_id": "user123",
  "name": "2026年第二季度",
  "start_date": "2026-04-01T00:00:00Z",
  "end_date": "2026-06-30T23:59:59Z",
  "status": "draft",
  "description": "2026年Q2绩效考核",
  "created_at": "2026-03-18T10:00:00Z",
  "updated_at": "2026-03-18T10:00:00Z"
}
```

---

### 4. 更新周期

**端点**: `PUT /api/v1/periods/{id}`

**权限**: HR Admin/System Admin

---

### 5. 删除周期

**端点**: `DELETE /api/v1/periods/{id}`

**权限**: System Admin

**业务规则**:
- 只能删除 draft 状态的周期

---

### 6. 获取当前周期

**端点**: `GET /api/v1/periods/current`

**功能**: 获取当前日期所在的开放周期

**成功响应** (200):
```json
{
  "id": "period-001",
  "user_id": "user-001",
  "name": "2026年第一季度",
  "start_date": "2026-01-01T00:00:00Z",
  "end_date": "2026-03-31T23:59:59Z",
  "status": "open",
  "description": null,
  "created_at": "2025-12-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z"
}
```

---

### 7. 更新周期状态

**端点**: `PUT /api/v1/periods/{id}/status`

**权限**: HR Admin/System Admin

**请求体**:
```json
{
  "status": "open"
}
```

**业务规则**:
- 状态流转必须按顺序：draft → open → closed → archived
- 不可逆转

---

### 8. 获取周期统计

**端点**: `GET /api/v1/periods/{id}/statistics`

**成功响应** (200):
```json
{
  "period_id": "period-001",
  "total_users": 100,
  "completed_contracts": 95,
  "completed_self_assessments": 90,
  "completed_evaluations": 85,
  "completion_rate": 0.85
}
```

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| PERIOD_001 | 周期不存在 |
| PERIOD_002 | 周期时间冲突 |
| PERIOD_003 | 状态流转无效 |
| PERIOD_004 | 不能删除非草稿状态的周期 |
