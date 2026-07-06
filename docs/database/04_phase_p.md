## 4. P阶段-智能定标

### 4.1 job_prototypes（岗位原型表）

**功能说明**：定义5种岗位原型（铁军型/项目型/运营型/职能型/管理型）

**表结构**：

| 列名 | 类型 | 说明 | 示例 | 约束 |
|------|------|------|------|------|
| id | VARCHAR(36) | 原型唯一标识 | "proto-s" | PRIMARY KEY |
| code | CHAR(1) | 原型编码 | "S" | UNIQUE, NOT NULL, 可选值: S/P/O/F/M |
| name | VARCHAR(50) | 原型名称 | "铁军型" | NOT NULL |
| description | TEXT | 原型描述 | "业绩导向，结果可量化" | NULLABLE |
| quantifiability_min | INT | 可量化度最小值 | 8 | DEFAULT 0 |
| quantifiability_max | INT | 可量化度最大值 | 10 | DEFAULT 10 |
| output_cycle_min | INT | 产出周期最小值 | 0 | DEFAULT 0 |
| output_cycle_max | INT | 产出周期最大值 | 3 | DEFAULT 10 |
| work_nature_min | INT | 工作性质最小值 | 8 | DEFAULT 0 |
| work_nature_max | INT | 工作性质最大值 | 10 | DEFAULT 10 |
| indicator_count_min | INT | 推荐指标最少数量 | 3 | NOT NULL |
| indicator_count_max | INT | 推荐指标最多数量 | 5 | NOT NULL |
| quantitative_ratio_min | FLOAT | 定量指标最低比例 | 0.80 | NOT NULL, 范围: 0-1 |
| quantitative_ratio_max | FLOAT | 定量指标最高比例 | 1.00 | NOT NULL, 范围: 0-1 |
| primary_target_setting | VARCHAR(50) | 主要目标设定逻辑 | "自上而下" | NOT NULL |
| created_at | TIMESTAMP | 创建时间 | "2026-01-01 10:00:00" | NOT NULL |
| updated_at | TIMESTAMP | 更新时间 | "2026-01-01 10:00:00" | NOT NULL |



**索引设计**：
- PRIMARY KEY (id)
- UNIQUE INDEX (code)

**业务约束**：
- 5种原型固定：S(铁军型)、P(项目型)、O(运营型)、F(职能型)、M(管理型)
- 三维度评分范围用于岗位分类匹配
- 各原型验证规则参考值：

| 原型 | indicator_count_min | indicator_count_max | quantitative_ratio_min | quantitative_ratio_max | primary_target_setting |
|------|---------------------|---------------------|------------------------|------------------------|------------------------|
| S | 3 | 5 | 0.80 | 1.00 | 自上而下 |
| P | 5 | 7 | 0.40 | 0.60 | 混合（自我设定为辅） |
| O | 4 | 5 | 0.90 | 1.00 | 历史推导 |
| F | 5 | 7 | 0.50 | 0.65 | 混合（自我设定为辅） |
| M | 5 | 6 | 0.50 | 0.70 | 自上而下 |

- `quantitative_ratio_min` 至 `quantitative_ratio_max` 之间为定量指标允许比例范围，其余为定性指标允许范围
- AI生成合约后可用 `indicator_count_min/max` 和 `quantitative_ratio_min/max` 进行自动化合规校验

---

### 4.2 strategy_matrices（策略矩阵表）

**功能说明**：存储每种岗位原型的8维度策略配置

**表结构**：

| 列名 | 类型 | 说明 | 示例 | 约束 |
|------|------|------|------|------|
| id | VARCHAR(36) | 策略唯一标识 | "strategy-001" | PRIMARY KEY |
| job_prototype_code | CHAR(1) | 岗位原型编码 | "S" | FOREIGN KEY → job_prototypes.code, NOT NULL |
| dimension | VARCHAR(50) | 策略维度 | "指标来源" | NOT NULL |
| configuration | JSON | 配置内容 | {"sources": ["业绩结果", "关键任务"]} | NOT NULL |
| priority | INT | 优先级 | 1 | DEFAULT 0 |
| created_at | TIMESTAMP | 创建时间 | "2026-01-01 10:00:00" | NOT NULL |
| updated_at | TIMESTAMP | 更新时间 | "2026-01-01 10:00:00" | NOT NULL |

**外键关系**：
- job_prototype_code → job_prototypes.code

**索引设计**：
- PRIMARY KEY (id)
- INDEX (job_prototype_code, dimension)

**业务约束**：
- 8个维度：指标来源/评价人/指标属性/指标维度/目标值设定/考核周期/辅导周期/结果应用
- 每个原型每个维度只有一条配置记录
- 各维度合法配置值枚举（来自5种原型实际数据）：

| 维度 | 合法配置值 |
|------|-----------|
| 指标来源 | 业绩结果KPI、关键任务、关键行为、项目里程碑、内部客户服务、战略目标分解 |
| 评价人 | 直属上级、360度内部客户、外部标杆机构、系统数据、质监部门、CEO/董事会 |
| 指标属性 | 定量为主（>80%）、定量定性混合（40-60%）、高度量化（>90%）、定性为辅 |
| 指标维度 | 业绩产出、项目过程、运营质量、服务能力、管理赋能、合规安全 |
| 目标值设定 | 自上而下、自我设定、历史推导、外部标杆、红线设定（可多选） |
| 考核周期 | monthly、quarterly、semi_annual（月度/季度/半年度） |
| 辅导周期 | weekly、biweekly、monthly（周/双周/月） |
| 结果应用 | 绩效奖金系数、职级晋升提名、荣誉称号、项目专项奖金、长期股权激励 |

---

### 4.3 job_analyses（岗位分析记录表）

**功能说明**：记录AI对岗位JD的分析结果

**表结构**：

| 列名 | 类型 | 说明 | 示例 | 约束 |
|------|------|------|------|------|
| id | VARCHAR(36) | 分析记录ID | "analysis-001" | PRIMARY KEY |
| user_id | VARCHAR(36) | 用户ID | "user-001" | FOREIGN KEY → users.id, NOT NULL |
| jd_text | TEXT | 岗位描述文本 | "负责Java后端开发..." | NOT NULL |
| job_prototype_code | CHAR(1) | 匹配的原型 | "P" | FOREIGN KEY → job_prototypes.code, NULLABLE |
| quantifiability_score | INT | 可量化度评分 | 6 | NULLABLE, 范围: 0-10 |
| output_cycle_score | INT | 产出周期评分 | 7 | NULLABLE, 范围: 0-10 |
| work_nature_score | INT | 工作性质评分 | 5 | NULLABLE, 范围: 0-10 |
| features | JSON | 提取的岗位特征 | {"keywords": ["开发", "项目"]} | NULLABLE |
| confidence | FLOAT | 匹配置信度 | 0.85 | NULLABLE, 范围: 0-1 |
| analysis_result | JSON | 完整分析结果 | {...} | NULLABLE |
| created_at | TIMESTAMP | 创建时间 | "2026-01-15 10:00:00" | NOT NULL |

**外键关系**：
- user_id → users.id
- job_prototype_code → job_prototypes.code

**索引设计**：
- PRIMARY KEY (id)
- INDEX (user_id)
- INDEX (job_prototype_code)

**业务约束**：
- 每次分析生成一条记录
- 三维度评分用于匹配岗位原型

---

### 4.4 performance_contracts（绩效合约表）

**功能说明**：存储AI生成的完整绩效合约

**表结构**：

| 列名 | 类型 | 说明 | 示例 | 约束 |
|------|------|------|------|------|
| id | VARCHAR(36) | 合约ID | "contract-001" | PRIMARY KEY |
| goal_id | VARCHAR(100) | 关联目标ID（D阶段填充） | "goal-001" | NULLABLE, UNIQUE |
| job_prototype_code | CHAR(1) | 岗位原型 | "S" | FOREIGN KEY → job_prototypes.code, NOT NULL |
| strategy_config | JSON | 8维度策略配置 | {"指标来源": [...], ...} | NOT NULL |
| contract_data | JSON | 完整合约数据 | {"indicators": [...]} | NOT NULL |
| ai_generated | BOOLEAN | 是否AI生成 | true | DEFAULT false |
| generation_log | TEXT | 生成日志 | "使用DeepSeek模型生成" | NULLABLE |
| confirmed_at | TIMESTAMP | 确认时间 | "2026-01-20 15:00:00" | NULLABLE |
| confirmed_by | VARCHAR(36) | 确认人ID | "user-001" | FOREIGN KEY → users.id, NULLABLE |
| created_at | TIMESTAMP | 创建时间 | "2026-01-20 10:00:00" | NOT NULL |
| updated_at | TIMESTAMP | 更新时间 | "2026-01-20 15:00:00" | NOT NULL |

**外键关系**：
- job_prototype_code → job_prototypes.code
- confirmed_by → users.id

**索引设计**：
- PRIMARY KEY (id)
- UNIQUE INDEX (goal_id)
- INDEX (job_prototype_code)

**业务约束**：
- goal_id 在 P 阶段为空，D 阶段生成 goal 时填充
- 支持同一用户同一周期多次生成合约（用于反馈调整）
- 确认后才能进入 D 阶段
- `contract_data` 规范结构（JSON Schema）：

```json
{
  "basic_info": {
    "position_title": "华东KA销售经理",
    "assessment_cycle": "monthly",
    "prototype_code": "S"
  },
  "indicators": [
    {
      "name": "区域净销售额",
      "definition": "华东区便利系统当月实际开票销售额",
      "scoring_standard": "(实际/目标)*100%",
      "target_setting_logic": "top_down",
      "target_value": "800万元",
      "target_value_numeric": 8000000,
      "target_value_unit": "元",
      "weight": 0.45,
      "indicator_attribute": "quantitative",
      "is_special": "none"
    },
    {
      "name": "乱价/串货行为",
      "definition": "擅自破价或跨区违规供货",
      "scoring_standard": "发生1起扣20分",
      "target_setting_logic": "redline",
      "target_value": "0起",
      "weight": null,
      "indicator_attribute": "qualitative",
      "is_special": "deduction",
      "deduction_rule": "每起扣20分"
    }
  ],
  "management_agreements": {
    "coaching_frequency": "weekly",
    "coaching_description": "每周五下午17:00提交《周销售复盘表》；次月5日前完成月度面谈",
    "result_applications": ["月度绩效奖金系数", "职级晋升提名（连续3月S级）"]
  },
  "validation": {
    "indicator_count": 5,
    "quantitative_ratio": 0.80,
    "meets_prototype_rules": true
  }
}
```

- `indicators[].weight` 对非扣分项之和必须等于 1.0
- `is_special=deduction` 的指标 `weight` 字段为 null，不参与权重汇总
- `is_special=veto` 的指标触发后，final_results 中等级强制降为最低

---

### 4.5 indicator_templates（指标模板表）

**功能说明**：存储不同岗位原型的指标模板

**表结构**：

| 列名 | 类型 | 说明 | 示例 | 约束 |
|------|------|------|------|------|
| id | VARCHAR(36) | 模板ID | "template-001" | PRIMARY KEY |
| job_prototype_code | CHAR(1) | 岗位原型 | "S" | FOREIGN KEY → job_prototypes.code, NOT NULL |
| indicator_type | VARCHAR(50) | 指标类型 | "关键业绩结果" | NOT NULL |
| source_type | VARCHAR(50) | 来源类型 | "组织目标分解" | NOT NULL |
| name_template | TEXT | 名称模板 | "销售额达成率" | NOT NULL |
| definition_template | TEXT | 定义模板 | "实际销售额/目标销售额" | NULLABLE |
| evaluation_criteria_template | TEXT | 评价标准模板 | ">=100%为优秀" | NULLABLE |
| weight_range_min | FLOAT | 权重最小值 | 0.3 | DEFAULT 0 |
| weight_range_max | FLOAT | 权重最大值 | 0.5 | DEFAULT 1 |
| target_setting_logic | ENUM | 目标设定逻辑 | "top_down" | NOT NULL, 可选值: top_down/self_set/historical/benchmark/redline |
| indicator_attribute | ENUM | 定量/定性属性 | "quantitative" | NOT NULL, 可选值: quantitative/qualitative |
| is_special | ENUM | 特殊处理标记 | "none" | DEFAULT 'none', 可选值: none/veto/deduction |
| created_at | TIMESTAMP | 创建时间 | "2026-01-01 10:00:00" | NOT NULL |
| updated_at | TIMESTAMP | 更新时间 | "2026-01-01 10:00:00" | NOT NULL |

**外键关系**：
- job_prototype_code → job_prototypes.code

**索引设计**：
- PRIMARY KEY (id)
- INDEX (job_prototype_code, indicator_type)

**业务约束**：
- 模板用于AI生成具体指标
- 权重范围指导指标权重分配
- `target_setting_logic` 枚举说明：
  - `top_down`：自上而下（组织战略/年度目标分解）
  - `self_set`：自我设定（员工自主规划/上报申请）
  - `historical`：历史推导（过去N月均值±提升比例）
  - `benchmark`：外部标杆（行业Top企业/竞品数据）
  - `redline`：红线设定（合规/安全事故，0容忍）
- `is_special` 枚举说明：
  - `veto`：一票否决，发生即整体不合格（如P类食品安全、O类安全生产、M类廉洁）
  - `deduction`：扣分项，按次扣分但不触发一票否决（如S类乱价串货、F类隐私泄露）

---

### 4.6 ai_generation_logs（AI生成日志表）

**功能说明**：记录所有AI生成操作的日志

**表结构**：

| 列名 | 类型 | 说明 | 示例 | 约束 |
|------|------|------|------|------|
| id | VARCHAR(36) | 日志ID | "log-001" | PRIMARY KEY |
| user_id | VARCHAR(36) | 用户ID | "user-001" | FOREIGN KEY → users.id, NOT NULL |
| generated_by | VARCHAR(36) | 操作人ID | "user-002" | FOREIGN KEY → users.id, NOT NULL |
| job_type | VARCHAR(10) | 任务类型 | "contract" | NULLABLE |
| input_text | TEXT | 输入文本 | "岗位描述..." | NULLABLE |
| output_data | JSON | 输出数据 | {"indicators": [...]} | NULLABLE |
| model_used | VARCHAR(50) | 使用模型 | "deepseek-chat" | NULLABLE |
| tokens_used | INT | 消耗token数 | 1500 | NULLABLE |
| generation_time_ms | INT | 生成耗时(毫秒) | 3200 | NULLABLE |
| success | BOOLEAN | 是否成功 | true | DEFAULT true |
| error_message | TEXT | 错误信息 | NULL | NULLABLE |
| job_analysis_id | VARCHAR(36) | 触发生成的岗位分析记录ID | "analysis-001" | FOREIGN KEY → job_analyses.id, NULLABLE |
| created_at | TIMESTAMP | 创建时间 | "2026-01-20 10:00:00" | NOT NULL |

**外键关系**：
- user_id → users.id
- generated_by → users.id
- job_analysis_id → job_analyses.id

**索引设计**：
- PRIMARY KEY (id)
- INDEX (user_id)
- INDEX (created_at)
- INDEX (job_analysis_id)

**业务约束**：
- 记录所有AI调用，用于审计和优化
- 失败记录保留error_message

---
