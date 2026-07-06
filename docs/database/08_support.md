## 8. 支持表

### 8.1 progress_records（进度记录表）

**功能说明**：D阶段进度追踪记录（C阶段共享）

**表结构**：

| 列名 | 类型 | 说明 | 示例 | 约束 |
|------|------|------|------|------|
| id | VARCHAR(36) | 记录ID | "progress-001" | PRIMARY KEY |
| indicator_id | VARCHAR(36) | 对应指标 | "indicator-001" | FOREIGN KEY → indicators.id, NOT NULL |
| user_id | VARCHAR(36) | 填报人 | "user-001" | FOREIGN KEY → users.id, NOT NULL |
| date | TIMESTAMP | 记录日期 | "2026-02-15 10:00:00" | NOT NULL |
| value | FLOAT | 进度值 | 75.5 | NOT NULL |
| note | VARCHAR | 备注 | "本周完成3个任务" | NULLABLE |
| created_at | TIMESTAMP | 创建时间 | "2026-02-15 10:00:00" | NOT NULL |
| updated_at | TIMESTAMP | 更新时间 | "2026-02-15 10:00:00" | NOT NULL |
| deleted_at | TIMESTAMP | 删除时间 | NULL | NULLABLE |

**外键关系**：
- indicator_id → indicators.id
- user_id → users.id

**索引设计**：
- PRIMARY KEY (id)
- INDEX (indicator_id, date)
- INDEX (user_id)

**业务约束**：
- D阶段填报，C阶段考核时使用
- 支持历史数据查询和趋势分析

---

### 8.2 comments（评论表）

**功能说明**：通用评论系统，支持多种资源类型

**表结构**：

| 列名 | 类型 | 说明 | 示例 | 约束 |
|------|------|------|------|------|
| id | VARCHAR(36) | 评论ID | "comment-001" | PRIMARY KEY |
| related_type | VARCHAR | 资源类型 | "evaluation" | NOT NULL, 如: evaluation/final_result/goal |
| related_id | VARCHAR(36) | 资源ID | "eval-001" | NOT NULL |
| author_id | VARCHAR(36) | 作者ID | "user-001" | FOREIGN KEY → users.id, NOT NULL |
| content | VARCHAR | 评论内容 | "这个评价很客观" | NOT NULL |
| created_at | TIMESTAMP | 创建时间 | "2026-03-25 16:00:00" | NOT NULL |
| updated_at | TIMESTAMP | 更新时间 | "2026-03-25 16:00:00" | NOT NULL |
| deleted_at | TIMESTAMP | 删除时间 | NULL | NULLABLE |

**外键关系**：
- author_id → users.id

**索引设计**：
- PRIMARY KEY (id)
- INDEX (related_type, related_id)
- INDEX (author_id)

**业务约束**：
- 支持多态关联（related_type + related_id）
- 可用于评价、结果、目标等多种资源

---

### 8.3 audit_logs（审计日志表）

**功能说明**：操作审计追踪，记录所有关键操作

**表结构**：

| 列名 | 类型 | 说明 | 示例 | 约束 |
|------|------|------|------|------|
| id | VARCHAR(36) | 日志ID | "audit-001" | PRIMARY KEY |
| actor_id | VARCHAR(36) | 操作人 | "user-001" | FOREIGN KEY → users.id, NOT NULL |
| action_type | ENUM | 操作类型 | "update" | NOT NULL, 可选值: create/update/delete/confirm/adjust |
| resource_type | ENUM | 资源类型 | "goal" | NOT NULL |
| resource_id | VARCHAR(36) | 资源ID | "goal-001" | NOT NULL |
| before | JSON | 变更前数据 | {"title": "旧标题"} | NULLABLE |
| after | JSON | 变更后数据 | {"title": "新标题"} | NULLABLE |
| timestamp | TIMESTAMP | 操作时间 | "2026-03-25 16:00:00" | NOT NULL |
| created_at | TIMESTAMP | 创建时间 | "2026-03-25 16:00:00" | NOT NULL |
| updated_at | TIMESTAMP | 更新时间 | "2026-03-25 16:00:00" | NOT NULL |
| deleted_at | TIMESTAMP | 删除时间 | NULL | NULLABLE |

**外键关系**：
- actor_id → users.id

**索引设计**：
- PRIMARY KEY (id)
- INDEX (actor_id, timestamp)
- INDEX (resource_type, resource_id)
- INDEX (timestamp)

**业务约束**：
- 记录所有关键操作，不可修改
- 支持数据回溯和合规审计
- resource_type包含：user/goal/indicator/self_assessment/evaluation_task/evaluation/score_aggregate/final_result

---
