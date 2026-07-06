## 7. A阶段-复盘发展

### 7.1 review_reports（复盘报告表）

**功能说明**：基于考核结果的AI复盘报告

**表结构**：

| 列名 | 类型 | 说明 | 示例 | 约束 |
|------|------|------|------|------|
| id | VARCHAR(36) | 报告ID | "review-001" | PRIMARY KEY |
| final_result_id | VARCHAR(36) | 最终结果ID | "result-001" | FOREIGN KEY → final_results.id, NOT NULL |
| user_id | VARCHAR(36) | 用户ID | "user-001" | FOREIGN KEY → users.id, NOT NULL |
| report_type | VARCHAR(20) | 报告类型 | "s_a" | NOT NULL, 可选值: s_a/b/c (对应绩效等级) |
| strengths_analysis | JSON | 优势分析 | {"strengths": [...]} | NULLABLE |
| improvement_areas | JSON | 待改进项 | {"areas": [...]} | NULLABLE |
| development_suggestions | JSON | 发展建议 | {"suggestions": [...]} | NULLABLE |
| ai_generated | BOOLEAN | 是否AI生成 | true | DEFAULT false |
| generated_at | TIMESTAMP | 生成时间 | "2026-04-10 10:00:00" | NOT NULL |
| reviewed_by_user | BOOLEAN | 用户已查看 | true | DEFAULT false |
| user_feedback | TEXT | 用户反馈 | "建议很有帮助" | NULLABLE |
| next_cycle_focus_areas | JSON | 下周期重点领域 | {"areas": ["技术深度", "项目管理"]} | NULLABLE |
| created_at | TIMESTAMP | 创建时间 | "2026-04-10 10:00:00" | NOT NULL |

**外键关系**：
- final_result_id → final_results.id
- user_id → users.id

**索引设计**：
- PRIMARY KEY (id)
- UNIQUE INDEX (final_result_id)
- INDEX (user_id)

**业务约束**：
- 每个final_result只有一份复盘报告
- 根据绩效等级生成不同类型报告

---

### 7.2 development_plans（发展计划表）

**功能说明**：个人发展计划（IDP）

**表结构**：

| 列名 | 类型 | 说明 | 示例 | 约束 |
|------|------|------|------|------|
| id | VARCHAR(36) | 计划ID | "plan-001" | PRIMARY KEY |
| review_report_id | VARCHAR(36) | 复盘报告ID | "review-001" | FOREIGN KEY → review_reports.id, NOT NULL |
| user_id | VARCHAR(36) | 用户ID | "user-001" | FOREIGN KEY → users.id, NOT NULL |
| plan_version | INT | 计划版本 | 1 | DEFAULT 1 |
| goals | JSON | 目标项数组 | [{"goal": "提升技术能力", ...}] | NOT NULL |
| actions | JSON | 行动措施 | [{"action": "学习新技术", ...}] | NOT NULL |
| required_resources | JSON | 所需资源 | [{"resource": "培训预算", ...}] | NULLABLE |
| timeline | JSON | 时间安排 | {"start": "2026-04", "end": "2026-06"} | NULLABLE |
| smart_evaluation | JSON | SMART原则评估 | {"specific": true, ...} | NULLABLE |
| ai_reviewed | BOOLEAN | AI已审核 | true | DEFAULT false |
| ai_suggestions | JSON | AI建议 | {"suggestions": [...]} | NULLABLE |
| status | VARCHAR(20) | 状态 | "approved" | DEFAULT 'draft', 可选值: draft/reviewed/approved/active/completed |
| approved_by | VARCHAR(36) | 审批人 | "user-002" | FOREIGN KEY → users.id, NULLABLE |
| approved_at | TIMESTAMP | 审批时间 | "2026-04-15 10:00:00" | NULLABLE |
| created_at | TIMESTAMP | 创建时间 | "2026-04-12 10:00:00" | NOT NULL |
| updated_at | TIMESTAMP | 更新时间 | "2026-04-15 10:00:00" | NOT NULL |
| completion_status | VARCHAR(20) | 完成状态 | "in_progress" | DEFAULT 'not_started', 可选值: not_started/in_progress/completed/carried_forward |
| completion_rate | FLOAT | 完成率 | 0.65 | NULLABLE, 范围: 0-1 |
| carry_forward_reason | TEXT | 延续原因 | "技术能力提升需要更长时间" | NULLABLE |
| linked_to_next_cycle | BOOLEAN | 是否已链接到下周期 | true | DEFAULT false |

**外键关系**：
- review_report_id → review_reports.id
- user_id → users.id
- approved_by → users.id

**索引设计**：
- PRIMARY KEY (id)
- INDEX (review_report_id)
- INDEX (user_id, status)

**业务约束**：
- 支持多版本迭代
- AI审核SMART原则符合性

---

### 7.3 inheritance_suggestions（目标继承建议表）

**功能说明**：AI生成的下周期目标继承建议

**表结构**：

| 列名 | 类型 | 说明 | 示例 | 约束 |
|------|------|------|------|------|
| id | VARCHAR(36) | 建议ID | "inherit-001" | PRIMARY KEY |
| user_id | VARCHAR(36) | 用户ID | "user-001" | FOREIGN KEY → users.id, NOT NULL |
| previous_development_plan_id | VARCHAR(36) | 上期发展计划 | "plan-001" | FOREIGN KEY → development_plans.id, NOT NULL |
| previous_final_result_id | VARCHAR(36) | 上期考核结果 | "result-001" | FOREIGN KEY → final_results.id, NOT NULL |
| new_period_id | VARCHAR(36) | 新周期ID | "period-2026-q2" | FOREIGN KEY → periods.id, NOT NULL |
| suggestion_type | VARCHAR(20) | 建议类型 | "new_indicator" | NOT NULL, 可选值: new_goal/new_indicator/adjust_weight/raise_target |
| suggestions | JSON | 继承建议内容 | {"inherit_goals": [...]} | NOT NULL |
| adopted_goal_id | VARCHAR(36) | 采纳后的目标ID | "goal-101" | FOREIGN KEY → goals.id, NULLABLE |
| adopted_indicator_id | VARCHAR(36) | 采纳后的指标ID | "indicator-201" | FOREIGN KEY → indicators.id, NULLABLE |
| adoption_modifications | JSON | 用户修改记录 | {"original_weight": 0.3, "adopted_weight": 0.25} | NULLABLE |
| status | VARCHAR(20) | 状态 | "pending" | DEFAULT 'pending', 可选值: pending/accepted/rejected/partially_adopted |
| rejected_reason | TEXT | 拒绝原因 | "该目标已不适用当前岗位" | NULLABLE |
| accepted_at | TIMESTAMP | 接受时间 | "2026-04-20 10:00:00" | NULLABLE |
| created_at | TIMESTAMP | 创建时间 | "2026-04-18 10:00:00" | NOT NULL |

**外键关系**：
- user_id → users.id
- previous_development_plan_id → development_plans.id
- previous_final_result_id → final_results.id
- new_period_id → periods.id
- adopted_goal_id → goals.id
- adopted_indicator_id → indicators.id

**索引设计**：
- PRIMARY KEY (id)
- INDEX (user_id, new_period_id)
- INDEX (previous_development_plan_id)

**业务约束**：
- 连接A阶段和下一周期P阶段
- 实现PDCA闭环

**suggestions JSON 结构**：

```json
{
  "suggestion_type": "new_indicator",
  "source_analysis": {
    "from_development_plan": {
      "goal_id": "dev-goal-001",
      "goal_name": "提升Java并发编程能力",
      "completion_status": "in_progress",
      "completion_rate": 0.65
    },
    "from_previous_performance": {
      "indicator_id": "indicator-005",
      "indicator_name": "代码质量评分",
      "previous_score": 72,
      "below_target": true
    }
  },
  "recommendation": {
    "indicator_name": "并发编程项目质量",
    "indicator_definition": "并发编程项目的代码质量、性能指标综合评分",
    "recommended_weight": 0.20,
    "recommended_target_value": 85,
    "rationale": "上周期代码质量评分偏低(72分)，且发展计划中明确提出提升并发编程能力，建议在新周期加大权重"
  },
  "confidence_score": 0.88
}
```

---
