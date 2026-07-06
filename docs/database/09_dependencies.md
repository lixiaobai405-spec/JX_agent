## 9. 阶段依赖关系

### 9.1 P阶段 → C阶段数据流转

**流转路径**：
```
job_analyses (岗位分析)
    ↓
job_prototypes (匹配原型)
    ↓
strategy_matrices (获取策略)
    ↓
indicator_templates (生成指标)
    ↓
performance_contracts (生成合约)
    ↓
goals (创建目标) + indicators (创建指标)
```

**关键外键**：
- `goals.performance_contract_id` → `performance_contracts.id`
- `indicators.template_id` → `indicator_templates.id`

**业务规则**：
- P阶段完成后，数据流入C阶段
- 合约确认后才能开始考核

---

### 9.2 P阶段 → D阶段数据流转

**流转路径**：
```
performance_contracts (绩效合约)
    ↓
goals (绩效目标) + indicators (绩效指标)
    ↓
checkin_tasks (生成填报任务)
    ↓
checkin_records (员工填报数据)
    ↓
diagnostic_reports (AI诊断报告)
    ↓
progress_records (进度记录)
```

**关键外键**：
- `goals.performance_contract_id` → `performance_contracts.id`
- `indicators.goal_id` → `goals.id`
- `checkin_tasks.indicator_id` → `indicators.id`
- `checkin_records.checkin_task_id` → `checkin_tasks.id`
- `progress_records.indicator_id` → `indicators.id`

**业务规则**：
- P 阶段完成后，基于 goals 和 indicators 生成 D 阶段的填报任务
- D 阶段在考核周期内持续运行（自循环）
- 填报周期由 P 阶段的策略决定（周推送/月推送）

---

### 9.3 D阶段 → C阶段数据支撑

**数据支撑路径**：
```
checkin_records (填报记录) ─┐
diagnostic_reports (诊断报告) ─┤
progress_records (进度数据) ─┤
                            ↓
                    C阶段评估时作为参考依据
                            ↓
                    evaluations (评价打分)
```

**关键说明**：
- D 阶段不"进入"C 阶段，而是当考核周期结束时，C 阶段自动触发
- C 阶段的评价人在打分时，可以查看 D 阶段积累的数据：
  - checkin_records：查看员工的实际完成数据
  - diagnostic_reports：了解执行过程中的问题和改进情况
  - progress_records：查看进度趋势
- 这些数据为 C 阶段的评价提供客观依据

**业务规则**：
- D 阶段数据为只读参考，不直接参与 C 阶段的评分计算
- C 阶段的触发条件是 periods.end_date 到期，而非 D 阶段完成

---

### 9.4 C阶段 → A阶段数据流转

**流转路径**：
```
evaluations (评价)
    ↓
score_aggregates (分数汇总)
    ↓
final_results (最终结果)
    ↓
review_reports (复盘报告)
    ↓
development_plans (发展计划)
```

**关键外键**：
- `score_aggregates.goal_id` → `goals.id`
- `final_results.computed_score_id` → `score_aggregates.id`
- `review_reports.final_result_id` → `final_results.id`
- `development_plans.review_report_id` → `review_reports.id`

**业务规则**：
- C阶段考核完成后进入A阶段
- 基于考核结果生成复盘和发展计划

---

### 9.5 A阶段 → P阶段数据继承

**继承路径**：
```
final_results (考核结果) → review_reports (复盘报告)
    ↓
development_plans (发展计划)
    ↓
inheritance_suggestions (继承建议) ← AI 分析生成
    ↓
new period (新周期) → performance_contracts (新合约)
    ↓
goals (新目标) + indicators (新指标)
```

**触发条件**：
- development_plans.status = 'approved'
- 新周期 periods.status = 'draft' 或 'open'
- 上一周期 final_results.status = 'confirmed'

**继承逻辑**：
- AI 分析 development_plans.goals 中的能力提升目标
- 提取未完成的发展项（completion_status != 'completed'）
- 结合 final_results.final_grade 判断是否需要延续改进
- 生成 inheritance_suggestions，包含具体的目标/指标建议

**转换规则**：
- 发展计划中的"能力提升目标" → 新周期的"绩效指标"
- 上周期低分指标（<70分）→ 建议在新周期保留并提高权重
- 上周期高分指标（>90分）→ 建议提高目标值或降低权重
- 红线指标 → 必须延续到新周期

**adoption 追踪**：
- 当用户接受建议并创建新 goal 时，记录 adopted_goal_id
- 当用户接受建议并创建新 indicator 时，记录 adopted_indicator_id
- 支持部分采纳（用户可修改建议后使用）

**关键外键**：
- `inheritance_suggestions.previous_development_plan_id` → `development_plans.id`
- `inheritance_suggestions.previous_final_result_id` → `final_results.id`
- `inheritance_suggestions.new_period_id` → `periods.id`
- `inheritance_suggestions.adopted_goal_id` → `goals.id`
- `inheritance_suggestions.adopted_indicator_id` → `indicators.id`

**业务规则**：
- A阶段发展计划可继承到下周期
- 实现持续改进的PDCA闭环

---

### 9.6 完整PDCA循环图

```
┌─────────────────────────────────────────────────────────────┐
│                      PDCA 完整循环                           │
└─────────────────────────────────────────────────────────────┘

P阶段 (智能定标)
┌──────────────────────────────────────────┐
│ job_analyses → job_prototypes            │
│      ↓                                    │
│ strategy_matrices → indicator_templates  │
│      ↓                                    │
│ performance_contracts                    │
│      ↓                                    │
│ goals + indicators                       │
└──────────────┬───────────────────────────┘
               ↓
D阶段 (执行追踪 - 周期内自循环)
┌──────────────────────────────────────────┐
│ ┌─────────────────────────────────┐      │
│ │  checkin_tasks (推送填报任务)    │      │
│ │         ↓                        │      │
│ │  checkin_records (员工填报)      │      │
│ │         ↓                        │      │
│ │  diagnostic_reports (AI诊断)    │      │
│ │         ↓                        │      │
│ │  coaching_requests (申请辅导)    │      │
│ │         ↓                        │      │
│ │  progress_records (进度记录)     │      │
│ │         ↓                        │      │
│ └─────────┴─────────────────────┘        │
│           (循环往复，直到考核周期结束)     │
└──────────────┬───────────────────────────┘
               ↓ (考核周期结束，自动触发)
C阶段 (考核评估)
┌──────────────────────────────────────────┐
│ self_assessments (员工自评)              │
│      ↓                                    │
│ evaluation_tasks (生成评价任务)          │
│      ↓                                    │
│ evaluations (评价人打分)                 │
│      ↓                                    │
│ score_aggregates (分数汇总)              │
│      ↓                                    │
│ grade_rules (应用等级规则)               │
│      ↓                                    │
│ final_results (最终结果)                 │
└──────────────┬───────────────────────────┘
               ↓
A阶段 (复盘发展)
┌──────────────────────────────────────────┐
│ review_reports (AI复盘报告)              │
│      ↓                                    │
│ development_plans (发展计划)             │
│      ↓                                    │
│ inheritance_suggestions (继承建议)       │
└──────────────┬───────────────────────────┘
               ↓
         (回到P阶段 - 新周期)
```

**关键说明**：

1. **P → D**：P 阶段完成后，进入 D 阶段执行追踪
2. **D 阶段自循环**：在考核周期内，D 阶段持续运行（填报→诊断→反馈→填报...）
3. **D → C**：当考核周期结束时（由 periods 表的 end_date 控制），自动触发 C 阶段
4. **C 阶段使用 D 阶段数据**：C 阶段评估时参考 D 阶段积累的 checkin_records、diagnostic_reports、progress_records
5. **C → A**：C 阶段完成后进入 A 阶段
6. **A → P**：A 阶段的 inheritance_suggestions 连接到下一周期的 P 阶段

---

### 9.7 核心表关系总览

**组织架构层**：
```
users ←→ departments ←→ positions
```

**周期管理层**：
```
periods → goals → indicators
```

**P阶段层**：
```
job_prototypes → strategy_matrices
       ↓
job_analyses → performance_contracts → goals
       ↓
indicator_templates → indicators
```

**C阶段层**：
```
goals → indicators → evaluation_tasks → evaluations
  ↓                        ↓
self_assessments    score_aggregates → final_results
                           ↓
                    grade_rules
```

**D阶段层**：
```
indicators → checkin_tasks → checkin_records
      ↓              ↓
progress_records  diagnostic_reports → coaching_requests
```

**A阶段层**：
```
final_results → review_reports → development_plans → inheritance_suggestions
```

**支持层**：
```
comments (多态关联所有资源)
audit_logs (记录所有操作)
ai_generation_logs (记录AI调用)
```

---
