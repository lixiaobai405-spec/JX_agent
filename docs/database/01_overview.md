## 1. 概述

### 1.1 数据库总体架构

本系统基于PDCA循环理论设计，实现完整的绩效管理闭环：
- **P阶段（Plan-计划）**：智能定标引擎，AI辅助生成绩效目标
- **D阶段（Do-执行）**：智能追踪与反馈，实时监控执行进度
- **C阶段（Check-考核）**：智能评估与定级，多维度考核评价
- **A阶段（Act-行动）**：个人复盘与发展，持续改进提升

### 1.2 数据表分类（共28张表）

**组织架构模块（3表）**
- users - 用户表
- departments - 部门表
- positions - 职位表

**考核周期模块（1表）**
- periods - 考核周期表

**P阶段-智能定标（6表）**
- job_prototypes - 岗位原型表
- strategy_matrices - 策略矩阵表
- job_analyses - 岗位分析记录表
- performance_contracts - 绩效合约表
- indicator_templates - 指标模板表
- ai_generation_logs - AI生成日志表

**D阶段-执行追踪（4表）**
- checkin_tasks - 填报任务表
- checkin_records - 填报记录表
- diagnostic_reports - 诊断报告表
- coaching_requests - 辅导请求表

**C阶段-考核评估（8表）**
- goals - 绩效目标表
- indicators - 绩效指标表
- self_assessments - 自评表
- evaluation_tasks - 评价任务表
- evaluations - 评价表
- score_aggregates - 分数汇总表
- grade_rules - 等级规则表
- final_results - 最终结果表

**A阶段-复盘发展（3表）**
- review_reports - 复盘报告表
- development_plans - 发展计划表
- inheritance_suggestions - 目标继承建议表

**支持表（3表）**
- progress_records - 进度记录表
- comments - 评论表
- audit_logs - 审计日志表

### 1.3 核心业务约束

1. **权重总和约束**：同一目标下所有指标权重之和必须等于1.0
2. **阶段顺序约束**：P→D→C→A按顺序执行，A阶段结果可继承到下一周期P阶段
3. **数据隔离约束**：所有业务表包含user_id或created_by字段，确保多用户数据隔离
4. **软删除约束**：所有表支持软删除（deleted_at字段），保证数据可追溯

### 1.4 技术实现说明

- **数据库**：PostgreSQL 15+
- **主键策略**：UUID（VARCHAR(36)）
- **JSON字段**：使用JSONB类型存储复杂结构数据
- **索引策略**：在外键、查询频繁字段、唯一约束字段上建立索引
- **时间戳**：所有表包含created_at、updated_at、deleted_at（可空）

---
