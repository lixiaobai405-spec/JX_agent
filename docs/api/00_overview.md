# API 总览

## 基础信息

**Base URL**: `http://localhost:8000/api/v1`

**协议**: HTTP/HTTPS

**数据格式**: JSON

**字符编码**: UTF-8

## 认证方式

所有需要认证的端点使用 JWT Bearer Token：

```
Authorization: Bearer {access_token}
```

获取 token 请参考 [认证模块文档](01_auth.md)。

## 通用请求头

```
Content-Type: application/json
Accept: application/json
Authorization: Bearer {access_token}
```

## 通用响应格式

### 成功响应

**单个资源**：
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "资源名称",
  "created_at": "2026-03-18T10:00:00Z",
  ...
}
```

**列表资源（分页）**：
```json
{
  "total": 150,
  "page": 1,
  "limit": 20,
  "pages": 8,
  "data": [
    {...},
    {...}
  ]
}
```

### 错误响应

```json
{
  "detail": "错误描述信息",
  "error_code": "ERROR_CODE",
  "timestamp": "2026-03-18T10:00:00Z"
}
```

## HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 201 | 创建成功 |
| 204 | 删除成功（无内容） |
| 400 | 请求参数错误 |
| 401 | 未认证或 token 无效 |
| 403 | 无权限访问 |
| 404 | 资源不存在 |
| 409 | 资源冲突 |
| 422 | 数据验证失败 |
| 429 | 请求过于频繁 |
| 500 | 服务器内部错误 |

## 分页规范

列表端点支持分页，使用查询参数：

- `page`: 页码（从 1 开始，默认 1）
- `limit`: 每页数量（默认 20，最大 100）

示例：
```
GET /api/v1/users?page=2&limit=50
```

## 过滤和排序

### 过滤

使用查询参数进行过滤：

```
GET /api/v1/users?role=manager&department_id=xxx
```

### 排序

使用 `sort` 参数，支持多字段排序：

```
GET /api/v1/users?sort=created_at:desc,name:asc
```

## 时间格式

所有时间字段使用 ISO 8601 格式（UTC）：

```
2026-03-18T10:00:00Z
```

## ID 格式

所有资源 ID 使用 UUID v4 格式：

```
550e8400-e29b-41d4-a716-446655440000
```

## 限流策略

| 端点类型 | 限制 |
|----------|------|
| 登录 | 5 次/分钟 |
| 密码重置 | 3 次/小时 |
| 一般 API | 100 次/分钟 |
| AI 服务 | 10 次/分钟 |

超出限制返回 429 状态码，响应头包含：
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1710756000
```

## 安全响应头

所有响应包含以下安全头：

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
```

## CORS 配置

允许的域名：
- 生产环境：`https://yourdomain.com`
- 开发环境：`http://localhost:3000`, `http://localhost:8501`

允许的方法：`GET, POST, PUT, DELETE, PATCH`

允许凭证：`true`

## API 模块列表

| 模块 | 路径前缀 | 文档 |
|------|----------|------|
| 认证 | `/auth` | [01_auth.md](01_auth.md) |
| 用户管理 | `/users` | [02_users.md](02_users.md) |
| 组织架构 | `/organizations` | [03_organizations.md](03_organizations.md) |
| 考核周期 | `/periods` | [04_periods.md](04_periods.md) |
| P阶段 - 智能定标 | `/plan` | [05_plan_phase.md](05_plan_phase.md) |
| D阶段 - 执行追踪 | `/do` | [06_do_phase.md](06_do_phase.md) |
| C阶段 - 考核评估 | `/check` | [07_check_phase.md](07_check_phase.md) |
| A阶段 - 复盘发展 | `/action` | [08_action_phase.md](08_action_phase.md) |
| AI 服务 | `/ai` | [09_ai_services.md](09_ai_services.md) |
| 通用工具 | `/common` | [10_common.md](10_common.md) |

## 版本控制

当前 API 版本：`v1`

版本包含在 URL 路径中：`/api/v1/...`

## 开发工具

### OpenAPI 文档

访问 `http://localhost:8000/docs` 查看交互式 API 文档（Swagger UI）。

访问 `http://localhost:8000/redoc` 查看 ReDoc 文档。

### 健康检查

```
GET /health
```

响应：
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-03-18T10:00:00Z"
}
```
