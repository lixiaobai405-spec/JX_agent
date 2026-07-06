# 绩效智能体后端

基于 FastAPI + LangGraph 构建的 AI 驱动绩效管理系统，实现 PDCA 全流程闭环自动化。

## 功能特性

系统按照 PDCA 管理闭环分为四个阶段：

| 阶段 | 名称 | 核心能力 |
|------|------|----------|
| **P（计划）** | 智能定标引擎 | AI 读取 JD，将岗位分类为 S/P/O/F/M 五大原型，自动生成绩效指标与合约 |
| **D（执行）** | 智能追踪与反馈 | 员工周期填报，AI 实时计算达成率与进度偏差，生成诊断报告（红绿灯看板 + 根因分析） |
| **C（考核）** | 智能评估与定级 | 多源评价（上级/360度/客户），系统自动算分，输出绩效等级（S/A/B/C）与结果确认单 |
| **A（复盘）** | 个人复盘与发展 | AI 生成个人绩效复盘报告，辅导员工制定 SMART 发展计划，并继承至下一周期 |

## 技术栈

- **后端框架**：FastAPI + SQLAlchemy（async）
- **数据库**：SQLite（aiosqlite），可替换为 PostgreSQL/MySQL
- **认证**：JWT 双 Token（python-jose + bcrypt）
- **AI 工作流**：LangGraph
- **LLM**：OpenAI 兼容接口（默认接入 DeepSeek）
- **包管理**：uv
- **运行时**：Python ≥ 3.13

## 项目结构

```
jx-agent/
├── main.py                      # 应用入口（lifespan 建表、路由注册）
│
├── core/                        # 基础设施层
│   ├── config.py                # 配置（pydantic-settings，读取 .env）
│   ├── database.py              # 异步 SQLAlchemy engine + get_db + init_db
│   ├── security.py              # JWT 创建/解码、bcrypt、密码强度校验
│   ├── dependencies.py          # FastAPI 依赖：get_current_user、require_roles
│   └── exceptions.py            # 统一异常类 + 异常处理器注册
│
├── models/                      # ORM 数据模型
│   ├── user.py                  # User（UserRole / UserStatus enum）
│   ├── organization.py          # Department、Position
│   ├── token.py                 # RefreshToken、BlacklistedAccessToken、PasswordResetToken
│   ├── period.py                # Period（考核周期）
│   ├── plan_phase.py            # JobPrototype、StrategyMatrix、PerformanceContract
│   ├── check_phase.py           # Goal、Indicator、SelfAssessment、Evaluation、FinalResult
│   ├── do_phase.py              # DataCheckin、DiagnosticReport、CoachingRequest
│   └── action_phase.py          # ReviewReport、DevelopmentPlan、InheritanceSuggestion
│
├── api/
│   └── v1/
│       ├── router.py            # 汇总所有子路由（prefix=/api/v1）
│       ├── auth/                # 认证模块（9 个端点）
│       ├── users/               # 用户管理模块（7 个端点）
│       ├── organizations/       # 组织架构模块（12 个端点）
│       ├── periods/             # 考核周期模块（8 个端点）
│       ├── plan/                # P 阶段模块（11 个端点）
│       ├── do/                  # D 阶段模块（15 个端点）
│       ├── check/               # C 阶段模块（14 个端点）
│       └── action/              # A 阶段模块（17 个端点）
│
├── graphs/                      # LangGraph PDCA 工作流
│   ├── p_graph.py               # P 阶段：岗位分类 → 指标生成
│   ├── d_graph.py               # D 阶段：达成率计算 → 反馈报告
│   ├── c_graph.py               # C 阶段：算分定级 → 结果单生成
│   └── a_graph.py               # A 阶段：复盘报告 → 发展计划辅导
│
├── utils/                       # 业务逻辑层
│   ├── calculations.py          # 绩效计算：达成率、加权得分、红绿灯状态
│   ├── llm.py                   # LLM 客户端封装（OpenAI 兼容 + 重试装饰器）
│   └── mock_llm.py              # Mock LLM 数据（本地测试用）
│
├── docs/
│   ├── blueprint.md             # 产品功能蓝图
│   ├── api/                     # API 接口文档
│   └── database/                # 数据库设计文档
│
├── frontend/                    # 前端源码（React + TypeScript + Vite）
├── .env                         # 本地环境变量（不提交）
├── .env_example                 # 环境变量模板
├── .gitignore                   # Git 忽略规则
├── .python-version              # Python 版本声明
├── pyproject.toml
├── uv.lock
├── Dockerfile
└── docker-compose.yml
```

## 快速开始

**环境要求**：Python ≥ 3.13、[uv](https://docs.astral.sh/uv/)、Node.js ≥ 18、npm ≥ 9

```bash
# 克隆项目
git clone -b backend https://gitee.com/chenghui03/jx-agent.git
cd jx-agent

# 安装后端依赖，uv 会使用项目内虚拟环境 .venv
uv sync

# 配置环境变量
cp .env_example .env
# 编辑 .env，至少填写 OPENAI_API_KEY 和 SECRET_KEY
```

后端默认使用项目内 `.venv` 环境配合 `uv` 运行：

```text
C:\Users\32159\Downloads\JX_agent\.venv
```

可用下面命令确认当前 `uv run` 使用的 Python：

```bash
uv run python -c "import sys; print(sys.executable)"
```

启动后端服务：

```bash
uv run python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

启动前端开发服务：

```bash
cd frontend
npm install
npm run dev
```

Windows 一键启动：

```powershell
.\start-dev.bat
```

服务启动后：
- API 文档：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/health`
- 前端页面：`http://localhost:5173`

## 环境变量

### AI Agent

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `OPENAI_API_KEY` | LLM API 密钥 | — |
| `OPENAI_BASE_URL` | API 接口地址 | `https://api.deepseek.com/v1` |
| `LLM_MODEL` | 使用的模型名称 | `deepseek-chat` |
| `USE_MOCK` | 是否使用 Mock 模式（无需真实 LLM） | `false` |

### 数据库 & 认证

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `DATABASE_URL` | 数据库连接串 | `sqlite+aiosqlite:///./jx-db.db` |
| `SECRET_KEY` | JWT 签名密钥（生产环境必须修改） | `change-this-secret-key-in-production` |
| `ALGORITHM` | JWT 算法 | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access Token 有效期（分钟） | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh Token 有效期（天） | `7` |
| `BCRYPT_COST` | bcrypt 加密强度 | `12` |
| `MAX_SESSIONS` | 单用户最大并发会话数 | `5` |
| `PASSWORD_RESET_TOKEN_EXPIRE_HOURS` | 密码重置 Token 有效期（小时） | `1` |

### FastAPI Server

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `HOST` | 服务监听地址 | `0.0.0.0` |
| `PORT` | 服务监听端口 | `8000` |

开启 Mock 模式后，所有 LLM 调用将使用本地预设数据，适合本地开发与测试：

```bash
USE_MOCK=true uv run python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

## 文档

- 产品功能蓝图：[docs/blueprint.md](docs/blueprint.md)
- API 接口文档：[docs/api/](docs/api/)
- 数据库设计：[docs/database/](docs/database/)
