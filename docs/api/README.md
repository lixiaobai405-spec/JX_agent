# API 文档目录

本目录包含 PDCA 绩效管理系统的完整 API 文档。

## 文档结构

### 核心基础模块
- [00_overview.md](00_overview.md) - API 总览和通用规范
- [01_auth.md](01_auth.md) - 认证模块（登录、登出、token 管理）
- [02_users.md](02_users.md) - 用户管理模块
- [03_organizations.md](03_organizations.md) - 组织架构模块（部门、岗位）
- [04_periods.md](04_periods.md) - 考核周期模块

### PDCA 业务模块
- [05_plan_phase.md](05_plan_phase.md) - P阶段：智能定标
- [06_do_phase.md](06_do_phase.md) - D阶段：执行追踪
- [07_check_phase.md](07_check_phase.md) - C阶段：考核评估
- [08_action_phase.md](08_action_phase.md) - A阶段：复盘发展

### 辅助功能模块
- [09_ai_services.md](09_ai_services.md) - AI 服务模块
- [10_common.md](10_common.md) - 通用工具模块
- [99_error_codes.md](99_error_codes.md) - 错误码参考

## 快速开始

1. **认证**：阅读 [01_auth.md](01_auth.md) 了解如何获取 access token
2. **基础数据**：阅读 [02_users.md](02_users.md)、[03_organizations.md](03_organizations.md)、[04_periods.md](04_periods.md) 了解基础数据管理
3. **业务流程**：按 P→D→C→A 顺序阅读对应文档

## API 基础信息

- **Base URL**: `http://localhost:8000/api/v1`
- **认证方式**: JWT Bearer Token
- **数据格式**: JSON
- **文档地址**: `http://localhost:8000/docs`

## 技术栈

- **框架**: FastAPI
- **数据库**: PostgreSQL 14+ with SQLAlchemy 2.0 (async)
- **认证**: JWT (PyJWT) + bcrypt
- **缓存**: Redis
- **AI**: LangGraph agents

## 开发指南

### 认证流程

```bash
# 1. 登录获取 token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "zhangsan", "password": "Password123"}'

# 2. 使用 token 访问 API
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer {access_token}"
```

### 分页请求

```bash
curl -X GET "http://localhost:8000/api/v1/users/?page=1&limit=20" \
  -H "Authorization: Bearer {token}"
```

## 权限体系

| 角色 | 权限范围 |
|------|----------|
| employee | 只能访问自己的数据 |
| manager | 可访问自己和下属的数据 |
| hr_admin | 可管理所有绩效数据 |
| system_admin | 完全权限 |

## 业务流程

### P阶段 - 智能定标
1. 岗位分析 → 2. 生成绩效合约 → 3. 确认合约

### D阶段 - 执行追踪
1. 数据填报 → 2. 生成诊断报告 → 3. 辅导请求

### C阶段 - 考核评估
1. 员工自评 → 2. 经理评价 → 3. 计算分数 → 4. 确认结果

### A阶段 - 复盘发展
1. 生成复盘报告 → 2. 制定发展计划 → 3. 目标继承

