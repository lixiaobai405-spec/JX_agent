# 组织架构模块 API

## 模块概述

组织架构模块负责部门和岗位的管理，支持部门层级结构查询。

**重要说明**：所有实体ID（department_id, position_id, parent_id, manager_id）均为系统自动生成的UUID，创建时无需提供ID，查询时使用返回的UUID。

## 涉及数据表

- `departments` - 部门信息（支持层级结构）
- `positions` - 岗位信息

## 权限规则

- **Employee/Manager**: 只读权限
- **HR Admin/System Admin**: 完全权限

---

## 部门管理

### 1. 获取部门列表

**端点**: `GET /api/v1/organizations/departments`

**查询参数**:
- `page`, `limit`: 分页参数
- `parent_id`: 父部门 ID（查询子部门）
- `search`: 搜索关键词

**成功响应** (200):
```json
{
  "total": 50,
  "page": 1,
  "limit": 20,
  "data": [
    {
      "id": "dept-001",
      "name": "技术部",
      "code": "TECH",
      "parent_id": null,
      "level": 1,
      "manager_id": "manager-001",
      "manager_name": "李四",
      "member_count": 25,
      "created_at": "2025-01-01T00:00:00Z"
    }
  ]
}
```

---

### 2. 获取部门详情

**端点**: `GET /api/v1/organizations/departments/{id}`

**成功响应** (200):
```json
{
  "id": "dept-001",
  "name": "技术部",
  "code": "TECH",
  "parent_id": null,
  "level": 1,
  "manager_id": "manager-001",
  "manager_name": "李四",
  "description": "负责技术研发",
  "member_count": 25,
  "created_at": "2025-01-01T00:00:00Z"
}
```

---

### 3. 创建部门

**端点**: `POST /api/v1/organizations/departments`

**权限**: HR Admin/System Admin

**请求体**:
```json
{
  "name": "产品部",
  "code": "PROD",
  "parent_id": null,
  "manager_id": "manager-002",
  "description": "负责产品设计"
}
```

**成功响应** (201):
```json
{
  "id": "dept-002",
  "name": "产品部",
  "code": "PROD",
  "level": 1,
  "created_at": "2026-03-18T10:00:00Z"
}
```

---

### 4. 更新部门

**端点**: `PUT /api/v1/organizations/departments/{id}`

**权限**: HR Admin/System Admin

**请求体**:
```json
{
  "name": "产品部（新）",
  "manager_id": "manager-003",
  "description": "更新后的描述"
}
```

---

### 5. 删除部门

**端点**: `DELETE /api/v1/organizations/departments/{id}`

**权限**: System Admin

**业务规则**:
- 不能删除有子部门的部门
- 不能删除有成员的部门

---

### 6. 获取部门树

**端点**: `GET /api/v1/organizations/departments/{id}/tree`

**功能**: 获取部门及其所有子部门（树形结构）

**成功响应** (200):
```json
{
  "id": "dept-001",
  "name": "技术部",
  "level": 1,
  "children": [
    {
      "id": "dept-001-1",
      "name": "前端组",
      "level": 2,
      "children": []
    },
    {
      "id": "dept-001-2",
      "name": "后端组",
      "level": 2,
      "children": []
    }
  ]
}
```

---

### 7. 获取部门成员

**端点**: `GET /api/v1/organizations/departments/{id}/members`

**查询参数**:
- `include_subdepts`: 是否包含子部门成员（默认 false）

**成功响应** (200):
```json
{
  "department_id": "dept-001",
  "department_name": "技术部",
  "members": [
    {
      "id": "user-001",
      "username": "zhangsan",
      "full_name": "张三",
      "position_name": "高级工程师"
    }
  ],
  "total": 25
}
```

---

## 岗位管理

### 8. 获取岗位列表

**端点**: `GET /api/v1/organizations/positions`

**查询参数**:
- `page`, `limit`: 分页参数
- `department_id`: 部门过滤
- `search`: 搜索关键词

**成功响应** (200):
```json
{
  "total": 30,
  "page": 1,
  "limit": 20,
  "data": [
    {
      "id": "pos-001",
      "name": "高级工程师",
      "code": "SE_SENIOR",
      "level": "P7",
      "department_id": "dept-001",
      "department_name": "技术部",
      "member_count": 5,
      "created_at": "2025-01-01T00:00:00Z"
    }
  ]
}
```

---

### 9. 获取岗位详情

**端点**: `GET /api/v1/organizations/positions/{id}`

**成功响应** (200):
```json
{
  "id": "pos-001",
  "name": "高级工程师",
  "code": "SE_SENIOR",
  "level": "P7",
  "department_id": "dept-001",
  "description": "负责核心功能开发",
  "responsibilities": ["需求分析", "代码开发", "技术评审"],
  "member_count": 5,
  "created_at": "2025-01-01T00:00:00Z"
}
```

---

### 10. 创建岗位

**端点**: `POST /api/v1/organizations/positions`

**权限**: HR Admin/System Admin

**请求体**:
```json
{
  "name": "产品经理",
  "code": "PM",
  "level": "P6",
  "department_id": "dept-002",
  "description": "负责产品规划",
  "responsibilities": ["需求分析", "产品设计"]
}
```

---

### 11. 更新岗位

**端点**: `PUT /api/v1/organizations/positions/{id}`

**权限**: HR Admin/System Admin

---

### 12. 删除岗位

**端点**: `DELETE /api/v1/organizations/positions/{id}`

**权限**: System Admin

**业务规则**:
- 不能删除有成员的岗位

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| ORG_001 | 部门不存在 |
| ORG_002 | 部门代码已存在 |
| ORG_003 | 不能删除有子部门的部门 |
| ORG_004 | 不能删除有成员的部门 |
| ORG_005 | 岗位不存在 |
| ORG_006 | 岗位代码已存在 |
| ORG_007 | 不能删除有成员的岗位 |
