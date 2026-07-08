# PDCA Demo Flow Execution Report

## 目标

为绩效智能体补齐可重复的本地 Mock 演示链路，覆盖五类岗位 S/P/O/F/M，并让 `demo_sales` 可以跑通完整 PDCA：

```text
JD input -> P 合约生成与确认 -> D 打卡与诊断 -> C 自评/经理评分/定级 -> A 复盘/IDP/继承建议
```

## 已完成事项

- 新增幂等 demo 数据脚本：`scripts/seed_demo_data.py`
- 新增 demo 数据校验脚本：`scripts/verify_demo_data.py`
- 补齐 `USE_MOCK=true` 下 S/P/O/F/M 五类岗位分类与指标生成。
- 新增五类岗位 Mock 校验：`scripts/verify_mock_llm_cases.py`
- 修复 P 阶段合约校验、指标方向映射、红线处理和展示元数据持久化。
- 新增 P 阶段校验：`scripts/verify_p_stage_contract.py`
- 修复 D 阶段反向指标计算、完整诊断字段落库。
- 新增 D 阶段校验：`scripts/verify_d_stage_demo.py`
- 修复 C 阶段评估任务重复生成、最终结果重复生成问题。
- 新增 C 阶段校验：`scripts/verify_c_stage_demo.py`
- 修复 A 阶段 Mock SMART 审核输出，补齐 IDP 审批和继承建议验证。
- 新增 A 阶段校验：`scripts/verify_a_stage_demo.py`
- 新增 API smoke script：`scripts/verify_pdca_demo_flow.py`
- 前端补齐诊断报告收起、辅导请求查看、A 阶段经理审批、继承建议下期周期逻辑和 query invalidation。
- README/DEPLOYMENT 已补充 demo 账号、启动命令和验收清单。

## Demo 账号

| username | password | role | use |
|---|---|---|---|
| `demo_sales` | `Demo@123456` | employee | 员工 PDCA 主流程 |
| `demo_manager` | `Demo@123456` | manager | 经理评分、辅导和审批 |
| `demo_ceo` | `Demo@123456` | system_admin | 管理员/高管兜底 |
| `demo_rd` | `Demo@123456` | employee | P 类项目型验收 |
| `demo_ops` | `Demo@123456` | employee | O 类运营型验收 |
| `demo_recruiter` | `Demo@123456` | employee | F 类职能型验收 |
| `demo_supply` | `Demo@123456` | manager | M 类管理型验收 |

这些账号仅用于本地演示。

## 最近验证结果

```text
uv run python scripts/verify_demo_data.py
DEMO_VERIFY_OK

$env:USE_MOCK='true'
uv run python scripts/verify_mock_llm_cases.py
MOCK_LLM_CASES_OK

uv run python scripts/verify_p_stage_contract.py
P_STAGE_CONTRACT_OK

uv run python scripts/verify_d_stage_demo.py
D_STAGE_DEMO_OK

uv run python scripts/verify_c_stage_demo.py
C_STAGE_DEMO_OK

uv run python scripts/verify_a_stage_demo.py
A_STAGE_DEMO_OK

uv run python scripts/verify_pdca_demo_flow.py
PDCA_DEMO_FLOW_OK

cd frontend
npm run build
npm run lint
```

前端 build 通过，Vite 仍有 chunk-size warning，可接受。

## 五类岗位验收

| code | 验收点 |
|---|---|
| S | 分类为 S，5 个指标，非红线定量权重 85%，月度周期 |
| P | 分类为 P，7 个指标，定性权重 45%，季度周期 |
| O | 分类为 O，5 个指标，生产/SOP/质量数据驱动，月度周期 |
| F | 分类为 F，7 个指标，满意度/合规/响应效率，月度周期 |
| M | 分类为 M，6 个指标，战略分解/团队赋能/长周期，半年度周期 |

## 注意事项

- 不要删除 `jx-db.db`；demo 脚本通过幂等 upsert 和 demo-owned 数据修正运行。
- `verify_p_stage_contract.py` 会关闭同一 demo 用户旧的 `绩效演示周期` open 状态，避免一个用户多个 open 周期导致合约无法打开计划周期。
- `verify_*_demo.py` 会写入本地演示数据，适合本地验收，不应对生产库运行。
- 本地 API smoke script 需要后端已在 `http://127.0.0.1:8000` 运行。
