## 3. 考核周期模块

### 3.1 periods（考核周期表）

**功能说明**：定义考核时间段，控制考核流程状态

**表结构**：

| 列名 | 类型 | 说明 | 示例 | 约束 |
|------|------|------|------|------|
| id | VARCHAR(36) | 周期唯一标识 | "period-2026-q1" | PRIMARY KEY |
| user_id | VARCHAR(50) | 周期所属用户ID | "user-001" | NOT NULL, INDEX, FK(users.id) |
| name | VARCHAR(100) | 周期名称 | "2026-Q1" | NOT NULL, INDEX |
| start_date | TIMESTAMP | 开始日期 | "2026-01-01 00:00:00" | NOT NULL |
| end_date | TIMESTAMP | 结束日期 | "2026-03-31 23:59:59" | NOT NULL |
| status | ENUM | 周期状态 | "open" | NOT NULL, 可选值: draft/open/closed/archived |
| description | VARCHAR(500) | 周期描述 | "2026年Q1绩效考核" | NULLABLE |
| created_at | TIMESTAMP | 创建时间 | "2025-12-15 10:00:00" | NOT NULL |
| updated_at | TIMESTAMP | 更新时间 | "2026-01-01 09:00:00" | NOT NULL |
| deleted_at | TIMESTAMP | 删除时间 | NULL | NULLABLE |

**索引设计**：
- PRIMARY KEY (id)
- INDEX (user_id)
- INDEX (name)
- INDEX (status)
- INDEX (start_date, end_date)
- INDEX (user_id, start_date, end_date)

**业务约束**：
- 每个周期对应一个用户（user_id）
- end_date 必须大于 start_date
- 状态流转：draft → open → closed → archived
- 同一用户同一时间只能有一个 open 状态的周期

---
