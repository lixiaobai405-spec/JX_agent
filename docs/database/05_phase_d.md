## 6. D阶段-执行追踪

### 6.1 checkin_tasks（填报任务表）

**功能说明**：定期填报任务生成

**表结构**：

| 列名 | 类型 | 说明 | 示例 | 约束 |
|------|------|------|------|------|
| id | VARCHAR(36) | 任务ID | "checkin-001" | PRIMARY KEY |
| indicator_id | VARCHAR(36) | 关联指标 | "indicator-001" | FOREIGN KEY → indicators.id, NOT NULL |
| user_id | VARCHAR(36) | 填报人 | "user-001" | FOREIGN KEY → users.id, NOT NULL |
| period_type | VARCHAR(20) | 周期类型 | "weekly" | NOT NULL, 可选值: weekly/monthly/quarterly |
| due_date | DATE | 截止日期 | "2026-02-07" | NOT NULL |
| status | VARCHAR(20) | 状态 | "pending" | DEFAULT 'pending', 可选值: pending/completed/overdue/skipped |
| reminder_sent | BOOLEAN | 是否已提醒 | false | DEFAULT false |
| created_at | TIMESTAMP | 创建时间 | "2026-02-01 00:00:00" | NOT NULL |
| updated_at | TIMESTAMP | 更新时间 | "2026-02-05 10:00:00" | NOT NULL |

**外键关系**：
- indicator_id → indicators.id
- user_id → users.id

**索引设计**：
- PRIMARY KEY (id)
- INDEX (indicator_id, user_id)
- INDEX (due_date, status)

**业务约束**：
- 系统自动生成填报任务
- 过期未完成标记为overdue

---

### 6.2 checkin_records（填报记录表）

**功能说明**：实际填报的数据记录

**表结构**：

| 列名 | 类型 | 说明 | 示例 | 约束 |
|------|------|------|------|------|
| id | VARCHAR(36) | 记录ID | "record-001" | PRIMARY KEY |
| checkin_task_id | VARCHAR(36) | 所属任务 | "checkin-001" | FOREIGN KEY → checkin_tasks.id, NOT NULL |
| indicator_id | VARCHAR(36) | 关联指标 | "indicator-001" | FOREIGN KEY → indicators.id, NOT NULL |
| user_id | VARCHAR(36) | 填报人 | "user-001" | FOREIGN KEY → users.id, NOT NULL |
| actual_value | JSON | 实际值 | {"value": 85, "unit": "%"} | NOT NULL |
| note | TEXT | 备注说明 | "本周完成3个项目" | NULLABLE |
| attachment_url | TEXT | 附件URL | "https://..." | NULLABLE |
| submitted_at | TIMESTAMP | 提交时间 | "2026-02-05 15:00:00" | NOT NULL |
| created_at | TIMESTAMP | 创建时间 | "2026-02-05 15:00:00" | NOT NULL |

**外键关系**：
- checkin_task_id → checkin_tasks.id
- indicator_id → indicators.id
- user_id → users.id

**索引设计**：
- PRIMARY KEY (id)
- INDEX (checkin_task_id)
- INDEX (indicator_id, submitted_at)

**业务约束**：
- 每个task可提交多次记录（修正数据）
- actual_value支持多种数据类型

---

### 6.3 diagnostic_reports（诊断报告表）

**功能说明**：AI生成的进度诊断报告

**表结构**：

| 列名 | 类型 | 说明 | 示例 | 约束 |
|------|------|------|------|------|
| id | VARCHAR(36) | 报告ID | "diag-001" | PRIMARY KEY |
| goal_id | VARCHAR(36) | 对应目标 | "goal-001" | FOREIGN KEY → goals.id, NOT NULL |
| user_id | VARCHAR(36) | 用户ID | "user-001" | FOREIGN KEY → users.id, NOT NULL |
| report_date | DATE | 报告日期 | "2026-02-15" | NOT NULL |
| overall_progress | FLOAT | 总进度百分比 | 65.5 | NULLABLE |
| weighted_achievement_rate | FLOAT | 加权达成率 | 68.2 | NULLABLE |
| time_progress | FLOAT | 时间进度 | 50.0 | NULLABLE |
| progress_deviation | FLOAT | 进度偏差 | -18.2 | NULLABLE |
| indicators_analysis | JSON | 各指标分析 | {"indicator-001": {...}} | NULLABLE |
| root_cause_analysis | JSON | 根因分析 | {"causes": [...]} | NULLABLE |
| improvement_suggestions | JSON | 改进建议 | {"suggestions": [...]} | NULLABLE |
| traffic_light_status | VARCHAR(10) | 红绿灯状态 | "yellow" | NULLABLE, 可选值: green/yellow/red |
| generated_by_ai | BOOLEAN | 是否AI生成 | true | DEFAULT false |
| created_at | TIMESTAMP | 创建时间 | "2026-02-15 10:00:00" | NOT NULL |

**外键关系**：
- goal_id → goals.id
- user_id → users.id

**索引设计**：
- PRIMARY KEY (id)
- INDEX (goal_id, report_date)
- INDEX (user_id)

**业务约束**：
- 定期自动生成诊断报告
- 红绿灯状态：green(正常)/yellow(预警)/red(严重偏离)

---

### 6.4 coaching_requests（辅导请求表）

**功能说明**：基于诊断报告的辅导请求

**表结构**：

| 列名 | 类型 | 说明 | 示例 | 约束 |
|------|------|------|------|------|
| id | VARCHAR(36) | 请求ID | "coach-001" | PRIMARY KEY |
| diagnostic_report_id | VARCHAR(36) | 诊断报告ID | "diag-001" | FOREIGN KEY → diagnostic_reports.id, NOT NULL |
| requester_id | VARCHAR(36) | 请求人 | "user-001" | FOREIGN KEY → users.id, NOT NULL |
| manager_id | VARCHAR(36) | 管理者 | "user-002" | FOREIGN KEY → users.id, NOT NULL |
| request_reason | TEXT | 请求原因 | "项目进度严重滞后" | NULLABLE |
| urgency_level | VARCHAR(20) | 紧急程度 | "high" | DEFAULT 'normal', 可选值: low/normal/high |
| status | VARCHAR(20) | 状态 | "pending" | DEFAULT 'pending', 可选值: pending/accepted/rejected/completed |
| scheduled_time | TIMESTAMP | 计划时间 | "2026-02-20 14:00:00" | NULLABLE |
| actual_time | TIMESTAMP | 实际时间 | "2026-02-20 14:30:00" | NULLABLE |
| notes | TEXT | 辅导记录 | "讨论了资源调配方案" | NULLABLE |
| created_at | TIMESTAMP | 创建时间 | "2026-02-15 15:00:00" | NOT NULL |
| updated_at | TIMESTAMP | 更新时间 | "2026-02-20 15:00:00" | NOT NULL |

**外键关系**：
- diagnostic_report_id → diagnostic_reports.id
- requester_id → users.id
- manager_id → users.id

**索引设计**：
- PRIMARY KEY (id)
- INDEX (diagnostic_report_id)
- INDEX (requester_id, status)
- INDEX (manager_id, status)

**业务约束**：
- 基于诊断报告触发辅导请求
- 管理者可接受或拒绝请求

---
