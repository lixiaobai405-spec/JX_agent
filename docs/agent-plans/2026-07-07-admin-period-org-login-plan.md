# Admin Period, Organization, User, And Multi-Login Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Do not use sub-agents unless the receiving conversation explicitly allows them.

**Goal:** 完成五个已确认需求：考核期关闭/重新开放/归档/恢复、部门后续编辑、管理员用户管理补齐、考核期名称 placeholder 优化、浏览器标签页级登录态隔离。

**Architecture:** 后端继续沿用 FastAPI + SQLAlchemy service/router/schema 分层；前端继续沿用 React + Vite + TanStack Query + 现有 shadcn 风格组件。优先复用现有 `periodsApi`、`organizationsApi`、`usersApi` 和已有页面，不引入新依赖，不做无关重构。

**Tech Stack:** FastAPI, SQLAlchemy async, SQLite, React, TypeScript, Vite, TanStack Query, axios, lucide-react, PowerShell, uv.

---

## Execution Rules

- [x] 先运行 `git status --short`，确认已有未提交改动。
- [x] 不覆盖、不回滚已有未提交改动，尤其是当前已存在的 PDCA 相关修改。
- [x] 每次修改文件前，先向用户说明本次改动范围。
- [x] 每完成一个任务，在本文档对应 checkbox 打勾。
- [x] 后端运行和测试优先使用项目 `.venv` / `uv` 推荐命令，不使用全局 Python。
- [x] 不读取或输出 `.env`、token、密码、cookie、私钥等敏感值。
- [x] 不执行删除数据库、清空数据、危险回滚、强制 push 等高风险操作。

当前只读核对时的 `git status --short` 摘要如下，执行时不要误回滚这些已有改动：

```text
 M DEPLOYMENT.md
 M README.md
 M api/v1/check/service.py
 M api/v1/do/service.py
 M api/v1/plan/service.py
 M frontend/src/api/action.ts
 M frontend/src/api/do.ts
 M frontend/src/pages/pdca/action/ActionPage.tsx
 M frontend/src/pages/pdca/check/CheckPage.tsx
 M frontend/src/pages/pdca/do/DoPage.tsx
 M frontend/src/pages/pdca/plan/PlanPage.tsx
 M frontend/src/pages/profile/ProfilePage.tsx
 M utils/calculations.py
 M utils/mock_llm.py
?? docs/agent-plans/2026-07-06-pdca-demo-execution-plan.md
?? docs/agent-plans/2026-07-06-pdca-demo-execution-report.md
?? frontend/src/lib/coaching.ts
?? frontend/src/lib/datetime.ts
?? frontend/tests/
?? scripts/
```

---

## Confirmed Requirements

### Requirement 1: 考核期关闭、重新开放、归档与恢复

- 只有 `manager` / `system_admin` 可以关闭、重新开放、归档、恢复。
- `已关闭` 周期显示两个操作：`重新开放`、`归档`。
- `重新开放` 把状态从 `closed` 改为 `open`。
- 如果该员工已有其他 `open` 周期，禁止重新开放。
- `归档` 把状态从 `closed` 改为 `archived`。
- 归档后的周期从主列表隐藏，只在归档管理区显示。
- 考核期管理页做成 Tab：`当前周期` / `归档管理`。
- 归档管理区可查看归档记录和恢复。
- `恢复` 把状态从 `archived` 改回 `closed`。
- 恢复后重新出现在主列表，并可继续 `重新开放` 或再次 `归档`。

状态流转：

```text
draft -> open -> closed -> archived
                 ^          |
                 |          |
              reopen      restore
```

### Requirement 2: 部门支持后续编辑父级部门和负责人

- 部门列表每行新增 `编辑` 按钮。
- 编辑弹窗支持修改：
  - 部门名称
  - 父级部门
  - 负责人
  - 说明
- 父级部门可以选择已有部门或 `无`。
- 选择 `无` 表示变为顶级部门。
- 禁止选择自己作为父级部门。
- 禁止选择自己的下级部门作为父级部门，防止循环组织结构。
- 负责人从已有用户中选择；如果负责人不存在，先在用户管理中创建。

### Requirement 3: 管理员端用户管理能力

- 用户管理入口在管理员账号中。
- 当前 `frontend/src/pages/management/ManagementPage.tsx` 已有 `system_admin` 创建用户入口，但字段不足。
- 需要补齐创建用户字段：
  - 用户名
  - 姓名
  - 邮箱
  - 初始密码
  - 角色
  - 所属部门
  - 岗位
  - 直属上级
  - 手机号（可选）
- 普通员工不能访问用户管理。
- `system_admin` 拥有完整用户创建能力。
- `hr_admin` 当前后端也允许创建用户，如不改权限，前端可保持只给 `system_admin` 展示创建入口。

### Requirement 4: 考核期名称输入提示

- 新建考核期名称输入框 placeholder 从 `如：2026-Q3` 改为 `如：2026年7月绩效周期`。
- 只改未输入前的提示文案。
- 不新增说明文字。
- 不改变后端字段或数据结构。

### Requirement 5: 标签页级登录态隔离

- 同一个浏览器中，不同标签页/窗口可以登录不同账号。
- 每个标签页维护自己的登录态。
- 多个账号刷新 token 时互不覆盖。
- 一个标签页退出，不影响其他标签页。
- 不要求账号切换 UI。
- 不要求复杂多会话管理页。
- 使用 `sessionStorage` 替代全局共享的 `localStorage` 保存 token。
- 集中封装登录态存储，避免散落调用。

---

## File Map

### Backend

- `api/v1/periods/service.py`
  - 修改考核期状态流转。
  - 限制状态操作权限为 `manager` / `system_admin`。
  - 默认列表隐藏 archived；显式 `status=archived` 时返回归档周期。
  - 保留 reopen 时的单 open 周期冲突检查。

- `api/v1/periods/router.py`
  - 优先复用现有 `PUT /periods/{period_id}/status`。
  - 不新增接口，除非执行时发现前端可读性明显需要独立接口。

- `api/v1/periods/schemas.py`
  - 大概率无需修改，因为已有 `PeriodStatusUpdate`。

- `api/v1/organizations/schemas.py`
  - 给 `DepartmentUpdate` 增加 `parent_id: str | None = None`。

- `api/v1/organizations/router.py`
  - `update_department` 使用 `body.model_dump(exclude_unset=True)`，保留显式传入的 `null`，用于把父级部门改成 `无`。

- `api/v1/organizations/service.py`
  - `update_department` 支持修改 `parent_id`。
  - 增加父级合法性校验和层级/路径重算。

- `core/exceptions.py`
  - 可新增组织层级错误，例如 `DepartmentParentInvalidError`，返回 400。

- `api/v1/users/router.py`
  - 已有 `POST /users/`，当前 `hr_admin` / `system_admin` 可创建用户。
  - 本需求优先前端补齐字段，后端不必新增接口。

- `api/v1/users/schemas.py`
  - 已支持 `department_id`、`position_id`、`manager_id`、`phone`。
  - 大概率无需修改。

### Frontend

- `frontend/src/pages/admin/AdminPeriodsPage.tsx`
  - 增加 `Tabs`。
  - 当前周期列表隐藏归档。
  - 归档管理列表只显示归档。
  - `closed` 状态显示 `重新开放` + `归档` 两个按钮。
  - `archived` 状态在归档管理中显示 `恢复`。
  - 名称 placeholder 改为 `如：2026年7月绩效周期`。

- `frontend/src/api/do.ts`
  - 可继续复用 `periodsApi.listByStatus(status)` 和 `periodsApi.updateStatus(id, status)`。
  - 如需要归档列表语义更清晰，可新增 `listArchived`，内部仍调用 `status=archived`。

- `frontend/src/pages/admin/AdminOrgPage.tsx`
  - 部门列表增加编辑按钮。
  - 新增编辑部门弹窗。
  - 调用新增的 `organizationsApi.updateDepartment`。
  - 保持已有新增/删除逻辑。

- `frontend/src/api/organizations.ts`
  - 新增 `updateDepartment(id, data)`。

- `frontend/src/pages/management/ManagementPage.tsx`
  - 补齐 `CreateUserDialog` 字段：部门、岗位、手机号。
  - 创建成功后刷新 `users` 查询。

- `frontend/src/lib/authStorage.ts`
  - 新建登录态存储模块。
  - 使用 `sessionStorage` 存取 `access_token` / `refresh_token`。

- `frontend/src/api/client.ts`
  - 替换直接 `localStorage` 调用为 `authStorage`。
  - refresh token 成功后只更新当前标签页的 `sessionStorage`。

- `frontend/src/pages/auth/LoginPage.tsx`
  - 登录成功后调用 `authStorage.setTokens(...)`。

- `frontend/src/hooks/index.ts`
  - logout 成功后调用 `authStorage.clearTokens()`。

- `frontend/src/router.tsx`
  - `RequireAuth` 使用 `authStorage.getAccessToken()`。

- `frontend/src/types/index.ts`
  - 如新增前端表单类型需要复用，可在页面内定义；不必强行改全局类型。

---

## Task 0: Baseline Check

**Files:**
- Read only: project root

- [x] **Step 0.1: Check worktree**

Run in PowerShell:

```powershell
git status --short
```

Expected:

```text
Shows existing modified/untracked files. Do not reset or checkout them.
```

- [x] **Step 0.2: Confirm frontend scripts**

Run:

```powershell
Get-Content -LiteralPath 'frontend/package.json'
```

Expected:

```text
Scripts include "build": "tsc -b && vite build" and "lint": "eslint .".
```

- [x] **Step 0.3: Confirm backend import command**

Run:

```powershell
uv run python -c "import main; print('IMPORT_OK')"
```

Expected:

```text
IMPORT_OK
```

If this fails because dependencies are missing, diagnose before changing code. Do not install dependencies without user confirmation if network or environment mutation is required.

---

## Task 1: Implement Period Close/Reopen/Archive/Restore

**Files:**
- Modify: `api/v1/periods/service.py`
- Modify: `frontend/src/pages/admin/AdminPeriodsPage.tsx`
- Optional modify: `frontend/src/api/do.ts`

- [x] **Step 1.1: Update backend status flow**

In `api/v1/periods/service.py`, change `STATUS_FLOW` to:

```python
STATUS_FLOW = {
    PeriodStatus.draft: [PeriodStatus.open],
    PeriodStatus.open: [PeriodStatus.closed],
    PeriodStatus.closed: [PeriodStatus.open, PeriodStatus.archived],
    PeriodStatus.archived: [PeriodStatus.closed],
}
```

Reason:

- `closed -> open` supports reopen.
- `closed -> archived` supports archive.
- `archived -> closed` supports restore.

- [x] **Step 1.2: Restrict period status operations to manager/system_admin**

In `update_period_status`, change permission logic so status changes allow only:

```python
if current_user.role not in (UserRole.manager, UserRole.system_admin):
    raise PermissionDeniedError("Only managers and system admins can change period status")
```

Keep `create_period` permissions unchanged unless user explicitly asks to change create permissions too.

- [x] **Step 1.3: Preserve manager scope**

In `update_period_status`, keep manager scope limited to manageable users. Current implementation only checks subordinate IDs. If product expects managers to operate their own period too, use:

```python
if current_user.role == UserRole.manager:
    subordinate_ids = await _get_subordinate_ids(db, current_user.id)
    allowed_ids = subordinate_ids + [current_user.id]
    if period.user_id not in allowed_ids:
        raise PermissionDeniedError("Managers can only change periods for themselves or their subordinates")
```

If execution owner is uncertain, prefer this broader manager/self behavior because `create_period` already allows manager self + subordinates.

- [x] **Step 1.4: Hide archived periods from default backend list**

In `list_periods`, after base query and status handling:

```python
if status:
    query = query.where(Period.status == status)
else:
    query = query.where(Period.status != PeriodStatus.archived)
```

This makes:

- `GET /periods/` return current non-archived periods.
- `GET /periods/?status=archived` return archived records for archive management.

- [x] **Step 1.5: Keep reopen conflict validation**

Do not remove this logic:

```python
if new_status == PeriodStatus.open:
    existing = await db.execute(
        select(Period).where(
            and_(
                Period.user_id == period.user_id,
                Period.status == PeriodStatus.open,
                Period.id != period_id,
                Period.deleted_at.is_(None),
            )
        )
    )
    if existing.scalars().first():
        raise PeriodDateConflictError("Another period is already open for this user")
```

This enforces “同一员工同一时间只能有一个开放考核期”.

- [x] **Step 1.6: Add frontend tabs in AdminPeriodsPage**

In `frontend/src/pages/admin/AdminPeriodsPage.tsx`, import tabs:

```tsx
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
```

Use two queries:

```tsx
const { data: periods = [] } = useQuery({
  queryKey: ['periods', 'current'],
  queryFn: periodsApi.list,
})

const { data: archivedPeriods = [] } = useQuery({
  queryKey: ['periods', 'archived'],
  queryFn: () => periodsApi.listByStatus('archived'),
})
```

On mutation success, invalidate both:

```tsx
qc.invalidateQueries({ queryKey: ['periods'] })
```

- [x] **Step 1.7: Replace single nextStatus action with explicit actions**

Replace the current `nextStatus` usage with a renderer equivalent to this behavior:

```tsx
function getStatusActions(period: Period) {
  if (period.status === 'draft') return [{ status: 'open' as PeriodStatus, label: '开放' }]
  if (period.status === 'open') return [{ status: 'closed' as PeriodStatus, label: '关闭' }]
  if (period.status === 'closed') {
    return [
      { status: 'open' as PeriodStatus, label: '重新开放' },
      { status: 'archived' as PeriodStatus, label: '归档', confirm: `确认归档「${period.name}」？` },
    ]
  }
  if (period.status === 'archived') {
    return [{ status: 'closed' as PeriodStatus, label: '恢复', confirm: `确认恢复「${period.name}」为已关闭？` }]
  }
  return []
}
```

Render multiple buttons for `closed` rows. For actions with `confirm`, call `window.confirm(...)` before `updateStatus.mutate(...)`.

- [x] **Step 1.8: Make archive tab restore-only**

In archive tab:

- List `archivedPeriods`.
- Show status badge `已归档`.
- Show only `恢复` button.
- Restore calls `periodsApi.updateStatus(id, 'closed')`.
- After success, invalidate `['periods']`.

- [x] **Step 1.9: Verify period flow manually**

Manual checks:

```text
1. Create draft period.
2. Open it.
3. Close it.
4. Confirm row now shows "重新开放" and "归档".
5. Click "重新开放"; status returns to "进行中".
6. Close again.
7. Click "归档"; row disappears from 当前周期.
8. Open 归档管理 tab; row appears there.
9. Click "恢复"; row disappears from 归档管理 and appears in 当前周期 as 已关闭.
10. If another open period already exists for same employee, reopen should fail with conflict toast.
```

---

## Task 2: Implement Department Edit Parent/Manager

**Files:**
- Modify: `core/exceptions.py`
- Modify: `api/v1/organizations/schemas.py`
- Modify: `api/v1/organizations/router.py`
- Modify: `api/v1/organizations/service.py`
- Modify: `frontend/src/api/organizations.ts`
- Modify: `frontend/src/pages/admin/AdminOrgPage.tsx`

- [x] **Step 2.1: Add organization hierarchy error**

In `core/exceptions.py`, add after organization errors:

```python
class DepartmentParentInvalidError(AppException):
    def __init__(self, msg: str = "Invalid department parent"):
        super().__init__(HTTP_400_BAD_REQUEST, "ORG_008", msg)
```

- [x] **Step 2.2: Allow DepartmentUpdate.parent_id**

In `api/v1/organizations/schemas.py`, change:

```python
class DepartmentUpdate(BaseModel):
    name: str | None = None
    parent_id: str | None = None
    manager_id: str | None = None
    description: str | None = None
```

- [x] **Step 2.3: Preserve explicit null parent_id**

In `api/v1/organizations/router.py`, change department update payload from `exclude_none=True` to `exclude_unset=True`:

```python
return await service.update_department(
    db=db,
    dept_id=dept_id,
    data=body.model_dump(exclude_unset=True),
)
```

Reason: `parent_id: null` must be preserved to support selecting `无`.

- [x] **Step 2.4: Add descendant detection helper**

In `api/v1/organizations/service.py`, add helper near department helpers:

```python
async def _get_descendant_department_ids(db: AsyncSession, dept_id: str) -> set[str]:
    descendant_ids: set[str] = set()
    queue = [dept_id]
    while queue:
        parent_id = queue.pop(0)
        result = await db.execute(
            select(Department.id).where(
                and_(Department.parent_id == parent_id, Department.deleted_at.is_(None))
            )
        )
        child_ids = list(result.scalars().all())
        for child_id in child_ids:
            if child_id not in descendant_ids:
                descendant_ids.add(child_id)
                queue.append(child_id)
    return descendant_ids
```

- [x] **Step 2.5: Recalculate department level/path recursively**

Add helper:

```python
async def _recalculate_department_tree(db: AsyncSession, dept: Department) -> None:
    if dept.parent_id:
        parent = await db.get(Department, dept.parent_id)
        dept.level = (parent.level + 1) if parent else 1
        dept.path = (parent.path + parent.id + "/") if parent else "/"
    else:
        dept.level = 1
        dept.path = "/"

    result = await db.execute(
        select(Department).where(
            and_(Department.parent_id == dept.id, Department.deleted_at.is_(None))
        )
    )
    for child in result.scalars().all():
        await _recalculate_department_tree(db, child)
```

- [x] **Step 2.6: Update department parent safely**

In `update_department`, support `parent_id`:

```python
async def update_department(db: AsyncSession, dept_id: str, data: dict) -> dict:
    dept = await db.get(Department, dept_id)
    if not dept or dept.deleted_at:
        raise DepartmentNotFoundError()

    if "parent_id" in data:
        from core.exceptions import DepartmentParentInvalidError

        new_parent_id = data["parent_id"]
        if new_parent_id == dept_id:
            raise DepartmentParentInvalidError("Department cannot use itself as parent")

        if new_parent_id:
            parent = await db.get(Department, new_parent_id)
            if not parent or parent.deleted_at:
                raise DepartmentNotFoundError()
            descendant_ids = await _get_descendant_department_ids(db, dept_id)
            if new_parent_id in descendant_ids:
                raise DepartmentParentInvalidError("Department cannot use its descendant as parent")

        dept.parent_id = new_parent_id
        await _recalculate_department_tree(db, dept)

    for field in ("name", "manager_id", "description"):
        if field in data:
            setattr(dept, field, data[field])

    await db.flush()
    return await _dept_to_dict(db, dept)
```

- [x] **Step 2.7: Add frontend updateDepartment API**

In `frontend/src/api/organizations.ts`, add:

```ts
updateDepartment: (id: string, data: {
  name?: string
  parent_id?: string | null
  manager_id?: string | null
  description?: string | null
}) => client.put<Department>(`/organizations/departments/${id}`, data).then((r) => r.data),
```

- [x] **Step 2.8: Add edit state and mutation in DepartmentPanel**

In `frontend/src/pages/admin/AdminOrgPage.tsx`, import an edit icon:

```tsx
import { Building2, BriefcaseBusiness, Pencil, Plus, Trash2 } from 'lucide-react'
```

Add state:

```tsx
const [editing, setEditing] = useState<Department | null>(null)
const [editForm, setEditForm] = useState({
  name: '',
  parent_id: '',
  manager_id: '',
  description: '',
})
```

When clicking edit:

```tsx
onClick={() => {
  setEditing(dept)
  setEditForm({
    name: dept.name,
    parent_id: dept.parent_id ?? '',
    manager_id: dept.manager_id ?? '',
    description: dept.description ?? '',
  })
}}
```

- [x] **Step 2.9: Prevent invalid parent selection in UI**

In the edit parent select:

```tsx
const parentOptions = departments.filter((dept) => dept.id !== editing?.id)
```

This prevents selecting itself. Backend still enforces descendant-cycle prevention.

- [x] **Step 2.10: Add edit dialog**

Use existing `Dialog` components if available in project:

```tsx
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
```

Render a dialog with:

- 部门名称 input
- 父级部门 select
- 负责人 select
- 说明 input
- 取消 button
- 保存 button

Submit payload:

```tsx
organizationsApi.updateDepartment(editing.id, {
  name: editForm.name.trim(),
  parent_id: editForm.parent_id || null,
  manager_id: editForm.manager_id || null,
  description: editForm.description.trim() || null,
})
```

On success:

```tsx
toast.success('部门已更新')
setEditing(null)
qc.invalidateQueries({ queryKey: ['departments'] })
```

- [x] **Step 2.11: Verify department edit flow**

Manual checks:

```text
1. 创建一个顶级部门 A，父级为 无。
2. 创建一个部门 B，父级选择 A。
3. 编辑 B，把负责人改为已有用户，保存后列表负责人更新。
4. 编辑 B，把父级改为 无，保存后层级变为 1。
5. 编辑 A，尝试把父级改为 B，后端应拒绝，提示不能选择下级部门。
6. 编辑任意部门，不能在下拉框中选择自己。
```

---

## Task 3: Complete Admin User Creation Fields

**Files:**
- Modify: `frontend/src/pages/management/ManagementPage.tsx`
- Existing backend: `api/v1/users/router.py`
- Existing backend: `api/v1/users/schemas.py`
- Existing frontend API: `frontend/src/api/users.ts`

- [x] **Step 3.1: Confirm backend already supports required fields**

Current `api/v1/users/schemas.py` already supports:

```python
department_id: str | None = None
position_id: str | None = None
manager_id: str | None = None
phone: str | None = None
```

Do not add backend fields unless execution reveals mismatch.

- [x] **Step 3.2: Add department and position queries to CreateUserDialog**

In `ManagementPage.tsx`, import:

```tsx
import { organizationsApi } from '@/api/organizations'
```

Inside `CreateUserDialog`, add:

```tsx
const { data: departments = [] } = useQuery({
  queryKey: ['departments'],
  queryFn: organizationsApi.listDepartments,
})

const { data: positions = [] } = useQuery({
  queryKey: ['positions'],
  queryFn: organizationsApi.listPositions,
})
```

`useQuery` is already imported at file top. If not available in final file state, add it from `@tanstack/react-query`.

- [x] **Step 3.3: Extend user form schema**

Change `userSchema` to:

```tsx
const userSchema = z.object({
  username: z.string().min(1, '请填写用户名'),
  full_name: z.string().min(1, '请填写姓名'),
  email: z.string().email('请填写有效邮箱'),
  password: z.string().min(6, '密码至少6位'),
  role: z.string().min(1),
  department_id: z.string().optional(),
  position_id: z.string().optional(),
  manager_id: z.string().optional(),
  phone: z.string().optional(),
})
```

- [x] **Step 3.4: Add default values**

Set defaults:

```tsx
defaultValues: {
  role: 'employee',
  department_id: '',
  position_id: '',
  manager_id: '',
  phone: '',
},
```

- [x] **Step 3.5: Submit optional fields correctly**

Change mutation payload:

```tsx
mutationFn: (data: UserForm) => usersApi.create({
  username: data.username,
  full_name: data.full_name,
  email: data.email,
  password: data.password,
  role: data.role,
  department_id: emptyToUndefined(data.department_id),
  position_id: emptyToUndefined(data.position_id),
  manager_id: emptyToUndefined(data.manager_id),
  phone: emptyToUndefined(data.phone),
}),
```

- [x] **Step 3.6: Add fields to dialog UI**

Add select controls:

```tsx
<div className="flex flex-col gap-1.5">
  <Label>所属部门（可选）</Label>
  <select {...register('department_id')} className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
    <option value="">未指定</option>
    {departments.map((dept) => (
      <option key={dept.id} value={dept.id}>{dept.name}</option>
    ))}
  </select>
</div>

<div className="flex flex-col gap-1.5">
  <Label>岗位（可选）</Label>
  <select {...register('position_id')} className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm">
    <option value="">未指定</option>
    {positions.map((position) => (
      <option key={position.id} value={position.id}>{position.name}</option>
    ))}
  </select>
</div>

<div className="flex flex-col gap-1.5">
  <Label>手机号（可选）</Label>
  <Input {...register('phone')} placeholder="手机号" />
</div>
```

Keep existing role and manager fields.

- [x] **Step 3.7: Verify user creation**

Manual checks:

```text
1. 使用 system_admin 登录。
2. 进入用户管理。
3. 创建一个员工，选择部门、岗位、直属上级。
4. 创建成功后，用户列表出现该用户。
5. 新用户可登录。
6. 新用户出现在部门负责人下拉框中。
7. 普通 employee 不显示创建用户入口。
```

---

## Task 4: Change Period Name Placeholder

**Files:**
- Modify: `frontend/src/pages/admin/AdminPeriodsPage.tsx`
- Modify: `frontend/src/pages/management/ManagementPage.tsx`

- [x] **Step 4.1: Update admin period page placeholder**

In `AdminPeriodsPage.tsx`, change:

```tsx
placeholder="如：2026-Q3"
```

to:

```tsx
placeholder="如：2026年7月绩效周期"
```

- [x] **Step 4.2: Update management create-period dialog placeholder**

In `ManagementPage.tsx`, there is another period creation dialog placeholder currently like:

```tsx
placeholder="如：2026-Q2"
```

Change it to:

```tsx
placeholder="如：2026年7月绩效周期"
```

Reason: 管理员也可能从用户管理/团队总览里创建考核期，两个入口应保持一致。

- [x] **Step 4.3: Verify placeholder only**

Manual checks:

```text
1. 打开考核期管理页，新建考核期名称输入框显示：如：2026年7月绩效周期。
2. 打开用户管理里“为某人创建考核期”弹窗，名称输入框显示同样提示。
3. 输入自定义名称后保存，列表显示用户输入的名称。
```

---

## Task 5: Implement Tab-Level Auth Isolation

**Files:**
- Create: `frontend/src/lib/authStorage.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/pages/auth/LoginPage.tsx`
- Modify: `frontend/src/hooks/index.ts`
- Modify: `frontend/src/router.tsx`

- [x] **Step 5.1: Create authStorage module**

Create `frontend/src/lib/authStorage.ts`:

```ts
const ACCESS_TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'

export const authStorage = {
  getAccessToken: () => sessionStorage.getItem(ACCESS_TOKEN_KEY),
  getRefreshToken: () => sessionStorage.getItem(REFRESH_TOKEN_KEY),
  setTokens: (accessToken: string, refreshToken: string) => {
    sessionStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
    sessionStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
  },
  clearTokens: () => {
    sessionStorage.removeItem(ACCESS_TOKEN_KEY)
    sessionStorage.removeItem(REFRESH_TOKEN_KEY)
  },
}
```

Reason: `sessionStorage` is isolated per top-level browsing context. Different tabs/windows can hold different users without overwriting each other.

- [x] **Step 5.2: Replace localStorage in client.ts**

In `frontend/src/api/client.ts`, import:

```ts
import { authStorage } from '@/lib/authStorage'
```

Change request interceptor:

```ts
const token = authStorage.getAccessToken()
```

Change refresh token read:

```ts
const refresh = authStorage.getRefreshToken()
```

Change refresh token write:

```ts
authStorage.setTokens(data.access_token, data.refresh_token)
```

Change clear:

```ts
authStorage.clearTokens()
```

- [x] **Step 5.3: Replace localStorage in LoginPage**

In `frontend/src/pages/auth/LoginPage.tsx`, import:

```tsx
import { authStorage } from '@/lib/authStorage'
```

Change login success:

```tsx
authStorage.setTokens(data.access_token, data.refresh_token)
```

Remove direct:

```tsx
localStorage.setItem(...)
```

- [x] **Step 5.4: Replace localStorage in useLogout**

In `frontend/src/hooks/index.ts`, import:

```ts
import { authStorage } from '@/lib/authStorage'
```

Change logout success:

```ts
authStorage.clearTokens()
qc.clear()
window.location.href = '/login'
```

- [x] **Step 5.5: Replace localStorage in router**

In `frontend/src/router.tsx`, import:

```tsx
import { authStorage } from '@/lib/authStorage'
```

Change:

```tsx
const token = authStorage.getAccessToken()
```

- [x] **Step 5.6: Search for leftover localStorage token calls**

Run:

```powershell
Select-String -Path 'frontend/src/**/*.ts','frontend/src/**/*.tsx' -Pattern 'localStorage'
```

Expected:

```text
No localStorage usages for access_token or refresh_token remain.
```

If other unrelated `localStorage` usages exist, do not change them unless they store login state.

- [x] **Step 5.7: Verify multi-account tab behavior**

Manual checks:

```text
1. 打开标签页 A，登录 demo_sales。
2. 打开标签页 B，登录 demo_manager。
3. 打开标签页 C，登录 demo_ceo。
4. 刷新 A，仍是 demo_sales。
5. 刷新 B，仍是 demo_manager。
6. 刷新 C，仍是 demo_ceo。
7. A 退出登录，B/C 不受影响。
8. B 触发 refresh token，A/C 不被覆盖。
9. C 访问管理员页面正常，A 仍保持员工权限。
```

---

## Task 6: Final Verification

**Files:**
- No direct edits unless verification reveals a bug.

- [x] **Step 6.1: Backend import check**

Run:

```powershell
uv run python -c "import main; print('IMPORT_OK')"
```

Expected:

```text
IMPORT_OK
```

- [x] **Step 6.2: Frontend build**

Run:

```powershell
Set-Location -LiteralPath 'frontend'
npm run build
```

Expected:

```text
TypeScript and Vite build complete without errors.
```

- [x] **Step 6.3: Frontend lint**

Run:

```powershell
Set-Location -LiteralPath 'frontend'
npm run lint
```

Expected:

```text
No lint errors.
```

- [x] **Step 6.4: Manual acceptance checklist**

Verify:

```text
[ ] 已关闭考核期显示“重新开放”和“归档”。
[ ] 归档后从主列表隐藏。
[ ] 归档管理 tab 能看到归档记录。
[ ] 归档恢复后状态为“已关闭”。
[ ] 有其他 open 周期时禁止重新开放。
[ ] 部门能编辑名称、父级部门、负责人、说明。
[ ] 部门不能选择自己或自己的下级作为父级。
[ ] system_admin 能创建带部门/岗位/上级的新用户。
[ ] 考核期名称 placeholder 为“如：2026年7月绩效周期”。
[ ] 多个浏览器标签页能同时登录不同账号，刷新/退出互不覆盖。
```

---

## Suggested Commit Boundaries

如果执行方需要分批提交，建议按下面顺序：

```text
feat: add period archive restore workflow
feat: add department edit parent manager flow
feat: complete admin user creation form
feat: isolate auth state per browser tab
```

提交前必须运行：

```powershell
git status --short
git diff
```

只提交本计划相关文件，不提交无关缓存、日志、数据库文件、临时文件或密钥。
