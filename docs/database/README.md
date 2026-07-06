# 绩效管理系统数据库设计文档

本系统基于PDCA循环理论设计，实现完整的绩效管理闭环，涵盖智能定标、执行追踪、考核评估、复盘发展四个阶段，共 **28张数据表**。

## 数据表分类

| 模块 | 表数 | 主要表 |
|------|------|--------|
| 组织架构 | 3 | users, departments, positions |
| 考核周期 | 1 | periods |
| P阶段-智能定标 | 6 | job_prototypes, strategy_matrices, job_analyses, performance_contracts, indicator_templates, ai_generation_logs |
| D阶段-执行追踪 | 4 | checkin_tasks, checkin_records, diagnostic_reports, coaching_requests |
| C阶段-考核评估 | 8 | goals, indicators, self_assessments, evaluation_tasks, evaluations, score_aggregates, grade_rules, final_results |
| A阶段-复盘发展 | 3 | review_reports, development_plans, inheritance_suggestions |
| 支持表 | 3 | progress_records, comments, audit_logs |

## 文档目录

| 文件 | 内容 |
|------|------|
| [01_overview.md](01_overview.md) | 第1章：概述（总体架构、28张表分类、核心约束、技术说明） |
| [02_organization.md](02_organization.md) | 第2章：组织架构模块（users / departments / positions） |
| [03_periods.md](03_periods.md) | 第3章：考核周期模块（periods） |
| [04_phase_p.md](04_phase_p.md) | 第4章：P阶段-智能定标（6张表） |
| [05_phase_d.md](05_phase_d.md) | 第5章：D阶段-执行追踪（4张表） |
| [06_phase_c.md](06_phase_c.md) | 第6章：C阶段-考核评估（8张表） |
| [07_phase_a.md](07_phase_a.md) | 第7章：A阶段-复盘发展（3张表） |
| [08_support.md](08_support.md) | 第8章：支持表（3张表） |
| [09_dependencies.md](09_dependencies.md) | 第9章：阶段依赖关系（流转图、循环图） |
| [10_appendix.md](10_appendix.md) | 附录：数据库设计原则 |

