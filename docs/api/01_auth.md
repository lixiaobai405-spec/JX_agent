# 认证模块 API

## 模块概述

认证模块负责用户身份验证、会话管理和密码管理。采用 JWT (JSON Web Token) 双 token 策略：
- **Access Token**: 15分钟过期，用于 API 访问
- **Refresh Token**: 7天过期，用于刷新 access token

## 涉及数据表

- `users` - 用户基础信息
- `refresh_tokens` - refresh token 存储和管理

## 认证流程

```
1. 用户登录 → 获取 access_token + refresh_token
2. 使用 access_token 访问 API
3. access_token 过期 → 使用 refresh_token 刷新
4. 登出 → 撤销 tokens
```

---

## 端点列表

### 1. 用户登录

**端点**: `POST /api/v1/auth/login`

**功能**: 验证用户凭证并返回 JWT tokens

**认证**: 无需认证

**权限**: 公开

**请求体**:
```json
{
  "username": "zhangsan",
  "password": "Password123"
}
```

**成功响应** (200):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 900,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "zhangsan",
    "email": "zhangsan@example.com",
    "role": "employee",
    "department_id": "dept-001"
  }
}
```

**错误响应**:
- 401: 用户名或密码错误
- 403: 账户已禁用
- 429: 登录尝试过于频繁

**业务规则**:
- 密码使用 bcrypt 验证
- 登录失败5次后锁定账户15分钟
- 限流：5次/分钟

**示例**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "zhangsan",
    "password": "Password123"
  }'
```

---

### 2. 刷新访问令牌

**端点**: `POST /api/v1/auth/refresh`

**功能**: 使用 refresh token 获取新的 access token

**认证**: 无需 Bearer token（使用 refresh token）

**请求体**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**成功响应** (200):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 900
}
```

**错误响应**:
- 401: refresh token 无效或已过期
- 401: refresh token 已被撤销

**业务规则**:
- 旧的 refresh token 自动撤销（token 轮换）
- 新的 refresh token 有效期重新计算（7天）

**示例**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

---

### 3. 用户登出

**端点**: `POST /api/v1/auth/logout`

**功能**: 撤销当前会话的 tokens

**认证**: 需要 Bearer token

**请求体**: 无

**成功响应** (200):
```json
{
  "message": "Successfully logged out"
}
```

**错误响应**:
- 401: token 无效

**业务规则**:
- access token 的 JTI 加入 Redis 黑名单（TTL = 剩余有效期）
- 撤销对应的 refresh token

**示例**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### 4. 获取当前用户信息

**端点**: `GET /api/v1/auth/me`

**功能**: 获取当前登录用户的详细信息

**认证**: 需要 Bearer token

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
  "created_at": "2025-01-01T00:00:00Z",
  "last_login_at": "2026-03-18T10:00:00Z"
}
```

**示例**:
```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### 5. 修改密码

**端点**: `POST /api/v1/auth/password/change`

**功能**: 修改当前用户密码

**认证**: 需要 Bearer token

**请求体**:
```json
{
  "old_password": "OldPassword123",
  "new_password": "NewPassword456"
}
```

**成功响应** (200):
```json
{
  "message": "Password changed successfully"
}
```

**错误响应**:
- 400: 旧密码错误
- 400: 新密码不符合要求

**业务规则**:
- 新密码要求：最少6字符，内容不限
- 修改密码后撤销所有现有会话（除当前会话）

**示例**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/password/change \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "old_password": "OldPassword123",
    "new_password": "NewPassword456"
  }'
```

---

### 6. 请求密码重置

**端点**: `POST /api/v1/auth/password/reset-request`

**功能**: 请求密码重置（发送重置链接到邮箱）

**认证**: 无需认证

**请求体**:
```json
{
  "email": "zhangsan@example.com"
}
```

**成功响应** (200):
```json
{
  "message": "Password reset email sent"
}
```

**业务规则**:
- 生成32字节随机 token，1小时过期
- 存储 token 的哈希值到数据库
- 限流：3次/小时

**示例**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/password/reset-request \
  -H "Content-Type: application/json" \
  -d '{
    "email": "zhangsan@example.com"
  }'
```

---

### 7. 确认密码重置

**端点**: `POST /api/v1/auth/password/reset-confirm`

**功能**: 使用重置 token 设置新密码

**认证**: 无需认证

**请求体**:
```json
{
  "token": "a1b2c3d4e5f6...",
  "new_password": "NewPassword789"
}
```

**成功响应** (200):
```json
{
  "message": "Password reset successfully"
}
```

**错误响应**:
- 400: token 无效或已过期
- 400: 新密码不符合要求

**业务规则**:
- 验证 token 有效性
- 重置密码后撤销所有会话

**示例**:
```bash
curl -X POST http://localhost:8000/api/v1/auth/password/reset-confirm \
  -H "Content-Type: application/json" \
  -d '{
    "token": "a1b2c3d4e5f6...",
    "new_password": "NewPassword789"
  }'
```

---

### 8. 查看活跃会话

**端点**: `GET /api/v1/auth/sessions`

**功能**: 查看当前用户的所有活跃会话

**认证**: 需要 Bearer token

**成功响应** (200):
```json
{
  "sessions": [
    {
      "id": "session-001",
      "device_info": {
        "browser": "Chrome",
        "os": "Windows 10",
        "device_type": "desktop"
      },
      "ip_address": "192.168.1.100",
      "created_at": "2026-03-18T09:00:00Z",
      "expires_at": "2026-03-25T09:00:00Z",
      "is_current": true
    },
    {
      "id": "session-002",
      "device_info": {
        "browser": "Safari",
        "os": "iOS 17",
        "device_type": "mobile"
      },
      "ip_address": "192.168.1.101",
      "created_at": "2026-03-17T10:00:00Z",
      "expires_at": "2026-03-24T10:00:00Z",
      "is_current": false
    }
  ]
}
```

**示例**:
```bash
curl -X GET http://localhost:8000/api/v1/auth/sessions \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

### 9. 撤销指定会话

**端点**: `DELETE /api/v1/auth/sessions/{session_id}`

**功能**: 撤销指定的会话

**认证**: 需要 Bearer token

**路径参数**:
- `session_id`: 会话 ID

**成功响应** (200):
```json
{
  "message": "Session revoked successfully"
}
```

**错误响应**:
- 404: 会话不存在
- 403: 无权撤销该会话（不属于当前用户）

**示例**:
```bash
curl -X DELETE http://localhost:8000/api/v1/auth/sessions/session-002 \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

---

## 数据模型

### LoginRequest
```json
{
  "username": "string (required, 3-50 chars)",
  "password": "string (required, 8-100 chars)"
}
```

### TokenResponse
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "Bearer",
  "expires_in": "integer (seconds)"
}
```

### JWT Payload (Access Token)
```json
{
  "sub": "user_id",
  "username": "zhangsan",
  "role": "employee",
  "department_id": "dept-001",
  "exp": 1710756900,
  "iat": 1710756000,
  "jti": "token-unique-id"
}
```

---

## 安全机制

### 密码安全
- 哈希算法：bcrypt (cost factor = 12)
- 密码要求：最少6字符，内容不限
- 密码历史：不允许使用最近3次使用过的密码

### Token 安全
- Access token 短期有效（15分钟）
- Refresh token 长期有效（7天）
- Token 轮换：刷新时撤销旧 token
- Token 黑名单：登出时加入 Redis

### 会话管理
- 最多5个并发会话
- 超出时自动撤销最旧会话
- 记录设备信息和 IP 地址

### 限流策略
- 登录：5次/分钟
- 密码重置：3次/小时
- 登录失败：5次后锁定15分钟

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| AUTH_001 | 用户名或密码错误 |
| AUTH_002 | 账户已禁用 |
| AUTH_003 | Token 无效或已过期 |
| AUTH_004 | Token 已被撤销 |
| AUTH_005 | 登录尝试过于频繁 |
| AUTH_006 | 密码不符合要求 |
| AUTH_007 | 旧密码错误 |
| AUTH_008 | 重置 token 无效或已过期 |
| AUTH_009 | 会话不存在 |
| AUTH_010 | 无权访问该会话 |
