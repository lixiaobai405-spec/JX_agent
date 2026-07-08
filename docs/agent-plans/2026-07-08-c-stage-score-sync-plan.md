# C 阶段分数限制与上下级同步修复实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Do not overwrite or revert existing uncommitted changes.

**Goal:** 修复 C 阶段自评/他评分数输入与提交范围问题，并让上下级 C 阶段相关信息在页面停留期间自动同步，减少手动刷新。

**Architecture:** 前端使用 React Query 做页面级短轮询与 mutation 后缓存失效；分数限制在前端输入、提交前校验、后端 schema/service 三层同时生效。后端继续使用 FastAPI + Pydantic + SQLAlchemy，不引入 WebSocket/SSE，保持当前架构低风险演进。

**Tech Stack:** React 19, TypeScript, Vite, TanStack Query, FastAPI, Pydantic, SQLAlchemy async, SQLite, pytest, PowerShell on Windows.

---

## Current Context

- C 阶段页面位于 `frontend/src/pages/pdca/check/CheckPage.tsx`。
- 员工自评分数输入当前使用 `Input type="number"`，`className="w-28"`，占位文案 `分数 (0-100)` 显示不完整。
- 经理他评分数输入当前使用 `Input type="number"`，`className="w-24"`，占位文案 `评分`。
- 当前前端用 `parseFloat(value) || 0` 组装分数，没有严格限制 `0-100`。
- 后端 `api/v1/check/schemas.py` 中：
  - `SelfAssessmentCreate.items` / `SelfAssessmentUpdate.items` 是裸 `dict`。
  - `EvaluationCreate.score` 是 `float`，没有范围限制。
- 后端 `api/v1/check/service.py` 直接保存 self assessment items 和 evaluation score，没有统一校验。
- C 阶段 hooks 位于 `frontend/src/hooks/index.ts`，当前 C 阶段相关 query 没有 `refetchInterval`。
- 项目后端测试已使用 `pytest`，默认测试路径配置在 `pyproject.toml` 的 `[tool.pytest.ini_options] testpaths = ["tests"]`。

## Requirements

- [ ] 要求 1：员工 C 阶段自我评估分数输入框要能完整显示 `分数 (0-100)`。
- [ ] 要求 2：员工自评分数和经理他评分数都必须强制限制在 `0-100`。
- [ ] 要求 3：上级和下级之间 C 阶段相关信息要更及时同步，不能依赖用户手动刷新。

## File Map

**Frontend create:**

- `frontend/src/lib/scores.ts`：分数解析、钳制、校验、展示工具。
- `frontend/tests/scores.test.ts`：分数工具轻量测试。

**Frontend modify:**

- `frontend/src/pages/pdca/check/CheckPage.tsx`：输入框宽度、输入钳制、提交前校验、mutation 后失效相关 query。
- `frontend/src/hooks/index.ts`：C 阶段与辅导请求相关 query 增加低频自动刷新。

**Backend modify:**

- `api/v1/check/schemas.py`：为 self assessment item 和 evaluation score 增加 `0-100` 校验。
- `api/v1/check/service.py`：服务层二次校验 self assessment items 和 evaluation score，防止绕过 schema 或历史调用写入脏数据。

**Backend tests create/modify:**

- `tests/test_check_score_validation.py`：覆盖后端 self assessment 和 evaluation 分数范围限制。

**Plan update:**

- `docs/agent-plans/2026-07-08-c-stage-score-sync-plan.md`：执行时逐项勾选。

---

## Task 0: Baseline And Existing Changes

**Files:** no source changes.

- [x] Run current status.

```powershell
Set-Location -LiteralPath "C:\Users\32159\Downloads\JX_agent"
git status --short
```

Expected: repo may contain existing uncommitted changes; do not revert unrelated files.

- [x] Check target diffs before editing.

```powershell
git diff -- "frontend/src/pages/pdca/check/CheckPage.tsx"
git diff -- "frontend/src/hooks/index.ts"
git diff -- "api/v1/check/schemas.py"
git diff -- "api/v1/check/service.py"
git diff -- "pyproject.toml"
```

Expected: understand existing local changes and make minimal edits on top of them.

- [x] Confirm pytest works.

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Expected: current backend tests pass before new changes.

---

## Task 1: Add Frontend Score Utilities

**Files:**

- Create: `frontend/src/lib/scores.ts`
- Create: `frontend/tests/scores.test.ts`

- [x] Write the failing frontend score utility test.

Create `frontend/tests/scores.test.ts`:

```ts
import assert from 'node:assert/strict'

import {
  clampScore,
  parseScoreInput,
  isScoreInRange,
  hasInvalidScores,
} from '../src/lib/scores.ts'

assert.equal(clampScore(-1), 0)
assert.equal(clampScore(0), 0)
assert.equal(clampScore(55.5), 55.5)
assert.equal(clampScore(100), 100)
assert.equal(clampScore(101), 100)

assert.equal(parseScoreInput(''), '')
assert.equal(parseScoreInput('abc'), '')
assert.equal(parseScoreInput('-8'), '0')
assert.equal(parseScoreInput('66'), '66')
assert.equal(parseScoreInput('6666'), '100')

assert.equal(isScoreInRange(''), false)
assert.equal(isScoreInRange('0'), true)
assert.equal(isScoreInRange('100'), true)
assert.equal(isScoreInRange('-1'), false)
assert.equal(isScoreInRange('101'), false)
assert.equal(isScoreInRange('abc'), false)

assert.equal(hasInvalidScores({ a: { score: '90' }, b: { score: '100' } }), false)
assert.equal(hasInvalidScores({ a: { score: '90' }, b: { score: '101' } }), true)
assert.equal(hasInvalidScores({ a: { score: '' } }), true)

console.log('scores tests passed')
```

- [x] Run the failing test.

```powershell
Set-Location -LiteralPath "C:\Users\32159\Downloads\JX_agent\frontend"
node --experimental-strip-types .\tests\scores.test.ts
```

Expected: fail with module not found or missing exports.

- [x] Implement `frontend/src/lib/scores.ts`.

```ts
export type ScoreDraftMap = Record<string, { score: string; comment?: string }>

export function clampScore(value: number): number {
  if (!Number.isFinite(value)) return 0
  if (value < 0) return 0
  if (value > 100) return 100
  return value
}

export function parseScoreInput(value: string): string {
  if (value.trim() === '') return ''
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return ''
  return String(clampScore(parsed))
}

export function isScoreInRange(value: string): boolean {
  if (value.trim() === '') return false
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed >= 0 && parsed <= 100
}

export function hasInvalidScores(items: ScoreDraftMap): boolean {
  return Object.values(items).some((item) => !isScoreInRange(item.score))
}

export function toScorePayload(items: ScoreDraftMap): Record<string, { score: number; comment: string }> {
  return Object.fromEntries(
    Object.entries(items).map(([id, value]) => [
      id,
      {
        score: clampScore(Number(value.score)),
        comment: value.comment ?? '',
      },
    ]),
  )
}
```

- [x] Run the score utility test again.

```powershell
node --experimental-strip-types .\tests\scores.test.ts
```

Expected: `scores tests passed`.

---

## Task 2: Apply Score Input UX And Submit Guard In C Page

**Files:**

- Modify: `frontend/src/pages/pdca/check/CheckPage.tsx`
- Test: `frontend/tests/scores.test.ts`

- [x] Import score helpers in `CheckPage.tsx`.

Add to imports:

```ts
import { hasInvalidScores, parseScoreInput, toScorePayload } from '@/lib/scores'
```

- [x] Replace employee self-assessment draft payload parsing.

In `saveDraft` mutation, replace:

```ts
const parsed = Object.fromEntries(Object.entries(items).map(([k, v]) => [k, { score: parseFloat(v.score) || 0, comment: v.comment }]))
```

with:

```ts
if (hasInvalidScores(items)) {
  throw new Error('评分必须在 0-100 之间')
}
const parsed = toScorePayload(items)
```

- [x] Add error handling for self-assessment draft mutation.

In `saveDraft` mutation options, add:

```ts
onError: (error) => {
  toast.error(error instanceof Error ? error.message : '保存失败')
},
```

- [x] Replace employee submit creation payload parsing.

In `submitSA` mutation, before creating self assessment, add:

```ts
if (hasInvalidScores(items)) {
  throw new Error('评分必须在 0-100 之间')
}
```

Then replace the inline `Object.fromEntries(...)` payload with:

```ts
toScorePayload(items)
```

- [x] Add error handling for submit self-assessment mutation.

In `submitSA` mutation options, add:

```ts
onError: (error) => {
  toast.error(error instanceof Error ? error.message : '提交失败')
},
```

- [x] Clamp employee score input while typing.

Replace self-assessment score input `onChange`:

```ts
onChange={(e) => setItems((prev) => ({ ...prev, [ind.id]: { ...prev[ind.id], score: e.target.value } }))}
```

with:

```ts
onChange={(e) => setItems((prev) => ({
  ...prev,
  [ind.id]: {
    ...prev[ind.id],
    score: parseScoreInput(e.target.value),
  },
}))}
```

- [x] Widen employee score input.

Replace:

```tsx
className="w-28"
```

with:

```tsx
className="w-36 shrink-0"
```

Expected: `分数 (0-100)` displays fully.

- [x] Guard manager evaluation submission.

In `submitEval` mutation, before calling `checkApi.submitEvaluation`, add:

```ts
if (!ev || !Number.isFinite(Number(ev.score)) || Number(ev.score) < 0 || Number(ev.score) > 100) {
  throw new Error('评分必须在 0-100 之间')
}
```

Then pass:

```ts
score: Number(ev.score)
```

- [x] Add error handling for manager evaluation mutation.

In `submitEval` mutation options, add:

```ts
onError: (error) => {
  toast.error(error instanceof Error ? error.message : '评分提交失败')
},
```

- [x] Clamp manager score input while typing.

Replace manager score input `onChange`:

```ts
onChange={(e) => setEvalScores((prev) => ({ ...prev, [task.indicator_id]: { ...prev[task.indicator_id], score: e.target.value } }))}
```

with:

```ts
onChange={(e) => setEvalScores((prev) => ({
  ...prev,
  [task.indicator_id]: {
    ...prev[task.indicator_id],
    score: parseScoreInput(e.target.value),
  },
}))}
```

- [x] Widen manager score input and placeholder.

Replace:

```tsx
placeholder="评分" className="w-24"
```

with:

```tsx
placeholder="分数 (0-100)" className="w-36 shrink-0"
```

- [x] Run frontend utility tests.

```powershell
node --experimental-strip-types .\tests\scores.test.ts
node --experimental-strip-types .\tests\coaching.test.ts
node --experimental-strip-types .\tests\api-normalizers.test.ts
```

Expected: all pass.

- [x] Run frontend build and lint.

```powershell
npm run build
npm run lint
```

Expected: both pass.

---

## Task 3: Add Backend Score Range Validation

**Files:**

- Modify: `api/v1/check/schemas.py`
- Modify: `api/v1/check/service.py`
- Create: `tests/test_check_score_validation.py`

- [x] Write failing backend validation tests.

Create `tests/test_check_score_validation.py`:

```python
import pytest
from pydantic import ValidationError

from api.v1.check.schemas import EvaluationCreate, SelfAssessmentCreate, SelfAssessmentUpdate
from api.v1.check.service import validate_score_items


def test_self_assessment_create_rejects_score_above_100():
    with pytest.raises(ValidationError):
        SelfAssessmentCreate(
            goal_id="goal-1",
            items={"indicator-1": {"score": 101, "comment": "too high"}},
        )


def test_self_assessment_create_rejects_score_below_0():
    with pytest.raises(ValidationError):
        SelfAssessmentCreate(
            goal_id="goal-1",
            items={"indicator-1": {"score": -1, "comment": "too low"}},
        )


def test_self_assessment_update_allows_valid_scores():
    payload = SelfAssessmentUpdate(items={"indicator-1": {"score": 88, "comment": "ok"}})
    assert payload.items["indicator-1"]["score"] == 88


def test_evaluation_create_rejects_score_above_100():
    with pytest.raises(ValidationError):
        EvaluationCreate(task_id="task-1", indicator_id="indicator-1", score=6666)


def test_evaluation_create_rejects_score_below_0():
    with pytest.raises(ValidationError):
        EvaluationCreate(task_id="task-1", indicator_id="indicator-1", score=-1)


def test_service_validation_rejects_invalid_items_when_called_directly():
    with pytest.raises(ValueError, match="评分必须在 0-100 之间"):
        validate_score_items({"indicator-1": {"score": 626662}})
```

- [x] Run the failing backend validation test.

```powershell
Set-Location -LiteralPath "C:\Users\32159\Downloads\JX_agent"
.\.venv\Scripts\python.exe -m pytest tests\test_check_score_validation.py
```

Expected: fail because schema/service validation is not implemented.

- [x] Add schema validation in `api/v1/check/schemas.py`.

Replace:

```python
from pydantic import BaseModel
```

with:

```python
from pydantic import BaseModel, Field, field_validator
```

Add after the comment `# Self Assessment`:

```python
class SelfAssessmentItem(BaseModel):
    score: float = Field(ge=0, le=100)
    comment: str | None = None
```

Change `SelfAssessmentCreate`:

```python
class SelfAssessmentCreate(BaseModel):
    goal_id: str
    items: dict[str, SelfAssessmentItem]
```

Change `SelfAssessmentUpdate`:

```python
class SelfAssessmentUpdate(BaseModel):
    items: dict[str, SelfAssessmentItem] | None = None
```

Change `EvaluationCreate`:

```python
class EvaluationCreate(BaseModel):
    task_id: str
    indicator_id: str
    score: float = Field(ge=0, le=100)
    comment: str | None = None
```

- [x] Convert Pydantic item models to plain dicts in `api/v1/check/router.py`.

In `create_self_assessment`, replace:

```python
return await service.create_self_assessment(db, current_user, data.goal_id, data.items)
```

with:

```python
items = {key: value.model_dump() for key, value in data.items.items()}
return await service.create_self_assessment(db, current_user, data.goal_id, items)
```

In `update_self_assessment`, replace:

```python
return await service.update_self_assessment(db, assessment_id, data.items)
```

with:

```python
items = {key: value.model_dump() for key, value in data.items.items()} if data.items is not None else None
return await service.update_self_assessment(db, assessment_id, items)
```

- [x] Add service-layer validation in `api/v1/check/service.py`.

Add near the top after imports:

```python
def validate_score_value(score: float) -> float:
    if score < 0 or score > 100:
        raise ValueError("评分必须在 0-100 之间")
    return score


def validate_score_items(items: dict | None) -> dict | None:
    if items is None:
        return None
    for item in items.values():
        score = item.get("score") if isinstance(item, dict) else None
        if score is None:
            raise ValueError("评分不能为空")
        validate_score_value(float(score))
    return items
```

Update `create_self_assessment`:

```python
items=validate_score_items(items),
```

Update `update_self_assessment` before assignment:

```python
assessment.items = validate_score_items(items)
```

Update `submit_evaluation` before creating `Evaluation`:

```python
score = validate_score_value(score)
```

- [x] Run backend validation test again.

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_check_score_validation.py
```

Expected: pass.

- [x] Run full backend pytest.

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Expected: all backend tests pass.

---

## Task 4: Add Page-Level Auto Sync With React Query Polling

**Files:**

- Modify: `frontend/src/hooks/index.ts`
- Modify: `frontend/src/pages/pdca/check/CheckPage.tsx`
- Test: frontend build/lint

- [x] Define shared C phase sync interval in `frontend/src/hooks/index.ts`.

Add near the imports:

```ts
const C_PHASE_SYNC_INTERVAL_MS = 5000
```

- [x] Add refetch interval to C phase data hooks.

Update `useSelfAssessment` query options:

```ts
refetchInterval: C_PHASE_SYNC_INTERVAL_MS,
refetchIntervalInBackground: false,
```

Update `usePendingEvaluationTasks`:

```ts
useQuery({
  queryKey: ['eval-tasks', 'pending'],
  queryFn: checkApi.pendingEvaluationTasks,
  refetchInterval: C_PHASE_SYNC_INTERVAL_MS,
  refetchIntervalInBackground: false,
})
```

Update `useGoalEvaluations` query options:

```ts
refetchInterval: C_PHASE_SYNC_INTERVAL_MS,
refetchIntervalInBackground: false,
```

Update `useFinalResult` query options:

```ts
refetchInterval: C_PHASE_SYNC_INTERVAL_MS,
refetchIntervalInBackground: false,
```

- [x] Add refetch interval to coaching request hooks because manager replies also cross account boundary.

Update `useMyCoachingRequests`:

```ts
useQuery({
  queryKey: ['coaching', 'my'],
  queryFn: doApi.myCoachingRequests,
  refetchInterval: C_PHASE_SYNC_INTERVAL_MS,
  refetchIntervalInBackground: false,
})
```

Update `useTeamCoachingRequests` similarly with `['coaching', 'team']`.

- [x] Invalidate all cross-account C phase queries after self-assessment submit.

In `CheckPage.tsx`, inside `submitSA.onSuccess`, keep existing invalidation and add:

```ts
qc.invalidateQueries({ queryKey: ['eval-tasks'] })
qc.invalidateQueries({ queryKey: ['eval-tasks', 'pending'] })
```

- [x] Invalidate self assessment after manager generates tasks.

In `generateTasks.onSuccess`, add:

```ts
qc.invalidateQueries({ queryKey: ['self-assessment', goal?.id] })
```

- [x] Invalidate final result and evaluations after manager submits evaluation.

In `submitEval.onSuccess`, add:

```ts
qc.invalidateQueries({ queryKey: ['final-result', goal?.id] })
```

- [x] Invalidate evaluations after final result generation and confirmation.

In `generateResult.onSuccess`, add:

```ts
qc.invalidateQueries({ queryKey: ['evaluations', goal?.id] })
```

In `confirmResult.onSuccess`, add:

```ts
qc.invalidateQueries({ queryKey: ['evaluations', goal?.id] })
```

- [x] Run frontend build and lint.

```powershell
Set-Location -LiteralPath "C:\Users\32159\Downloads\JX_agent\frontend"
npm run build
npm run lint
```

Expected: both pass.

---

## Task 5: Verification And Manual QA

**Files:** no source changes.

- [x] Run frontend light tests.

```powershell
Set-Location -LiteralPath "C:\Users\32159\Downloads\JX_agent\frontend"
node --experimental-strip-types .\tests\scores.test.ts
node --experimental-strip-types .\tests\datetime.test.ts
node --experimental-strip-types .\tests\authStorage.test.ts
node --experimental-strip-types .\tests\coaching.test.ts
node --experimental-strip-types .\tests\api-normalizers.test.ts
```

Expected: all pass.

- [x] Run frontend build and lint.

```powershell
npm run build
npm run lint
```

Expected: both pass.

- [x] Run backend tests.

```powershell
Set-Location -LiteralPath "C:\Users\32159\Downloads\JX_agent"
.\.venv\Scripts\python.exe -m pytest
```

Expected: all pass.

- [x] Restart backend if it is already running without reload.

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object LocalAddress,LocalPort,OwningProcess
```

If a uvicorn process is already running without `--reload`, stop only that backend process chain and restart with:

```powershell
Set-Location -LiteralPath "C:\Users\32159\Downloads\JX_agent"
$env:USE_MOCK='true'
uv run python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

- [x] Ensure frontend is running.

```powershell
Set-Location -LiteralPath "C:\Users\32159\Downloads\JX_agent\frontend"
npm run dev
```

- [ ] Manual check for requirement 1.

Open `http://localhost:5173/pdca/check` as employee. Expected: self-assessment score input displays `分数 (0-100)` completely.

- [ ] Manual check for requirement 2, employee self score.

As employee, type `6666` into a self-assessment score field. Expected: the field becomes `100` or submit is blocked with `评分必须在 0-100 之间`; no value above `100` is saved.

- [ ] Manual check for requirement 2, manager evaluation score.

As manager, type `626662` into a manager evaluation score field. Expected: the field becomes `100` or submit is blocked with `评分必须在 0-100 之间`; no value above `100` is saved.

- [ ] Manual check for backend enforcement.

Use browser Network or API client to submit an evaluation score `101`. Expected: FastAPI returns validation error, and database does not store the invalid score.

- [ ] Manual check for requirement 3, employee to manager sync.

Open employee C page and manager C page in separate browser windows. Employee submits self assessment. Expected: manager pending task/self-assessment state updates within about 5 seconds without manual refresh.

- [ ] Manual check for requirement 3, manager to employee sync.

Manager submits evaluation or final result. Expected: employee C page updates evaluation progress/final result within about 5 seconds without manual refresh.

- [ ] Manual check for coaching reply sync.

Manager accepts/replies to a coaching request. Expected: employee D/A related coaching request list or detail reflects the update within about 5 seconds without manual refresh.

- [x] Final git status.

```powershell
git status --short
```

Expected: changed files are limited to this task plus pre-existing unrelated changes. Do not revert unrelated changes.

---

## Rollback Plan

- If score input UX causes issues, revert only `frontend/src/pages/pdca/check/CheckPage.tsx`, `frontend/src/lib/scores.ts`, and `frontend/tests/scores.test.ts` changes from this plan.
- If backend validation blocks valid existing data, revert only `api/v1/check/schemas.py`, `api/v1/check/router.py`, `api/v1/check/service.py`, and `tests/test_check_score_validation.py` changes from this plan.
- If polling causes performance issues, revert only `frontend/src/hooks/index.ts` polling additions and keep score validation.
- Do not use `git reset --hard`.
- Do not delete or revert unrelated uncommitted changes that existed before this plan execution.

## Notes For Executor

- Use TDD: write failing tests before implementation for score utility and backend validation.
- Keep polling interval at `5000ms` initially. Do not introduce WebSocket/SSE in this plan.
- Keep polling disabled in background with `refetchIntervalInBackground: false`.
- Do not mutate historical abnormal scores in this plan. If existing database rows already contain values above `100`, create a separate data cleanup plan.
- If `npm run lint` fails on pre-existing files, identify whether the failure is caused by this plan before changing unrelated code.
- If browser manual sync still feels slow, lower interval to `3000ms` only after confirming backend load is acceptable.
