# 管理后台稳定化修复计划

**目标**：让当前绩效智能体项目具备可演示的基础管理闭环：管理员能创建组织、岗位、账号、考核期，前端不再出现明显 404 和表单/接口错配。

**范围**：本轮只修复前端管理入口、组织/考核期页面、账号创建校验、修改密码字段、前端 lint 中的确定性问题，并补充必要 API 封装。不改真实密钥，不重构后端架构，不删除 Docker 文件。

**当前证据**：
- `/admin/org` 和 `/admin/periods` 在侧边栏存在，但 `router.tsx` 没有对应路由。
- 用户创建密码规则已改为“至少6位，内容无限制”。
- `authApi.changePassword()` 发送 `current_password`，后端要求 `old_password`。
- `.env` 中 `OPENAI_API_KEY` 是占位值且 `USE_MOCK=false`，AI 演示接口会失败。
- 当前 SQLite 只有 `admin` 账号，部门、岗位、考核期均为空。
- `npm run lint` 当前失败，`npx tsc --noEmit -p tsconfig.app.json` 当前通过。

## 任务清单

- [x] **任务 1：生成修复计划文档**
  - 文件：`docs/agent-plans/management-stabilization-plan.md`
  - 验证：文档已创建，后续任务按实际进展打勾。

- [x] **任务 2：添加失败检查，锁定当前问题**
  - 检查侧边栏管理员链接是否都有路由。
  - 检查创建用户密码文案是否与后端强度规则一致。
  - 检查修改密码请求字段是否使用 `old_password`。
  - 检查 `npm run lint` 当前失败项，作为工程质量修复目标。

- [x] **任务 3：补齐管理员路由页面**
  - 新增 `/admin/org` 页面，支持部门和岗位列表、创建、删除。
  - 新增 `/admin/periods` 页面，支持考核期列表、创建、状态推进。
  - 新增前端 `organizationsApi`，对接后端 `/api/v1/organizations/*`。
  - 更新 `router.tsx` 挂载两个管理员页面。

- [x] **任务 4：修复表单和接口错配**
  - 创建用户前后端密码规则改为至少 6 位，内容不限制。
  - 创建用户时将空字符串 `manager_id` 转成 `undefined`，避免无效外键。
  - 修改密码接口字段从 `current_password` 改为 `old_password`。
  - 前端全局错误读取后端 `message` 字段，避免只显示英文或 Axios 默认错误。

- [x] **任务 5：修复 lint 中的确定性问题**
  - `AILoadingSkeleton` 不在 render 中调用 `Math.random()`。
  - UI variant 导出文件处理 Fast Refresh lint 规则。
  - 尽量移除本轮触达文件里的显式 `any`。

- [x] **任务 6：验证**
  - 运行：`npm run lint`
  - 运行：`npx tsc --noEmit -p tsconfig.app.json`
  - 运行：`npm run build`
  - 后端健康检查：`http://localhost:8000/health`
  - 前端页面检查：`http://localhost:5173/admin/org`、`/admin/periods` 不再 404。

## 预期交付

- 管理员侧边栏两个入口可打开。
- 管理员可在前端创建部门、岗位、员工账号、考核期。
- 创建用户密码提示与后端一致。
- 修改密码请求字段与后端一致。
- lint/typecheck/build 至少给出明确验证结果。

## 剩余风险

- 如果不把 `.env` 改为 `USE_MOCK=true` 或填入真实 API Key，AI 生成链路仍会失败。
- 当前没有正式测试框架，部分验证依赖 lint、typecheck、build 和页面手动/浏览器检查。
- 组织管理本轮优先满足演示所需的创建和列表，不扩展复杂组织树拖拽、批量导入等高级能力。
## 最近验证结果

- `npm run lint`：通过。
- `npx tsc --noEmit -p tsconfig.app.json`：通过。
- `npm run build`：通过；Vite 仅提示单个 JS chunk 超过 500 kB。
- `http://127.0.0.1:8000/health`：返回 `{"status":"ok"}`。
- `http://127.0.0.1:5173/admin/org`：HTTP 200。
- `http://127.0.0.1:5173/admin/periods`：HTTP 200。
- `.env`：`USE_MOCK=true`，`OPENAI_API_KEY` 仍为占位值，演示时不会调用真实 LLM。
