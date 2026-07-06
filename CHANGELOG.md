# Changelog

## [Unreleased] - 2026-04-07

### Fixed
- 修复前端用户创建表单的 TypeScript 类型错误
  - 将 userSchema 中 role 字段从 `.default('employee')` 改为 `.min(1)`，解决输入/输出类型不匹配
  - 为 handleSubmit 回调添加显式类型注解，确保类型推断正确

## [2026-04-03]

### Added
- 组织架构测试文档 (test/ORGANIZATION_STRUCTURE.md)
- 新增测试脚本：new_period_api.sh, test_review_report_idempotency.sh

### Fixed
- 修复 review report 生成接口的幂等性问题，避免重复生成报告时违反唯一约束
- 修复 token 刷新时的时区比较错误 (naive vs aware datetime)

## [2026-04-02]

### Added
- 前端完整部署文档，包含三种部署方式（Nginx、Docker、静态托管）
- 开发服务器配置说明（host、port、allowedHosts、proxy）
- Node.js 环境要求说明（>= 18.0.0）

### Fixed
- 修复 ManagementPage.tsx 中对象展开顺序导致的 TypeScript 错误
- 修复 ActionPage.tsx 中未使用变量 reviewText 的 TypeScript 警告
- 配置 Vite 开发服务器监听 0.0.0.0，支持外部访问
- 添加域名白名单配置，允许 jx.yiriso.fun 访问

### Changed
- 更新前端 README.md，从模板文档改为项目专用文档
