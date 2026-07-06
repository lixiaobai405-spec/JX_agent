## 5. C阶段-考核评估

### 5.1 goals（绩效目标表）

**功能说明**：个人绩效目标/合约，C阶段核心表

**表结构**：

| 列名 | 类型 | 说明 | 示例 | 约束 |
|------|------|------|------|------|
| id | VARCHAR(36) | 目标ID | "goal-001" | PRIMARY KEY |
| owner_user_id | VARCHAR(36) | 目标责任人 | "user-001" | FOREIGN KEY → users.id, NOT NULL |
| period_id | VARCHAR(36) | 考核周期 | "period-2026-q1" | FOREIGN KEY → periods.id, NOT NULL |
| title | VARCHAR | 目标标题 | "2026Q1个人绩效目标" | NOT NULL |
| description | VARCHAR | 目标描述 | "完成核心项目开发" | NULLABLE |
| created_by | VARCHAR(36) | 创建者 | "user-002" | FOREIGN KEY → users.id, NOT NULL |
| ai_generated | BOOLEAN | 是否AI生成 | true | DEFAULT false |
| performance_contract_id | VARCHAR(36) | 绩效合约ID | "contract-001" | FOREIGN KEY → performance_contracts.id, NULLABLE |
| created_at | TIMESTAMP | 创建时间 | "2026-01-20 10:00:00" | NOT NULL |
| updated_at | TIMESTAMP | 更新时间 | "2026-01-20 10:00:00" | NOT NULL |
| deleted_at | TIMESTAMP | 删除时间 | NULL | NULLABLE |

**外键关系**：
- owner_user_id → users.id
- period_id → periods.id
- created_by → users.id
- performance_contract_id → performance_contracts.id

**索引设计**：
- PRIMARY KEY (id)
- INDEX (owner_user_id, period_id)
- INDEX (performance_contract_id)

**业务约束**：
- 每个用户每个周期可有多个目标
- 链接P阶段的performance_contract

---

### 5.2 indicators（绩效指标表）

**功能说明**：具体考核指标/KPI

**表结构**：

| 列名 | 类型 | 说明 | 示例 | 约束 |
|------|------|------|------|------|
| id | VARCHAR(36) | 指标ID | "indicator-001" | PRIMARY KEY |
| goal_id | VARCHAR(36) | 所属目标 | "goal-001" | FOREIGN KEY → goals.id, NOT NULL |
| name | VARCHAR | 指标名称 | "项目按期交付率" | NOT NULL |
| definition | VARCHAR | 指标定义 | "按期交付项目数/总项目数" | NULLABLE |
| direction | ENUM | 指标方向 | "positive" | NOT NULL, 可选值: positive/negative |
| weight | FLOAT | 指标权重 | 0.3 | NOT NULL, 范围: 0-1 |
| target_value | FLOAT | 目标值 | 95.0 | NULLABLE |
| score_method | ENUM | 计分方法 | "ratio" | NOT NULL, 可选值: ratio/mapping/binary/manual |
| redline | BOOLEAN | 是否红线指标 | false | DEFAULT false |
| is_team_indicator | BOOLEAN | 是否团队指标 | false | DEFAULT false |
| source | VARCHAR | 指标来源 | "组织目标分解" | NULLABLE |
| template_id | VARCHAR(36) | 模板ID | "template-001" | FOREIGN KEY → indicator_templates.id, NULLABLE |
| created_at | TIMESTAMP | 创建时间 | "2026-01-20 10:00:00" | NOT NULL |
| updated_at | TIMESTAMP | 更新时间 | "2026-01-20 10:00:00" | NOT NULL |
| deleted_at | TIMESTAMP | 删除时间 | NULL | NULLABLE |

**外键关系**：
- goal_id → goals.id
- template_id → indicator_templates.id

**索引设计**：
- PRIMARY KEY (id)
- INDEX (goal_id)

**业务约束**：
- 同一goal下所有指标权重之和必须为1.0
- 红线指标不达标则整体考核不合格

---

### 5.3 self_assessments（自评表）

**功能说明**：员工自评记录

**表结构**：

| 列名 | 类型 | 说明 | 示例 | 约束 |
|------|------|------|------|------|
| id | VARCHAR(36) | 自评ID | "self-001" | PRIMARY KEY |
| goal_id | VARCHAR(36) | 对应目标 | "goal-001" | FOREIGN KEY → goals.id, NOT NULL |
| user_id | VARCHAR(36) | 提交用户 | "user-001" | FOREIGN KEY → users.id, NOT NULL |
| submitted_at | TIMESTAMP | 提交时间 | "2026-03-25 10:00:00" | NULLABLE |
| items | JSON | 自评项数据 | {"indicator-001": {"score": 90, "comment": "..."}} | NOT NULL |
| status | ENUM | 状态 | "submitted" | NOT NULL, 可选值: draft/submitted/withdrawn |
| created_at | TIMESTAMP | 创建时间 | "2026-03-20 10:00:00" | NOT NULL |
| updated_at | TIMESTAMP | 更新时间 | "2026-03-25 10:00:00" | NOT NULL |
| deleted_at | TIMESTAMP | 删除时间 | NULL | NULLABLE |

**外键关系**：
- goal_id → goals.id
- user_id → users.id

**索引设计**：
- PRIMARY KEY (id)
- INDEX (goal_id)
- INDEX (user_id)

**业务约束**：
- 每个goal每个用户只能有一条自评记录
- 提交后不可修改（需撤回后重新提交）

---

### 5.4 evaluation_tasks（评价任务表）

**功能说明**：分配给他人的评价任务

**表结构**：

| 列名 | 类型 | 说明 | 示例 | 约束 |
|------|------|------|------|------|
| id | VARCHAR(36) | 任务ID | "task-001" | PRIMARY KEY |
| goal_id | VARCHAR(36) | 对应目标 | "goal-001" | FOREIGN KEY → goals.id, NOT NULL |
| indicator_id | VARCHAR(36) | 具体指标 | "indicator-001" | FOREIGN KEY → indicators.id, NULLABLE |
| evaluator_user_id | VARCHAR(36) | 评价人 | "user-002" | FOREIGN KEY → users.id, NOT NULL |
| assigned_by | VARCHAR(36) | 分配人 | "user-003" | FOREIGN KEY → users.id, NOT NULL |
| status | ENUM | 状态 | "pending" | NOT NULL, 可选值: pending/completed/expired |
| assigned_at | TIMESTAMP | 分配时间 | "2026-03-20 10:00:00" | NOT NULL |
| due_at | TIMESTAMP | 截止时间 | "2026-03-30 23:59:59" | NOT NULL |
| created_at | TIMESTAMP | 创建时间 | "2026-03-20 10:00:00" | NOT NULL |
| updated_at | TIMESTAMP | 更新时间 | "2026-03-25 15:00:00" | NOT NULL |
| deleted_at | TIMESTAMP | 删除时间 | NULL | NULLABLE |

**外键关系**：
- goal_id → goals.id
- indicator_id → indicators.id
- evaluator_user_id → users.id
- assigned_by → users.id

**索引设计**：
- PRIMARY KEY (id)
- INDEX (goal_id)
- INDEX (evaluator_user_id, status)

**业务约束**：
- indicator_id为空表示整体评价
- 过期未完成自动标记为expired

---

### 5.5 evaluations（评价表）

**功能说明**：具体评价分数和评语

**表结构**：

| 列名 | 类型 | 说明 | 示例 | 约束 |
|------|------|------|------|------|
| id | VARCHAR(36) | 评价ID | "eval-001" | PRIMARY KEY |
| task_id | VARCHAR(36) | 所属任务 | "task-001" | FOREIGN KEY → evaluation_tasks.id, NOT NULL |
| goal_id | VARCHAR(36) | 对应目标 | "goal-001" | FOREIGN KEY → goals.id, NOT NULL |
| indicator_id | VARCHAR(36) | 具体指标 | "indicator-001" | FOREIGN KEY → indicators.id, NOT NULL |
| evaluator_id | VARCHAR(36) | 评价人 | "user-002" | FOREIGN KEY → users.id, NOT NULL |
| score | FLOAT | 评价分数 | 85.5 | NOT NULL, 范围: 0-100 |
| comment | VARCHAR | 评价评语 | "完成质量较高" | NULLABLE |
| created_at | TIMESTAMP | 创建时间 | "2026-03-25 15:00:00" | NOT NULL |
| updated_at | TIMESTAMP | 更新时间 | "2026-03-25 15:00:00" | NOT NULL |
| deleted_at | TIMESTAMP | 删除时间 | NULL | NULLABLE |

**外键关系**：
- task_id → evaluation_tasks.id
- goal_id → goals.id
- indicator_id → indicators.id
- evaluator_id → users.id

**索引设计**：
- PRIMARY KEY (id)
- INDEX (task_id)
- INDEX (goal_id, indicator_id)

**业务约束**：
- 每个task只能提交一次评价
- 分数范围0-100

---

### 5.6 score_aggregates（分数汇总表）

**功能说明**：计算后的分数汇总

**表结构**：

| 列名 | 类型 | 说明 | 示例 | 约束 |
|------|------|------|------|------|
| id | VARCHAR(36) | 汇总ID | "agg-001" | PRIMARY KEY |
| goal_id | VARCHAR(36) | 对应目标 | "goal-001" | FOREIGN KEY → goals.id, NOT NULL |
| final_score | FLOAT | 最终总分 | 87.5 | NOT NULL, 范围: 0-100 |
| breakdown | JSON | 各指标分数明细 | {"indicator-001": 85, "indicator-002": 90} | NOT NULL |
| computed_at | TIMESTAMP | 计算时间 | "2026-03-31 10:00:00" | NOT NULL |
| created_at | TIMESTAMP | 创建时间 | "2026-03-31 10:00:00" | NOT NULL |
| updated_at | TIMESTAMP | 更新时间 | "2026-03-31 10:00:00" | NOT NULL |
| deleted_at | TIMESTAMP | 删除时间 | NULL | NULLABLE |

**外键关系**：
- goal_id → goals.id

**索引设计**：
- PRIMARY KEY (id)
- UNIQUE INDEX (goal_id)

**业务约束**：
- 每个goal只有一条汇总记录
- final_score = Σ(指标分数 × 权重)

---

### 5.7 grade_rules（等级规则表）

**功能说明**：等级匹配规则配置

**表结构**：

| 列名 | 类型 | 说明 | 示例 | 约束 |
|------|------|------|------|------|
| id | VARCHAR(36) | 规则ID | "rule-001" | PRIMARY KEY |
| period_id | VARCHAR(36) | 所属周期 | "period-2026-q1" | FOREIGN KEY → periods.id, NOT NULL |
| mode | ENUM | 定级模式 | "absolute" | NOT NULL, 可选值: absolute/relative |
| absolute_bands | JSON | 绝对定级规则 | {"S": 95, "A": 90, "B": 80, "C": 70, "D": 0} | NULLABLE |
| relative_distribution | JSON | 强制分布比例 | {"S": 0.05, "A": 0.15, "B": 0.60, "C": 0.15, "D": 0.05} | NULLABLE |
| fallback_strategy | JSON | 后备策略 | {"use_absolute_if_small_team": true} | NULLABLE |
| created_at | TIMESTAMP | 创建时间 | "2026-01-01 10:00:00" | NOT NULL |
| updated_at | TIMESTAMP | 更新时间 | "2026-01-01 10:00:00" | NOT NULL |
| deleted_at | TIMESTAMP | 删除时间 | NULL | NULLABLE |

**外键关系**：
- period_id → periods.id

**索引设计**：
- PRIMARY KEY (id)
- INDEX (period_id)

**业务约束**：
- absolute模式：按分数段定级
- relative模式：按排名强制分布

---

### 5.8 final_results（最终结果表）

**功能说明**：最终确认的考核结果

**表结构**：

| 列名 | 类型 | 说明 | 示例 | 约束 |
|------|------|------|------|------|
| id | VARCHAR(36) | 结果ID | "result-001" | PRIMARY KEY |
| goal_id | VARCHAR(36) | 对应目标 | "goal-001" | FOREIGN KEY → goals.id, NOT NULL |
| computed_score_id | VARCHAR(36) | 计算分数ID | "agg-001" | FOREIGN KEY → score_aggregates.id, NULLABLE |
| suggested_grade | VARCHAR | 建议等级 | "A" | NULLABLE |
| final_grade | VARCHAR | 最终等级 | "A" | NOT NULL |
| confirmed_by | VARCHAR(36) | 确认人 | "user-003" | FOREIGN KEY → users.id, NOT NULL |
| confirmed_at | TIMESTAMP | 确认时间 | "2026-04-05 10:00:00" | NOT NULL |
| adjustment_reason | VARCHAR | 调整原因 | "特殊贡献加分" | NULLABLE |
| status | ENUM | 状态 | "confirmed" | NOT NULL, 可选值: pending/confirmed/adjusted/archived |
| created_at | TIMESTAMP | 创建时间 | "2026-04-01 10:00:00" | NOT NULL |
| updated_at | TIMESTAMP | 更新时间 | "2026-04-05 10:00:00" | NOT NULL |
| deleted_at | TIMESTAMP | 删除时间 | NULL | NULLABLE |

**外键关系**：
- goal_id → goals.id
- computed_score_id → score_aggregates.id
- confirmed_by → users.id

**索引设计**：
- PRIMARY KEY (id)
- UNIQUE INDEX (goal_id)
- INDEX (final_grade)

**业务约束**：
- 每个goal只有一条最终结果
- 可手动调整等级（需记录原因）

---
