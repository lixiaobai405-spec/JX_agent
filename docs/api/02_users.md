# 用户管理模块 API

## 模块概述

用户管理模块负责用户信息的增删改查、下属关系查询等功能。

**重要说明**：所有实体ID（user_id, department_id, position_id, manager_id）均为系统自动生成的UUID，创建时无需提供ID，查询时使用返回的UUID。

## 涉及数据表

- `users` - 用户基础信息
- `departments` - 部门信息（关联查询）
- `positions` - 岗位信息（关联查询）

## 权限规则

- **Employee**: 只能查看/修改自己的信息
- **Manager**: 可查看/管理直接和间接下属
- **HR Admin**: 可管理所有用户
- **System Admin**: 完全权限

---

## 端点列表

### 1. 获取用户列表

**端点**: `GET /api/v1/users/`

**功能**: 获取用户列表（支持分页、过滤、排序）

**认证**: 需要 Bearer token

**权限**:
- Employee: 只能查看自己
- Manager: 可查看自己和下属
- HR Admin/System Admin: 可查看所有用户

**查询参数**:
- `page`: 页码（默认 1）
- `limit`: 每页数量（默认 20，最大 100）
- `role`: 角色过滤（employee/manager/hr_admin/system_admin）
- `department_id`: 部门 ID 过滤
- `status`: 状态过滤（active/inactive）
- `search`: 搜索关键词（用户名、姓名、邮箱）
- `sort`: 排序字段（created_at:desc, name:asc）

**成功响应** (200):
```json
{
  "total": 150,
  "page": 1,
  "limit": 20,
  "pages": 8,
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "zhangsan",
      "email": "zhangsan@example.com",
      "full_name": "张三",
      "role": "employee",
      "department_id": "dept-001",
      "department_name": "技术部",
      "position_id": "pos-001",
      "position_name": "高级工程师",
      "manager_id": "manager-001",
      "manager_name": "李四",
      "status": "active",
      "created_at": "2025-01-01T00:00:00Z"
    }
  ]
}
```

**示例**:
```bash
curl -X GET "http://localhost:8000/api/v1/users/?page=1&limit=20&role=employee&department_id=dept-001" \
  -H "Authorization: Bearer {token}"
```

---

### 2. 获取用户详情

**端点**: `GET /api/v1/users/{user_id}`

**功能**: 获取指定用户的详细信息

**认证**: 需要 Bearer token

**权限**: 根据角色限制访问范围

**路径参数**:
- `user_id`: 用户 ID

**成功响应** (200):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "zhangsan",
  "email": "zhangsan@example.com",
  "full_name": "张三",
  "role": "employee",
  "department_id": "dept-001",
  "department_name": "技术部",
  "position_id": "pos-001",
  "position_name": "高级工程师",
  "manager_id": "manager-001",
  "manager_name": "李四",
  "status": "active",
  "hire_date": "2025-01-01",
  "phone": "13800138000",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2026-03-18T10:00:00Z",
  "last_login_at": "2026-03-18T09:00:00Z"
}
```

**错误响应**:
- 403: 无权访问该用户
- 404: 用户不存在

---

### 3. 创建用户

**端点**: `POST /api/v1/users/`

**功能**: 创建新用户

**认证**: 需要 Bearer token

**权限**: 仅 HR Admin 和 System Admin

**请求体**:
```json
{
  "username": "lisi",
  "email": "lisi@example.com",
  "full_name": "李四",
  "password": "Password123",
  "role": "employee",
  "department_id": "dept-001",
  "position_id": "pos-001",
  "manager_id": "manager-001",
  "hire_date": "2026-03-18",
  "phone": "13800138001"
}
```

**成功响应** (201):
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "username": "lisi",
  "email": "lisi@example.com",
  "full_name": "李四",
  "role": "employee",
  "department_id": "dept-001",
  "position_id": "pos-001",
  "manager_id": "manager-001",
  "status": "active",
  "created_at": "2026-03-18T10:00:00Z"
}
```

**错误响应**:
- 400: 用户名或邮箱已存在
- 403: 无权创建用户

**业务规则**:
- 用户名唯一，3-50字符
- 邮箱唯一，符合邮箱格式
- 密码符合安全要求

---

### 4. 更新用户信息

**端点**: `PUT /api/v1/users/{user_id}`

**功能**: 更新用户信息

**认证**: 需要 Bearer token

**权限**:
- Employee: 只能更新自己的部分字段（邮箱、电话）
- Manager: 可更新下属的部分字段
- HR Admin/System Admin: 可更新所有字段

**路径参数**:
- `user_id`: 用户 ID

**请求体**:
```json
{
  "email": "newemail@example.com",
  "full_name": "张三（新）",
  "phone": "13900139000",
  "department_id": "dept-002",
  "position_id": "pos-002",
  "manager_id": "manager-002"
}
```

**成功响应** (200):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "zhangsan",
  "email": "newemail@example.com",
  "full_name": "张三（新）",
  "updated_at": "2026-03-18T10:30:00Z"
}
```

---

### 5. 删除用户

**端点**: `DELETE /api/v1/users/{user_id}`

**功能**: 删除用户（软删除）

**认证**: 需要 Bearer token

**权限**: 仅 System Admin

**路径参数**:
- `user_id`: 用户 ID

**成功响应** (200):
```json
{
  "message": "User deleted successfully"
}
```

**业务规则**:
- 软删除：设置 status = 'inactive'，保留数据
- 撤销该用户的所有会话

---

### 6. 获取下属列表

**端点**: `GET /api/v1/users/{user_id}/subordinates`

**功能**: 获取指定用户的所有下属（递归查询）

**认证**: 需要 Bearer token

**权限**:
- 只能查询自己或有权访问的用户的下属

**路径参数**:
- `user_id`: 用户 ID

**查询参数**:
- `direct_only`: 是否只查询直接下属（默认 false）

**成功响应** (200):
```json
{
  "user_id": "manager-001",
  "user_name": "李四",
  "subordinates": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "zhangsan",
      "full_name": "张三",
      "role": "employee",
      "department_name": "技术部",
      "position_name": "高级工程师",
      "is_direct": true,
      "level": 1
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "username": "wangwu",
      "full_name": "王五",
      "role": "employee",
      "department_name": "技术部",
      "position_name": "工程师",
      "is_direct": false,
      "level": 2
    }
  ],
  "total": 2
}
```

---

### 7. 获取我的团队

**端点**: `GET /api/v1/users/me/team`

**功能**: 获取当前用户的团队信息（自己 + 下属）

**认证**: 需要 Bearer token

**成功响应** (200):
```json
{
  "manager": {
    "id": "manager-001",
    "username": "lisi",
    "full_name": "李四",
    "role": "manager"
  },
  "team_members": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "zhangsan",
      "full_name": "张三",
      "role": "employee",
      "is_direct": true
    }
  ],
  "total_members": 1
}
```

---

## 数据模型

### UserCreate
```json
{
  "username": "string (required, 3-50 chars, unique)",
  "email": "string (required, email format, unique)",
  "full_name": "string (required, 1-100 chars)",
  "password": "string (required, 6+ chars)",
  "role": "enum (employee/manager/hr_admin/system_admin)",
  "department_id": "string (required, UUID)",
  "position_id": "string (required, UUID)",
  "manager_id": "string (optional, UUID)",
  "hire_date": "string (date format: YYYY-MM-DD)",
  "phone": "string (optional)"
}
```

### UserUpdate
```json
{
  "email": "string (optional)",
  "full_name": "string (optional)",
  "phone": "string (optional)",
  "department_id": "string (optional)",
  "position_id": "string (optional)",
  "manager_id": "string (optional)"
}
```

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| USER_001 | 用户不存在 |
| USER_002 | 用户名已存在 |
| USER_003 | 邮箱已存在 |
| USER_004 | 无权访问该用户 |
| USER_005 | 无权修改该用户 |
| USER_006 | 无权删除该用户 |
| USER_007 | 密码不符合要求 |
