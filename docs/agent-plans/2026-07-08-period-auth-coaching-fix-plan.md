# 2026-07-08 考核期、账号互踢、辅导请求模块修复计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` to execute this plan step by step. Do not overwrite or revert existing uncommitted changes.

**Goal:** 修复三个问题：`/admin/periods` 页面空值崩溃、多个账号/多个会话登录时互相强制退出、`D - 执行追踪` 页面始终展示“我的辅导请求”模块并在无数据时显示空态。

**Architecture:** React 19 + TypeScript + Vite 前端通过 `frontend/src/api/*` 调用 FastAPI 后端；后端认证使用 JWT access token（访问令牌）+ refresh token（刷新令牌），SQLite 存储 `RefreshToken` 和 `BlacklistedAccessToken`；PDCA D 阶段页面由 `frontend/src/pages/pdca/do/DoPage.tsx` 渲染。

**Tech Stack:** FastAPI, SQLAlchemy async, SQLite, JWT, React 19, TypeScript, Vite, TanStack Query, PowerShell on Windows.

**当前检查结论：**

- 工作区已有大量未提交改动，执行时不能覆盖或回滚这些改动。开始实现前必须再次运行 `git status --short` 和针对目标文件的 `git diff`。
- 要求 1 的直接风险点在 `frontend/src/pages/admin/AdminPeriodsPage.tsx`：`PeriodTable` 使用 `periods.length`，但 `frontend/src/api/do.ts` 的 `periodsApi.list()` / `listByStatus()` 直接返回 `r.data.items`。如果后端返回 `items: null`，React Query 的 `data = []` 默认值不会生效，组件会崩溃。
- 要求 2 的关键风险点在 `api/v1/auth/service.py`：`logout()` 当前会撤销当前用户所有未撤销的 refresh token。一个会话登出后，同一用户其他标签页/会话会在刷新 token 时失败并跳转登录。若用户观察到“不同账号互踢”，还需要结合浏览器标签页复制 `sessionStorage`、前端 401 处理和实际 Network 请求进一步验证。
- 要求 3 的直接风险点在 `frontend/src/pages/pdca/do/DoPage.tsx`：当前只有 `(coachingRequests?.length ?? 0) > 0` 时才渲染“我的辅导请求”，所以无数据时整个模块消失。

## Task 0: 基线确认

**Files:** no source changes.

- [x] 运行 `git status --short`，记录已有未提交改动。
- [x] 针对即将修改的文件运行 `git diff -- <file>`，确认是否已有用户改动；如有，保留并在其基础上最小修改。
- [x] 确认后端使用项目内 `.venv` / `uv run`，不使用全局 Python。
- [x] 确认前端没有 `npm test` 脚本，现有轻量测试用 `node --experimental-strip-types` 单文件执行。

**Commands:**

```powershell
git status --short

git diff -- "frontend/src/api/do.ts"
git diff -- "frontend/src/pages/admin/AdminPeriodsPage.tsx"
git diff -- "api/v1/auth/service.py"
git diff -- "api/v1/auth/router.py"
git diff -- "api/v1/auth/schemas.py"
git diff -- "frontend/src/api/auth.ts"
git diff -- "frontend/src/pages/pdca/do/DoPage.tsx"
git diff -- "frontend/src/lib/coaching.ts"
```

## Task 1: 修复考核期管理空值崩溃

**Goal:** `/admin/periods` 即使接口返回 `items: null` 或异常空值，也不能因为 `periods.length` 崩溃。

**Files:**

- `frontend/src/api/do.ts`
- `frontend/src/pages/admin/AdminPeriodsPage.tsx`
- `frontend/src/lib/api-normalizers.ts`，新建
- `frontend/tests/api-normalizers.test.ts`，新建

**Steps:**

- [x] 新建 `frontend/src/lib/api-normalizers.ts`，放通用数组兜底函数，例如 `normalizeList<T>(items: T[] | null | undefined): T[]`，只在 `Array.isArray(items)` 时返回原数组，否则返回 `[]`。
- [x] 修改 `frontend/src/api/do.ts` 的 `periodsApi.list()` 和 `periodsApi.listByStatus()`，把 `r.data.items` 统一经过 `normalizeList()` 后返回。
- [x] 修改 `frontend/src/pages/admin/AdminPeriodsPage.tsx` 的 `PeriodTable`，让 `periods` 参数允许 `null | undefined`，组件内部统一转成 `safePeriods`，渲染时只使用 `safePeriods.length` 和 `safePeriods.map()`。
- [x] 新建 `frontend/tests/api-normalizers.test.ts`，覆盖 `undefined`、`null`、非数组、空数组、正常数组。
- [x] 不改后端接口结构；如果后续确认后端确实返回 `items: null`，再单独做后端一致性修复。

**Verification:**

```powershell
Set-Location -LiteralPath "C:\Users\32159\Downloads\JX_agent\frontend"
node --experimental-strip-types .\tests\api-normalizers.test.ts
npm run build
npm run lint
```

**Expected result:**

- `http://localhost:5173/admin/periods` 不再出现 `Cannot read properties of null (reading 'length')`。
- 当前考核期和归档考核期为空时都显示已有空状态文案。

## Task 2: 修复多会话/多账号登录互相退出

**Goal:** 一个标签页或一个会话登出、刷新失败、重新登录时，不应错误影响其他账号或其他有效会话。

**Files:**

- `api/v1/auth/schemas.py`
- `api/v1/auth/router.py`
- `api/v1/auth/service.py`
- `frontend/src/api/auth.ts`
- `frontend/src/api/client.ts`，只在确认 401 误清理当前会话时修改
- `frontend/src/lib/authStorage.ts`，只在确认标签页隔离仍有问题时修改
- `frontend/tests/authStorage.test.ts`，按实际前端改动补充

**Backend Steps:**

- [x] 在 `api/v1/auth/schemas.py` 新增 `LogoutRequest`，包含可选 `refresh_token: str | None = None`。
- [x] 修改 `api/v1/auth/router.py` 的 `/auth/logout`，接收可选请求体 `LogoutRequest`，把当前 access token 的 `jti`、过期时间和请求体里的 `refresh_token` 一起传给 service。
- [x] 修改 `api/v1/auth/service.py` 的 `logout()` 签名为接收 `refresh_token_str: str | None = None`。
- [x] 保留 access token blacklist（访问令牌黑名单）逻辑。
- [x] 把“撤销当前用户所有 refresh token”的逻辑改为：如果传入 `refresh_token_str`，只按 `hash_token(refresh_token_str)` 找到当前用户对应的那一条 `RefreshToken` 并设置 `revoked_at`；不要撤销同一用户的其他会话。
- [x] 如果没有传入 refresh token，只拉黑当前 access token，不批量撤销 refresh token。这样兼容旧调用，不扩大影响。
- [x] 保留 `change_password()` 和 `confirm_password_reset()` 的“撤销所有 refresh token”逻辑，因为密码变更/重置属于安全场景。

**Frontend Steps:**

- [x] 修改 `frontend/src/api/auth.ts`，`logout()` 调用时从 `authStorage.getRefreshToken()` 读取当前标签页的 refresh token，并发送 `{ refresh_token }` 到 `/auth/logout`。
- [x] 检查 `frontend/src/api/client.ts` 的 401 响应逻辑：只有当前标签页 refresh 失败时才 `authStorage.clearTokens()` 并跳转 `/login`；不要引入 `localStorage` 广播式退出。
- [ ] 如果实测“不同账号互踢”仍存在，再检查是否因为浏览器“复制标签页”带来了相同 `sessionStorage` 初始 token。必要时给 `authStorage` 增加 tab instance 标识，仅清理当前 tab namespace 下的 token。

**Verification:**

```powershell
Set-Location -LiteralPath "C:\Users\32159\Downloads\JX_agent"
.\.venv\Scripts\python.exe -m pytest tests
```

```powershell
Set-Location -LiteralPath "C:\Users\32159\Downloads\JX_agent\frontend"
node --experimental-strip-types .\tests\authStorage.test.ts
npm run build
npm run lint
```

**Manual browser check:**

- [x] 启动后端和前端。

```powershell
Set-Location -LiteralPath "C:\Users\32159\Downloads\JX_agent"
$env:USE_MOCK='true'
uv run python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

```powershell
Set-Location -LiteralPath "C:\Users\32159\Downloads\JX_agent\frontend"
npm run dev
```

- [ ] 用不同浏览器窗口或不同浏览器配置文件分别登录两个账号，不要只用“复制标签页”作为唯一验证方式。
- [ ] 在账号 A 已登录时登录账号 B，账号 A 不应被跳转到 `/login`。
- [ ] 账号 A 登出后，账号 B 不应被跳转到 `/login`。
- [ ] 同一账号在两个窗口登录时，其中一个登出后，另一个不应因为 refresh token 被批量撤销而强制退出。
- [ ] 如果仍出现退出，记录失败窗口的 Network 里第一个 401 请求、接口路径、响应体和当前账号名，再继续定位。

## Task 3: “我的辅导请求”模块始终展示

**Goal:** `D - 执行追踪` 右侧 AI 诊断区域下方始终显示“我的辅导请求”模块；无数据时显示“暂无数据”，有数据时显示列表和“查看”按钮。

**Files:**

- `frontend/src/pages/pdca/do/DoPage.tsx`
- `frontend/src/lib/coaching.ts`
- `frontend/tests/coaching.test.ts`

**Steps:**

- [x] 在 `frontend/src/lib/coaching.ts` 新增纯函数，例如 `filterCoachingRequestsByGoal<T extends { goal_id: string | null | undefined }>(requests, goalId)`，对 `null | undefined` 返回 `[]`，只保留当前 `goal.id` 的请求。
- [x] 在 `frontend/tests/coaching.test.ts` 增加测试：无请求返回空数组；`goalId` 为空返回空数组；混合 goal 的请求只返回当前 goal 的请求。
- [x] 修改 `frontend/src/pages/pdca/do/DoPage.tsx`，用该纯函数替代内联 `allCoachingRequests?.filter(...)`。
- [x] 移除外层 `(coachingRequests?.length ?? 0) > 0 &&` 条件，让模块容器始终渲染。
- [x] 当 `coachingRequests.length === 0` 时，在模块内渲染一个轻量空态卡片，文案为 `暂无数据`。
- [x] 有数据时保持现有卡片列表、状态 Badge 和 `CoachingRequestDetailDialog` 查看按钮。
- [x] 保持模块位置在右栏诊断结果卡片下方，也就是截图红框区域。

**Verification:**

```powershell
Set-Location -LiteralPath "C:\Users\32159\Downloads\JX_agent\frontend"
node --experimental-strip-types .\tests\coaching.test.ts
npm run build
npm run lint
```

**Manual browser check:**

- [ ] 使用没有辅导请求的员工账号打开 `http://localhost:5173/pdca/do`，诊断卡片下方显示“我的辅导请求”和 `暂无数据`。
- [ ] 创建一条辅导请求后，模块显示请求列表。
- [ ] 上级接受/回复后，员工侧点击“查看”能看到上级回复内容。

## Task 4: 总体验证与回归

**Files:** no source changes beyond Tasks 1-3.

- [x] 运行全部现有前端轻量测试。
- [x] 运行前端构建和 lint。
- [x] 运行后端现有 pytest。
- [ ] 手动验证三个页面/流程。
- [x] 最后运行 `git status --short`，总结只包含本次任务相关改动，不包含用户原有无关改动。

**Commands:**

```powershell
Set-Location -LiteralPath "C:\Users\32159\Downloads\JX_agent\frontend"
node --experimental-strip-types .\tests\datetime.test.ts
node --experimental-strip-types .\tests\authStorage.test.ts
node --experimental-strip-types .\tests\coaching.test.ts
node --experimental-strip-types .\tests\api-normalizers.test.ts
npm run build
npm run lint
```

```powershell
Set-Location -LiteralPath "C:\Users\32159\Downloads\JX_agent"
.\.venv\Scripts\python.exe -m pytest tests
```

```powershell
git status --short
```

## Rollback Plan

- 前端崩溃修复如有问题，只回退 `frontend/src/api/do.ts`、`frontend/src/pages/admin/AdminPeriodsPage.tsx`、`frontend/src/lib/api-normalizers.ts` 和 `frontend/tests/api-normalizers.test.ts` 中本次新增内容。
- 认证修复如有问题，只回退 `/auth/logout` 请求体、`service.logout()` 精准撤销逻辑和前端 `authApi.logout()` 传 refresh token 的改动；不要改动密码变更/重置的全量 token 失效逻辑。
- 辅导请求模块如有 UI 问题，只回退 `DoPage.tsx` 的常驻模块渲染和 `coaching.ts` 新增筛选 helper。
- 不使用 `git reset --hard`，不覆盖用户已有未提交改动。

## Notes For Executor

- 每次修改文件前，先说明具体改动范围。
- 如果 `npm run lint` 失败，先区分是本次新增问题还是历史问题；历史问题只记录，不做无关重构。
- 如果 `/auth/logout` 加请求体后 FastAPI 参数解析报错，优先使用 `Body(default=None)` 或一个默认空 schema，不改认证整体结构。
- 如果用户坚持“不同账号互踢”而不是“同账号多会话互踢”，优先用 Network 日志确认第一个 401 来源，再决定是否需要增强前端 tab 隔离。
