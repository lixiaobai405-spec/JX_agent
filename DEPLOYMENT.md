# 绩效智能体（jx-agent）部署指南

## 环境要求

- Docker >= 24.0
- Docker Compose >= 2.0
- DeepSeek API Key（或兼容 OpenAI 接口的 LLM 服务）
- 本地演示/开发：Python >= 3.13、uv、Node.js、npm

---

## 本地演示/开发运行

后端默认使用项目内 `.venv` 环境配合 `uv` 运行：

```text
C:\Users\32159\Downloads\JX_agent\.venv
```

后端：

```bash
cp .env_example .env
uv sync
uv run python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

如需确认 `uv run` 使用的 Python 路径：

```bash
uv run python -c "import sys; print(sys.executable)"
```

前端：

```bash
cd frontend
npm install
npm run dev
```

访问地址：

- 后端健康检查：`http://localhost:8000/health`
- 后端 API 文档：`http://localhost:8000/docs`
- 前端页面：`http://localhost:5173`

课堂演示如果没有可用 API Key，可在 `.env` 中设置 `USE_MOCK=true`，后端仍使用同一条启动命令。

---

## Docker 快速部署

**第一步：解压交付包**

```bash
tar -xzf jx-agent-*.tar.gz
cd jx-agent
```

**第二步：配置环境变量**

```bash
cp .env_example .env
```

用文本编辑器打开 `.env`，至少填写以下两项：

```
OPENAI_API_KEY=your_api_key_here
SECRET_KEY=your_random_secret_key_here
DATABASE_URL=sqlite+aiosqlite:///./data/jx-db.db
```

**第三步：构建镜像**

```bash
docker compose build
```

**第四步：启动服务**

```bash
docker compose up -d
```

**第五步：访问系统**

浏览器打开 `http://服务器IP`，使用初始账号登录。

---

## 环境变量说明

| 变量 | 必填 | 默认值 | 说明 |
|------|:----:|--------|------|
| `OPENAI_API_KEY` | 是 | — | DeepSeek 或 OpenAI API Key |
| `SECRET_KEY` | 是 | — | JWT 签名密钥，请设置为随机字符串 |
| `DATABASE_URL` | 是 | sqlite（见上） | 数据库连接串，需指向 `./data/` 目录 |
| `OPENAI_BASE_URL` | 否 | `https://api.deepseek.com/v1` | LLM 接口地址，可替换为其他兼容接口 |
| `LLM_MODEL` | 否 | `deepseek-chat` | 使用的模型名称 |
| `USE_MOCK` | 否 | `false` | 设为 `true` 时使用 Mock LLM，无需 API Key |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 否 | `15` | 访问令牌有效期（分钟） |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 否 | `7` | 刷新令牌有效期（天） |

---

## 数据持久化

SQLite 数据库文件存储在宿主机 `./data/` 目录（通过 Docker volume 挂载）。

备份数据库：

```bash
cp ./data/jx-db.db ./backup/jx-db-$(date +%Y%m%d).db
```

---

## 服务管理

```bash
# 查看运行状态
docker compose ps

# 查看日志
docker compose logs -f backend

# 停止服务
docker compose down

# 升级（重新构建并重启）
docker compose up -d --build
```

---

## 常见问题

**端口 80 被占用**

修改 `docker-compose.yml` 中 `frontend` 服务的端口映射：

```yaml
ports:
  - "8080:80"   # 改为其他端口
```

**无 API Key 时验证功能**

在 `.env` 中设置 `USE_MOCK=true`，系统将使用内置 Mock 数据响应 AI 请求，无需真实 API Key。

**API Key 无效或请求失败**

检查 `OPENAI_BASE_URL` 与 `OPENAI_API_KEY` 是否匹配。使用 DeepSeek 时 Base URL 应为 `https://api.deepseek.com/v1`。

---

## 交付文件清单

```
jx-agent/
├── main.py                  # 后端入口
├── core/                    # 基础设施（配置、数据库、认证）
├── models/                  # 数据模型
├── api/                     # API 路由
├── graphs/                  # AI 工作流（PDCA 四阶段）
├── utils/                   # 业务逻辑
├── frontend/                # 前端源码（React + TypeScript）
├── docs/                    # API 文档、数据库设计文档
├── pyproject.toml           # Python 依赖
├── uv.lock                  # 依赖锁定文件
├── .python-version          # Python 版本声明
├── .gitignore               # Git 忽略规则
├── .env_example             # 环境变量模板
├── Dockerfile               # 后端镜像
├── docker-compose.yml       # 服务编排
├── README.md
└── CHANGELOG.md
```
