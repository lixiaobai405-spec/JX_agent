## 2. 组织架构模块

### 2.1 users（用户表）

**功能说明**：存储系统用户信息，支持多角色权限系统

**表结构**：

| 列名 | 类型 | 说明 | 示例 | 约束 |
|------|------|------|------|------|
| id | VARCHAR(36) | 用户唯一标识 | "a1b2c3d4-e5f6-7890-abcd-ef1234567890" | PRIMARY KEY |
| username | VARCHAR | 用户名 | "zhangsan" | UNIQUE, NOT NULL, INDEX |
| full_name | VARCHAR | 用户全名 | "张三" | NOT NULL |
| email | VARCHAR | 电子邮箱 | "zhangsan@company.com" | UNIQUE, NOT NULL, INDEX |
| role | ENUM | 用户角色 | "employee" | NOT NULL, 可选值: employee/manager/hr_admin/system_admin |
| department_id | VARCHAR(36) | 所属部门ID | "dept-001" | FOREIGN KEY → departments.id |
| position_id | VARCHAR(36) | 职位ID | "pos-001" | FOREIGN KEY → positions.id |
| hashed_password | VARCHAR | 加密密码 | "$2b$12$..." | NULLABLE |
| created_at | TIMESTAMP | 创建时间 | "2026-01-01 10:00:00" | NOT NULL, DEFAULT CURRENT_TIMESTAMP |
| updated_at | TIMESTAMP | 更新时间 | "2026-03-15 14:30:00" | NOT NULL, DEFAULT CURRENT_TIMESTAMP |
| deleted_at | TIMESTAMP | 删除时间（软删除） | NULL | NULLABLE |

**外键关系**：
- department_id → departments.id（所属部门）
- position_id → positions.id（职位）

**索引设计**：
- PRIMARY KEY (id)
- UNIQUE INDEX (username)
- UNIQUE INDEX (email)
- INDEX (department_id)
- INDEX (deleted_at)

**业务约束**：
- 用户名和邮箱必须唯一
- 角色决定系统权限范围
- 软删除后用户名和邮箱可被重用

---

### 2.2 departments（部门表）

**功能说明**：组织架构树形结构，支持多级部门嵌套

**表结构**：

| 列名 | 类型 | 说明 | 示例 | 约束 |
|------|------|------|------|------|
| id | VARCHAR(36) | 部门唯一标识 | "dept-001" | PRIMARY KEY |
| name | VARCHAR | 部门名称 | "技术研发部" | NOT NULL, INDEX |
| code | VARCHAR | 部门编码 | "TECH-RD" | UNIQUE, NOT NULL |
| parent_id | VARCHAR(36) | 父部门ID | "dept-000" | FOREIGN KEY → departments.id, NULLABLE |
| manager_id | VARCHAR(36) | 部门负责人ID | "user-001" | FOREIGN KEY → users.id, NULLABLE |
| description | TEXT | 部门描述 | "负责公司核心产品研发" | NULLABLE |
| level | INT | 部门层级 | 2 | NOT NULL, DEFAULT 1 |
| path | VARCHAR | 部门路径 | "/dept-000/dept-001" | NOT NULL |
| order_index | INT | 排序序号 | 10 | NOT NULL, DEFAULT 0 |
| is_active | BOOLEAN | 是否启用 | true | NOT NULL, DEFAULT true |
| created_at | TIMESTAMP | 创建时间 | "2026-01-01 10:00:00" | NOT NULL |
| updated_at | TIMESTAMP | 更新时间 | "2026-03-15 14:30:00" | NOT NULL |
| deleted_at | TIMESTAMP | 删除时间 | NULL | NULLABLE |


**外键关系**：
- parent_id → departments.id（父部门，自关联）
- manager_id → users.id（部门负责人）

**索引设计**：
- PRIMARY KEY (id)
- UNIQUE INDEX (code)
- INDEX (name)
- INDEX (parent_id)
- INDEX (path)

**业务约束**：
- 根部门parent_id为NULL
- path字段记录完整层级路径，便于查询子树
- 删除部门时需检查是否有子部门和员工

---

### 2.3 positions（职位表）

**功能说明**：职位信息管理，关联部门和岗位族

**表结构**：

| 列名 | 类型 | 说明 | 示例 | 约束 |
|------|------|------|------|------|
| id | VARCHAR(36) | 职位唯一标识 | "pos-001" | PRIMARY KEY |
| title | VARCHAR | 职位名称 | "高级Java工程师" | NOT NULL, INDEX |
| code | VARCHAR | 职位编码 | "TECH-JAVA-SR" | UNIQUE, NOT NULL |
| department_id | VARCHAR(36) | 所属部门ID | "dept-001" | FOREIGN KEY → departments.id, NULLABLE |
| job_family | VARCHAR | 岗位族 | "技术研发" | NULLABLE |
| job_level | VARCHAR | 职级 | "P7" | NULLABLE |
| description | TEXT | 职位描述 | "负责核心业务系统开发" | NULLABLE |
| requirements | TEXT | 任职要求 | "5年以上Java开发经验" | NULLABLE |
| is_active | BOOLEAN | 是否启用 | true | NOT NULL, DEFAULT true |
| created_at | TIMESTAMP | 创建时间 | "2026-01-01 10:00:00" | NOT NULL |
| updated_at | TIMESTAMP | 更新时间 | "2026-03-15 14:30:00" | NOT NULL |
| deleted_at | TIMESTAMP | 删除时间 | NULL | NULLABLE |

**外键关系**：
- department_id → departments.id（所属部门）

**索引设计**：
- PRIMARY KEY (id)
- UNIQUE INDEX (code)
- INDEX (title)
- INDEX (department_id)

**业务约束**：
- 职位编码全局唯一
- 职位可跨部门复用（department_id可为空）
- job_family和job_level用于P阶段岗位分类

---
