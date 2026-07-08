# PDCA Demo Flow Implementation Plan

> **For agentic workers:** execute this plan task-by-task in a new Codex conversation. Use `executing-plans` if available. Do not start subagents unless the user explicitly asks for them. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reliable demo and acceptance path for the performance AI agent so the five customer test roles can prove the full PDCA workflow from JD input to next-cycle improvement inheritance.

**Architecture:** Keep the existing FastAPI + SQLAlchemy async + SQLite backend and React + TypeScript + Vite frontend. Add deterministic demo data and verification scripts first, then close gaps in P/D/C/A behavior and frontend flow. Prefer idempotent seed scripts and narrow feature fixes over broad refactors.

**Tech Stack:** FastAPI, SQLAlchemy async, SQLite, LangGraph, OpenAI-compatible LLM client with `USE_MOCK`, React 19, TypeScript, Vite, PowerShell on Windows.

---

## Execution Rules For The Next Conversation

- Default communication language: Chinese.
- Work from `C:\Users\32159\Downloads\JX_agent`.
- Before edits, run `git status --short` and inspect related diffs. Do not overwrite or revert user changes.
- Do not read or print real secrets from `.env`. Use `.env_example` for configuration structure.
- Do not delete `jx-db.db` or reset data unless the user explicitly confirms.
- Use PowerShell-compatible commands. Do not use Bash-style `&&` in PowerShell.
- Backend commands should use the project `.venv` / `uv` pattern already established for this project.
- Keep commits small if the user asks to commit. Suggested commit boundaries are listed at the end of each task group.

## Current Known Worktree Risks

At the time this plan was created, the worktree had uncommitted files from earlier work:

```text
M  frontend/src/pages/profile/ProfilePage.tsx
?? HANDOFF.md
?? frontend/src/lib/datetime.ts
?? frontend/tests/
?? docs/agent-plans/2026-07-06-pdca-demo-execution-plan.md
```

The next conversation must re-check the live status because this may have changed. Do not revert these changes unless the user explicitly asks.

## Source Requirements

The customer documents are:

- `C:\Users\32159\Downloads\JX_agent\docs\绩效智能体功能蓝图_0129.docx`
- `C:\Users\32159\Downloads\JX_agent\docs\绩效智能体测试数据.docx`

The five required acceptance roles are:

| Code | Role Type | Demo Position | Required Proof |
|---|---|---|---|
| S | 铁军型 | 华东KA销售经理 | 3-5 indicators, quantitative weight over 80%, monthly cycle |
| P | 项目型 | 气泡水研发高级工程师 | 5-7 indicators, qualitative ratio around 40%-60%, quarterly cycle |
| O | 运营型 | 饮料灌装线线长 | SOP and production data driven, highly quantitative, monthly cycle |
| F | 职能型 | 华东区招聘专员 | service satisfaction, compliance, response efficiency, monthly cycle |
| M | 管理型 | 供应链总监 | strategic decomposition, team enablement, long cycle, half-year cycle |

The end-to-end demo path must be:

```text
JD input
-> job prototype classification
-> strategy mapping
-> performance contract generation
-> contract confirmation
-> D-phase check-ins
-> diagnostic report
-> C-phase self assessment and manager evaluation
-> final score and grade
-> A-phase review report
-> development plan AI review
-> next-cycle inheritance suggestion
```

## File Map

Likely files to create:

- `scripts/seed_demo_data.py`: idempotent demo data seed for organization, users, periods, JD cases, and optional full S-role PDCA snapshot.
- `scripts/verify_demo_data.py`: deterministic assertions that the demo seed exists and is internally consistent.
- `scripts/verify_pdca_demo_flow.py`: API-level smoke script that exercises the S-role path against a running backend.
- `frontend/src/lib/pdcaDisplay.ts`: optional shared frontend display helpers if PDCA page duplication grows.
- `docs/agent-plans/2026-07-06-pdca-demo-execution-report.md`: execution report generated after implementation.

Likely files to modify:

- `utils/mock_llm.py`: add complete mock classification and indicator output for S/P/O/F/M test cases.
- `graphs/p_graph.py`: ensure prompts and schema reliably support all five prototypes and customer examples.
- `api/v1/plan/service.py`: verify contract validation and confirmation correctly create `Goal` and `Indicator` rows.
- `api/v1/do/service.py`: improve D-phase calculation inputs and report completeness where needed.
- `api/v1/check/service.py`: ensure C-phase can complete from seeded or UI-created data.
- `api/v1/action/service.py`: ensure A-phase review, plan review, and inheritance suggestions produce useful demo content.
- `frontend/src/pages/pdca/plan/PlanPage.tsx`: make P-stage demo actions obvious.
- `frontend/src/pages/pdca/do/DoPage.tsx`: make check-in, diagnosis, and coaching request flow obvious.
- `frontend/src/pages/pdca/check/CheckPage.tsx`: make self-assessment, manager evaluation, and final result flow obvious.
- `frontend/src/pages/pdca/action/ActionPage.tsx`: make review report, development plan, AI review, and inheritance visible.
- `README.md` or `DEPLOYMENT.md`: document demo accounts and demo path after implementation.

---

## Task 0: Baseline Guard And Verification

**Files:**
- Read: `README.md`
- Read: `HANDOFF.md`
- Read: `pyproject.toml`
- Read: `frontend/package.json`
- Read: `api/v1/*/router.py`
- Read: `api/v1/*/service.py`
- Read: `models/*.py`

- [x] **Step 0.1: Check current Git state**

Run:

```powershell
git status --short
```

Expected: identify pending files before any edit. If unrelated user changes exist, leave them untouched and mention them before editing.

- [x] **Step 0.2: Verify backend import baseline**

Run:

```powershell
uv run python -c "import main; print('IMPORT_OK')"
```

Expected:

```text
IMPORT_OK
```

- [x] **Step 0.3: Verify frontend baseline**

Run:

```powershell
cd frontend
npm run build
```

Expected: exit code 0. Existing Vite chunk-size warning is acceptable.

- [x] **Step 0.4: Record baseline gaps**

Create a short note in the implementation response, not a new file yet, covering:

```text
- existing pending changes
- backend import result
- frontend build result
- whether jx-db.db exists
- whether ports 8000 and 5173 are already in use
```

Suggested commit boundary: no commit for Task 0.

---

## Task 1: Add Idempotent Demo Seed Data

**Goal:** The project must have deterministic customer-style data for all five role types, without requiring manual database editing.

**Files:**
- Create: `scripts/seed_demo_data.py`
- Create: `scripts/verify_demo_data.py`
- Read: `models/user.py`
- Read: `models/organization.py`
- Read: `models/period.py`
- Read: `models/check_phase.py`
- Read: `models/plan_phase.py`
- Read: `models/do_phase.py`
- Read: `models/action_phase.py`

- [x] **Step 1.1: Create `scripts/seed_demo_data.py` with an idempotent upsert structure**

Use the project async session from `core.database.AsyncSessionLocal`. The script must:

```text
1. call init_db() before seeding
2. find existing rows by stable unique keys such as username, department code, position code, period name
3. create missing rows
4. update only demo-owned rows identified by demo usernames/codes
5. never delete existing rows
6. print a concise summary of created/updated records
```

Demo user passwords should be non-secret test passwords, for example:

```text
Demo@123456
```

Do not reuse any real user password from `.env` or the local database.

- [x] **Step 1.2: Seed organization structure**

Create or update these departments:

| code | name | parent |
|---|---|---|
| `DEMO_COMPANY` | 乐饮食品有限公司 | none |
| `DEMO_SALES_EAST` | 华东销售部 | `DEMO_COMPANY` |
| `DEMO_RND` | 研发中心 | `DEMO_COMPANY` |
| `DEMO_FACTORY` | 生产运营部 | `DEMO_COMPANY` |
| `DEMO_HR` | 人力资源部 | `DEMO_COMPANY` |
| `DEMO_SUPPLY` | 供应链中心 | `DEMO_COMPANY` |

Create or update these positions:

| code | title | department |
|---|---|---|
| `DEMO_CEO` | CEO | `DEMO_COMPANY` |
| `DEMO_SALES_MANAGER` | 华东销售部负责人 | `DEMO_SALES_EAST` |
| `DEMO_KA_SALES` | 华东KA销售经理 | `DEMO_SALES_EAST` |
| `DEMO_RND_ENGINEER` | 气泡水研发高级工程师 | `DEMO_RND` |
| `DEMO_LINE_LEADER` | 饮料灌装线线长 | `DEMO_FACTORY` |
| `DEMO_RECRUITER` | 华东区招聘专员 | `DEMO_HR` |
| `DEMO_SUPPLY_DIRECTOR` | 供应链总监 | `DEMO_SUPPLY` |

- [x] **Step 1.3: Seed demo users**

Create or update these users:

| username | role | full_name | position | manager |
|---|---|---|---|---|
| `demo_ceo` | `system_admin` | 周总 | CEO | none |
| `demo_manager` | `manager` | 李娜 | 华东销售部负责人 | `demo_ceo` |
| `demo_sales` | `employee` | 王强 | 华东KA销售经理 | `demo_manager` |
| `demo_rd` | `employee` | 陈晨 | 气泡水研发高级工程师 | `demo_ceo` |
| `demo_ops` | `employee` | 赵磊 | 饮料灌装线线长 | `demo_ceo` |
| `demo_recruiter` | `employee` | 孙敏 | 华东区招聘专员 | `demo_manager` |
| `demo_supply` | `manager` | 吴昊 | 供应链总监 | `demo_ceo` |

Use demo emails under `example.com`. Keep `demo_sales` compatible with the existing local user if it already exists.

- [x] **Step 1.4: Seed one active or draft current period per demo user**

Create a period named:

```text
2026年7月绩效演示周期
```

For S/O/F users, set monthly date range:

```text
start_date = 2026-07-01 00:00:00 UTC
end_date = 2026-07-31 23:59:59 UTC
status = draft
```

For P users, create:

```text
2026年Q3绩效演示周期
start_date = 2026-07-01 00:00:00 UTC
end_date = 2026-09-30 23:59:59 UTC
status = draft
```

For M users, create:

```text
2026年下半年绩效演示周期
start_date = 2026-07-01 00:00:00 UTC
end_date = 2026-12-31 23:59:59 UTC
status = draft
```

- [x] **Step 1.5: Store the five JD cases in the script as constants**

Use the exact customer test JD content from `绩效智能体测试数据.docx`:

```text
S: 华东KA销售经理
P: 气泡水研发高级工程师
O: 饮料灌装线线长
F: 华东区招聘专员
M: 供应链总监
```

The seed script should print the username and matching JD label so the operator can copy a JD into the P-stage UI if needed.

- [x] **Step 1.6: Create `scripts/verify_demo_data.py`**

The verification script must assert:

```text
1. all seven demo users exist
2. all six demo departments exist
3. all seven demo positions exist
4. each five acceptance users has a period
5. manager relationships are set
6. no demo user has an empty hashed_password
```

Use built-in `assert` and exit non-zero on failure. Do not add `pytest` unless the user approves a dependency addition.

- [x] **Step 1.7: Run seed and verification**

Run:

```powershell
uv run python scripts/seed_demo_data.py
uv run python scripts/verify_demo_data.py
```

Expected:

```text
DEMO_SEED_OK
DEMO_VERIFY_OK
```

Suggested commit:

```powershell
git add scripts/seed_demo_data.py scripts/verify_demo_data.py
git commit -m "Add deterministic PDCA demo seed data"
```

---

## Task 2: Complete Mock LLM Coverage For S/P/O/F/M

**Goal:** With `USE_MOCK=true`, all five customer JD cases must classify correctly and generate indicators matching the customer document rules.

**Files:**
- Modify: `utils/mock_llm.py`
- Modify if needed: `graphs/p_graph.py`
- Create: `scripts/verify_mock_llm_cases.py`

- [x] **Step 2.1: Add five explicit mock classification responses**

In `utils/mock_llm.py`, provide classification data for:

```text
MOCK_CLASSIFY_S
MOCK_CLASSIFY_P
MOCK_CLASSIFY_O
MOCK_CLASSIFY_F
MOCK_CLASSIFY_M
```

Each response must include:

```text
position_type
position_type_name
classification_reasoning
score_quantifiability
score_output_cycle
score_work_nature
features
confidence
```

Use the document logic:

```text
S: high quantifiability, short cycle, flexible result-oriented sales work
P: low quantifiability, long milestone cycle, creative project work
O: high quantifiability, short cycle, standardized SOP work
F: lower quantifiability, short response cycle, standardized service/support work
M: lower quantifiability, long cycle, strategic and team enablement work
```

- [x] **Step 2.2: Add five explicit mock indicator responses**

In `utils/mock_llm.py`, provide:

```text
MOCK_INDICATORS_S
MOCK_INDICATORS_P
MOCK_INDICATORS_O
MOCK_INDICATORS_F
MOCK_INDICATORS_M
```

The indicator names, target values, weights, coaching cycle, and result application should match `绩效智能体测试数据.docx`.

Non-redline weights must sum to `100`. Redline indicators must use:

```json
{
  "type": "redline",
  "weight": 0,
  "is_redline": true
}
```

- [x] **Step 2.3: Route mock outputs by JD keywords**

Update the mock client routing so these keywords select the right case:

| keyword | expected type |
|---|---|
| `华东区全家` or `便利系统` or `新品铺货` | S |
| `气泡水新口味` or `中试生产` or `产品专利` | P |
| `灌装线` or `生产SOP` or `次品率` | O |
| `招聘` or `候选人` or `入职手续` | F |
| `供应链` or `仓储自动化` or `供应商` | M |

- [x] **Step 2.4: Create `scripts/verify_mock_llm_cases.py`**

The script should import the five JD strings from `scripts/seed_demo_data.py` or duplicate them as constants if importing creates side effects. It must call:

```python
from graphs.p_graph import run_classify_only, run_generate_indicators
```

Use `AsyncSessionLocal` for `run_generate_indicators`. For each case, assert:

```text
classification code matches expected
indicator count matches expected range
non-redline weight sum is 100
redline count is at least 1
assessment period matches expected monthly/quarterly/half-year
```

- [x] **Step 2.5: Run mock verification**

Run:

```powershell
$env:USE_MOCK='true'
uv run python scripts/verify_mock_llm_cases.py
```

Expected:

```text
MOCK_LLM_CASES_OK
```

Suggested commit:

```powershell
git add utils/mock_llm.py graphs/p_graph.py scripts/verify_mock_llm_cases.py
git commit -m "Complete mock LLM coverage for five PDCA role types"
```

---

## Task 3: Make P-Stage Contract Generation Demo-Safe

**Goal:** P-stage should generate and confirm a contract without malformed weights, wrong indicator direction, or duplicate goal confusion.

**Files:**
- Modify: `api/v1/plan/service.py`
- Create: `scripts/verify_p_stage_contract.py`

- [x] **Step 3.1: Verify contract validation uses current indicator schema**

Review `validate_contract_indicators()` in `api/v1/plan/service.py`. It currently needs to align with `graphs/p_graph.py` indicator fields:

```text
type: positive | negative | qualitative | redline
weight: integer percentage
is_redline: boolean
```

Required validation behavior:

```text
1. redline indicators are excluded from regular weight sum
2. regular weights sum to 100 before persistence
3. indicator count includes redline indicators because the customer examples count them
4. quantitative ratio counts positive and negative indicators as quantitative
5. qualitative ratio counts qualitative indicators as qualitative
```

- [x] **Step 3.2: Verify confirm contract maps indicator direction correctly**

In `confirm_contract()`, map:

```text
positive -> IndicatorDirection.positive
negative -> IndicatorDirection.negative
qualitative -> IndicatorDirection.positive
redline -> IndicatorDirection.negative
```

Keep `weight = ind_data["weight"] / 100.0`.

Set `redline = ind_data["is_redline"] or ind_data["type"] == "redline"`.

- [x] **Step 3.3: Preserve display metadata**

If the current `Indicator` model lacks fields for unit, target display, and scoring rule, do not change the schema in this task. Store user-facing details in `definition` by appending concise text:

```text
目标：{target_display}；评分：{scoring_rule}
```

This is a pragmatic demo-safe approach that avoids a database migration.

- [x] **Step 3.4: Create `scripts/verify_p_stage_contract.py`**

The script should:

```text
1. seed demo data
2. use USE_MOCK=true
3. create a job analysis for demo_sales using the S-role JD
4. generate a contract for demo_sales and the July period
5. confirm the contract
6. assert one Goal exists for demo_sales and the period
7. assert indicators are created with correct names and weights
8. assert the July period status becomes open
```

- [x] **Step 3.5: Run verification**

Run:

```powershell
$env:USE_MOCK='true'
uv run python scripts/verify_p_stage_contract.py
```

Expected:

```text
P_STAGE_CONTRACT_OK
```

Suggested commit:

```powershell
git add api/v1/plan/service.py scripts/verify_p_stage_contract.py
git commit -m "Make P-stage contract confirmation demo safe"
```

---

## Task 4: Make D-Stage Diagnosis Useful For Demo

**Goal:** The demo user should be able to submit check-ins and see a clear diagnostic report with progress, traffic light, root cause, suggestions, and coaching action.

**Files:**
- Modify: `api/v1/do/service.py`
- Modify if needed: `graphs/d_graph.py`
- Modify if needed: `utils/calculations.py`
- Create: `scripts/verify_d_stage_demo.py`
- Modify: `frontend/src/pages/pdca/do/DoPage.tsx`

- [x] **Step 4.1: Verify D-stage numeric calculation**

Ensure positive indicators calculate:

```text
achievement = actual / target
```

Ensure negative indicators calculate:

```text
achievement = target / actual
```

when actual is greater than zero. Redline indicators should drive red status when actual value breaches the redline rule.

- [x] **Step 4.2: Persist complete report fields**

When generating `DiagnosticReport`, populate:

```text
weighted_achievement_rate
time_progress
progress_deviation
overall_progress
indicators_analysis
root_cause_analysis
improvement_suggestions
traffic_light_status
generated_by_ai
```

If the graph already returns some fields under different keys, normalize them in `api/v1/do/service.py` rather than changing database schema.

- [x] **Step 4.3: Use S-role check-in scenario**

For `demo_sales`, seed or submit these current values:

| indicator | target | actual | expected |
|---|---:|---:|---|
| 区域净销售额 | 800 | 520 | red/yellow risk |
| 新品铺货率 | 85 | 70 | yellow/risk |
| 销售回款率 | 98 | 96 | near target |
| 巡店SOP执行 | 92 | 90 | near target |
| 乱价/串货行为 | 0 | 0 | no redline breach |

- [x] **Step 4.4: Create `scripts/verify_d_stage_demo.py`**

The script should:

```text
1. ensure the P-stage S-role goal exists
2. submit or update one latest check-in per indicator
3. generate a diagnostic report
4. assert traffic_light_status is yellow or red
5. assert improvement_suggestions is not empty
6. create a coaching request and assert it points to demo_manager
```

- [x] **Step 4.5: Improve D frontend affordances**

In `frontend/src/pages/pdca/do/DoPage.tsx`, make sure the page clearly supports:

```text
1. current indicators visible
2. actual value input per indicator
3. submit check-in button
4. generate diagnosis button
5. diagnostic report visible after generation
6. apply for coaching button when report exists
```

Do not redesign the whole page. Keep the existing component style.

- [x] **Step 4.6: Run verification**

Run:

```powershell
$env:USE_MOCK='true'
uv run python scripts/verify_d_stage_demo.py
cd frontend
npm run build
npm run lint
```

Expected:

```text
D_STAGE_DEMO_OK
frontend build exits 0
frontend lint exits 0
```

Suggested commit:

```powershell
git add api/v1/do/service.py graphs/d_graph.py utils/calculations.py scripts/verify_d_stage_demo.py frontend/src/pages/pdca/do/DoPage.tsx
git commit -m "Improve D-stage demo diagnosis flow"
```

---

## Task 5: Make C-Stage Evaluation And Final Grade Demo-Safe

**Goal:** The demo can move from self-assessment through manager evaluation to final result without manual database editing.

**Files:**
- Modify: `api/v1/check/service.py`
- Create: `scripts/verify_c_stage_demo.py`
- Modify: `frontend/src/pages/pdca/check/CheckPage.tsx`

- [x] **Step 5.1: Verify D-phase completion rule**

`generate_evaluation_tasks()` requires `period.d_phase_completed == True`. Add a demo-safe path in the verification script to mark the demo period complete after D-stage diagnosis exists.

Do not remove the rule. It reflects the customer flow.

- [x] **Step 5.2: Verify self-assessment flow**

The script must create and submit a self-assessment for `demo_sales` with items:

```json
{
  "区域净销售额": {"actual": 520, "self_score": 75, "comment": "核心便利系统铺货推进中，但成交转化偏慢。"},
  "新品铺货率": {"actual": 70, "self_score": 78, "comment": "重点门店已进入谈判，部分门店排期延后。"},
  "销售回款率": {"actual": 96, "self_score": 92, "comment": "大客户回款整体稳定。"},
  "巡店SOP执行": {"actual": 90, "self_score": 90, "comment": "陈列和价签执行基本符合要求。"}
}
```

- [x] **Step 5.3: Verify manager evaluation flow**

Generate evaluation tasks for the S-role goal, then submit manager scores:

```text
区域净销售额: 76
新品铺货率: 80
销售回款率: 92
巡店SOP执行: 88
```

Assert all tasks become `completed`.

- [x] **Step 5.4: Verify final result generation**

Generate final result and assert:

```text
ScoreAggregate exists
FinalResult exists
final_grade is one of S/A/B/C
status is pending before confirmation
status is confirmed after confirmation
```

- [x] **Step 5.5: Improve C frontend affordances**

In `frontend/src/pages/pdca/check/CheckPage.tsx`, make sure the page clearly supports:

```text
1. employee self-assessment create/edit/submit
2. manager pending evaluation tasks
3. evaluation score submission
4. final result generation
5. final result confirmation
```

Keep role-based behavior simple and visible. Employee sees self-assessment; manager/admin sees evaluation tasks.

- [x] **Step 5.6: Run verification**

Run:

```powershell
$env:USE_MOCK='true'
uv run python scripts/verify_c_stage_demo.py
cd frontend
npm run build
npm run lint
```

Expected:

```text
C_STAGE_DEMO_OK
frontend build exits 0
frontend lint exits 0
```

Suggested commit:

```powershell
git add api/v1/check/service.py scripts/verify_c_stage_demo.py frontend/src/pages/pdca/check/CheckPage.tsx
git commit -m "Complete C-stage demo evaluation flow"
```

---

## Task 6: Make A-Stage Review, Development Plan, And Inheritance Demo-Safe

**Goal:** The demo can show the customer that performance results become personal growth actions and next-cycle suggestions.

**Files:**
- Modify: `api/v1/action/service.py`
- Modify if needed: `graphs/a_graph.py`
- Create: `scripts/verify_a_stage_demo.py`
- Modify: `frontend/src/pages/pdca/action/ActionPage.tsx`

- [x] **Step 6.1: Verify review report content**

Generate a review report from the confirmed S-role final result. Assert:

```text
strengths_analysis has at least one item or summary
improvement_areas has at least one item for lower-scored indicators
report_type matches final grade family
```

- [x] **Step 6.2: Verify development plan creation**

Create a development plan for `demo_sales`:

```json
{
  "goals": {
    "text": "提升重点便利系统客户转化率，将华东区核心门店新品铺货率提升到85%以上。"
  },
  "actions": {
    "text": "每周复盘3个失败谈判案例，按客户类型调整报价话术；每周五向李娜提交铺货推进清单。"
  },
  "required_resources": {
    "text": "需要上级协助复盘重点客户谈判策略，并提供优秀KA案例。"
  },
  "timeline": {
    "text": "2026年8月底前完成第一轮重点门店复盘，2026年9月底前形成标准打法。"
  }
}
```

- [x] **Step 6.3: Verify AI plan review**

Run AI review and assert:

```text
ai_reviewed is true
smart_evaluation exists
ai_suggestions.overall_review is not empty
```

- [x] **Step 6.4: Verify manager approval**

Submit and approve the development plan as `demo_manager` or `demo_ceo`. Assert:

```text
status becomes approved
approved_by is set
approved_at is set
```

- [x] **Step 6.5: Verify inheritance suggestion**

Create the next period:

```text
2026年8月绩效演示周期
```

Generate inheritance suggestions from July to August. Assert:

```text
at least one InheritanceSuggestion exists
suggestion_type is new_indicator
status is pending
accept and reject endpoints both work on separate suggestions or in separate script runs
```

- [x] **Step 6.6: Improve A frontend affordances**

In `frontend/src/pages/pdca/action/ActionPage.tsx`, make sure the page clearly supports:

```text
1. generate/view review report
2. create/edit development plan
3. submit to AI review
4. show AI SMART feedback
5. submit/approve plan
6. generate/view next-cycle inheritance suggestion
```

- [x] **Step 6.7: Run verification**

Run:

```powershell
$env:USE_MOCK='true'
uv run python scripts/verify_a_stage_demo.py
cd frontend
npm run build
npm run lint
```

Expected:

```text
A_STAGE_DEMO_OK
frontend build exits 0
frontend lint exits 0
```

Suggested commit:

```powershell
git add api/v1/action/service.py graphs/a_graph.py scripts/verify_a_stage_demo.py frontend/src/pages/pdca/action/ActionPage.tsx
git commit -m "Complete A-stage demo growth loop"
```

---

## Task 7: Add One End-To-End Demo Smoke Script

**Goal:** A future maintainer can prove the S-role demo works with one command after starting the backend.

**Files:**
- Create: `scripts/verify_pdca_demo_flow.py`
- Modify if needed: `README.md`

- [x] **Step 7.1: Start backend in mock mode**

Use one terminal:

```powershell
$env:USE_MOCK='true'
uv run python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Expected:

```text
Uvicorn running on http://0.0.0.0:8000
```

- [x] **Step 7.2: Create API smoke script**

`scripts/verify_pdca_demo_flow.py` should use standard library `urllib.request` or an already installed HTTP client. Do not add a new dependency.

The script should:

```text
1. login as demo_sales with Demo@123456
2. call /api/v1/auth/me
3. confirm profile returns demo_sales
4. fetch current period or use seeded period id
5. fetch current goal
6. fetch indicators
7. fetch latest diagnostic
8. fetch final result if C-stage script has run
9. fetch review report if A-stage script has run
```

This smoke script can depend on Tasks 1-6 having run. It should fail with a clear message if the backend is not running.

- [x] **Step 7.3: Run smoke script**

Run in a second terminal:

```powershell
uv run python scripts/verify_pdca_demo_flow.py
```

Expected:

```text
PDCA_DEMO_FLOW_OK
```

Suggested commit:

```powershell
git add scripts/verify_pdca_demo_flow.py README.md
git commit -m "Add PDCA demo flow smoke verification"
```

---

## Task 8: Frontend Demo Polish Across PDCA Pages

**Goal:** The UI should guide a user through the demo without needing to understand internal API order.

**Files:**
- Modify: `frontend/src/pages/pdca/plan/PlanPage.tsx`
- Modify: `frontend/src/pages/pdca/do/DoPage.tsx`
- Modify: `frontend/src/pages/pdca/check/CheckPage.tsx`
- Modify: `frontend/src/pages/pdca/action/ActionPage.tsx`
- Modify if needed: `frontend/src/hooks/index.ts`
- Modify if needed: `frontend/src/api/*.ts`

- [x] **Step 8.1: Add clear empty states**

Each PDCA page should show a useful command when data is missing:

```text
P page: no analysis -> show JD input and analyze button
P page: analysis exists but no contract -> show generate contract button
P page: contract exists but not confirmed -> show confirm button
D page: no goal -> tell user to complete P stage
D page: no check-in -> show input controls
C page: D not complete -> explain D-stage requirement
A page: no final result -> tell user to complete C stage
```

- [x] **Step 8.2: Add query invalidation after mutations**

After each successful mutation, invalidate relevant React Query keys:

```text
['me']
['periods', 'current']
['goal', periodId]
['indicators', goalId]
['diagnostic', goalId]
['self-assessment', goalId]
['eval-tasks']
['final-result', goalId]
['review-report-user', userId, periodId]
['my-plans']
['inheritance-suggestions', userId, periodId]
```

This prevents stale UI during the live demo.

- [x] **Step 8.3: Keep layout stable**

Do not add marketing-style sections. Keep pages operational:

```text
toolbar
current stage status
main form/table
AI output panel
next action button
```

- [x] **Step 8.4: Run frontend verification**

Run:

```powershell
cd frontend
npm run build
npm run lint
```

Expected:

```text
build exits 0
lint exits 0
```

Suggested commit:

```powershell
git add frontend/src/pages/pdca frontend/src/hooks/index.ts frontend/src/api
git commit -m "Polish PDCA frontend demo flow"
```

---

## Task 9: Demo Documentation And Operator Checklist

**Goal:** Another person can run the demo without reading the code.

**Files:**
- Create: `docs/agent-plans/2026-07-06-pdca-demo-execution-report.md`
- Modify: `README.md`
- Modify if needed: `DEPLOYMENT.md`

- [x] **Step 9.1: Add demo accounts section**

Document these demo accounts:

| username | password | role | use |
|---|---|---|---|
| `demo_sales` | `Demo@123456` | employee | employee PDCA flow |
| `demo_manager` | `Demo@123456` | manager | manager evaluation and coaching |
| `demo_ceo` | `Demo@123456` | system_admin | admin/manager fallback |
| `demo_rd` | `Demo@123456` | employee | P-type acceptance |
| `demo_ops` | `Demo@123456` | employee | O-type acceptance |
| `demo_recruiter` | `Demo@123456` | employee | F-type acceptance |
| `demo_supply` | `Demo@123456` | manager | M-type acceptance |

Make clear these are local demo credentials, not production credentials.

- [x] **Step 9.2: Add local demo startup commands**

Document:

```powershell
$env:USE_MOCK='true'
uv run python scripts/seed_demo_data.py
uv run python scripts/verify_demo_data.py
uv run python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

In another PowerShell terminal:

```powershell
cd frontend
npm run dev
```

Open:

```text
http://localhost:5173
http://localhost:8000/docs
```

- [x] **Step 9.3: Add S-role live demo script**

Document the live sequence:

```text
1. Login as demo_sales
2. Open Profile and confirm 华东KA销售经理
3. Open P阶段 and analyze/generate/confirm contract
4. Open D阶段 and submit check-ins
5. Generate diagnostic report and apply for coaching
6. Login as demo_manager
7. Open C阶段 and complete evaluation tasks
8. Generate final result
9. Login as demo_sales
10. Confirm result if needed
11. Open A阶段 and generate review report
12. Create development plan
13. Run AI review and show SMART feedback
14. Generate next-cycle inheritance suggestion
```

- [x] **Step 9.4: Add five-role acceptance checklist**

Document:

```text
S: classify as S, 5 indicators, non-redline quantitative weight 85%
P: classify as P, 7 indicators, qualitative weight 45%
O: classify as O, 5 indicators, SOP and production metrics
F: classify as F, 7 indicators, satisfaction/compliance/service metrics
M: classify as M, 6 indicators, strategy/team/long-cycle metrics
```

- [x] **Step 9.5: Run full verification**

Run:

```powershell
$env:USE_MOCK='true'
uv run python scripts/verify_demo_data.py
uv run python scripts/verify_mock_llm_cases.py
uv run python scripts/verify_p_stage_contract.py
uv run python scripts/verify_d_stage_demo.py
uv run python scripts/verify_c_stage_demo.py
uv run python scripts/verify_a_stage_demo.py
cd frontend
npm run build
npm run lint
```

Expected:

```text
DEMO_VERIFY_OK
MOCK_LLM_CASES_OK
P_STAGE_CONTRACT_OK
D_STAGE_DEMO_OK
C_STAGE_DEMO_OK
A_STAGE_DEMO_OK
frontend build exits 0
frontend lint exits 0
```

Suggested commit:

```powershell
git add README.md DEPLOYMENT.md docs/agent-plans/2026-07-06-pdca-demo-execution-report.md
git commit -m "Document PDCA demo operation path"
```

---

## Final Acceptance Criteria

The implementation is complete only when all of these are true:

- [x] `uv run python scripts/seed_demo_data.py` is idempotent.
- [x] `uv run python scripts/verify_demo_data.py` prints `DEMO_VERIFY_OK`.
- [x] `USE_MOCK=true` supports all S/P/O/F/M role cases.
- [x] P-stage generates and confirms a contract for `demo_sales`.
- [x] D-stage check-ins generate a useful diagnostic report.
- [x] D-stage can create a coaching request for the manager.
- [x] C-stage self-assessment, evaluation tasks, final result, and confirmation work.
- [x] A-stage review report, development plan, AI review, approval, and inheritance suggestion work.
- [x] Frontend build passes.
- [x] Frontend lint passes.
- [x] README or deployment docs explain demo accounts and live demo sequence.
- [x] No real secrets are printed or committed.
- [x] No unrelated user changes are reverted.

## Suggested Execution Order

Use this exact order:

```text
Task 0 -> Task 1 -> Task 2 -> Task 3 -> Task 4 -> Task 5 -> Task 6 -> Task 7 -> Task 8 -> Task 9
```

If time is limited before a demo, stop after Task 6 and document remaining gaps. Tasks 1-6 are the minimum to prove the core customer requirement.

## Prompt For The Next Conversation

Copy this into the next Codex conversation:

```text
请执行 C:\Users\32159\Downloads\JX_agent\docs\agent-plans\2026-07-06-pdca-demo-execution-plan.md。

要求：
1. 先阅读计划和当前 git status。
2. 不要覆盖或回滚已有未提交改动。
3. 按任务顺序执行，每完成一个任务更新计划勾选。
4. 优先用 USE_MOCK=true 跑通五类岗位和 demo_sales 的完整 PDCA 链路。
5. 每次修改文件前说明改动范围。
6. 运行计划里的验证命令，失败时先定位根因再修。
```
