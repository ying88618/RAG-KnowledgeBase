# 智能知识库问答系统（Spring Boot + Python 知识库服务）

一个前后端分离的全栈项目，由 **Java 后端（Spring Boot）** 与 **Python 知识库 / 智能体服务** 两部分组成：

- **Java 端**：提供用户、文章、分类、文件上传、OSS、JWT 鉴权等 REST 接口，并通过 HTTP 调用 Python 端的智能体（Agent）能力。
- **Python 端**：基于 FastAPI + LangGraph + pgvector 的知识库检索与对话 Agent，并集成 Tavily 联网搜索工具，负责文档向量化入库、智能问答与实时信息检索。Agent 以**全局单例**形式构建（`create_agent` 仅执行一次），请求级别的「知识库集合名 / 相似度阈值」通过 `contextvars` 注入，由模型自主决定是否调用 `knowledge_base_search`（本地知识库）或 `web_search`（Tavily 联网）工具。


---

## 1. 整体架构

```
┌──────────────┐      HTTP (8071 → 8000)      ┌──────────────────┐
│  Spring Boot │ ───────────────────────────► │  Python FastAPI  │
│  (Java 21)   │   agent.base-url            │  (uvicorn :8000) │
│  :8071       │                              │  LangGraph Agent │
└──────┬───────┘                              └────────┬─────────┘
       │                                               │
       │                          ┌────────────────────┼───────────────────┐
       ▼                          ▼                    ▼                   ▼
┌────────────┐            ┌──────────────┐     ┌──────────────┐    ┌──────────────┐
│ MySQL      │            │ PostgreSQL   │     │ Redis (Java) │    │ Redis (Py)   │
│ big_event  │            │ + pgvector   │     │ 登录态/JWT   │    │ 聊天历史 TTL │
│ 用户/业务  │            │ 向量库       │     │              │    │ 1800s        │
└────────────┘            └──────────────┘     └──────────────┘    └──────────────┘
```

### 关键技术栈
| 模块 | 技术 |
|------|------|
| Java | Spring Boot 3.x、Java 21、Maven、MyBatis-Plus 3.5.9 |
| Python | FastAPI、uvicorn、LangGraph、LangChain、pgvector |
| 数据库 | MySQL（`big_event`）、PostgreSQL + pgvector（`KnowledgeBase`） |
| 缓存 | Redis（Java 端登录态/JWT；Python 端聊天历史） |
| 对象存储 | 阿里云 OSS（oss-cn-shenzhen） |
| 大模型 | 硅基流动 API 代理（OpenAI 兼容）：Qwen/Qwen3.5-27B，嵌入 BAAI/bge-large-zh-v1.5 |

### 端口约定
- Java 后端：`8071`
- Python 知识库服务：`8000`
- MySQL：`3306`
- PostgreSQL：`5432`
- Redis：`6379`

---

## 2. 环境依赖

- **JDK 21**
- **Maven 3.8+**
- **Python 3.10+**
- **MySQL 8.x**（库名 `big_event`）
- **PostgreSQL 15+**，并安装 **pgvector** 扩展（库名 `KnowledgeBase`）
- **Redis 6+**

---

## 3. 配置与环境变量

> ⚠️ 本项目所有敏感配置均通过**环境变量注入**，仓库内不含任何明文密码。
> 启动前请务必设置以下**必填**环境变量（MySQL 密码、JWT 密钥、OSS 凭据），否则 Java 端会因无法解析占位符而启动失败。Redis 运行在本地且未设密码，无需配置密码变量。

### 3.1 Java 端（`src/main/resources/application.yml` + `application.properties`）

| 环境变量 | 用途 | 是否必填 |
|----------|------|----------|
| `DB_USERNAME` | MySQL 用户名（默认 `root`） | 否（有默认值） |
| `DB_URL` | MySQL JDBC 连接串（默认本地 `big_event`） | 否（有默认值） |
| `DB_PASSWORD` | MySQL 密码 | **必填** |
| `REDIS_HOST` | Redis 主机（默认 `localhost`） | 否 |
| `REDIS_PORT` | Redis 端口（默认 `6379`） | 否 |
| `LOG_PATH` | 日志文件输出路径 | 否（默认 `springboot-01-start/logs/springboot.log`） |
| `JWT_KEY` | JWT 签名密钥 | **必填** |
| `OSS_ACCESS_KEY_ID` | 阿里云 OSS AccessKeyId | **必填** |
| `OSS_ACCESS_KEY_SECRET` | 阿里云 OSS AccessKeySecret | **必填** |

> 说明：Java 端 `application.properties` 中的 OSS endpoint、bucket、region 及 Agent 地址（`http://127.0.0.1:8000/`）已写死在文件中，如需变更可直接改文件或补充对应占位符。

### 3.2 Python 端（`KnowledgeBase/.env`）

复制模板后填写（`.env` 已被 `.gitignore` 忽略，不会入库）：

```bash
cp KnowledgeBase/.env.example KnowledgeBase/.env
```

| 变量 | 说明 | 示例 |
|------|------|------|
| `OPENAI_API_KEY` | 硅基流动 API Key | `your_key_here` |
| `OPENAI_BASE_URL` | 模型代理地址 | `https://api.siliconflow.cn/v1` |
| `MODEL_NAME` | 对话模型 | `Qwen/Qwen3.5-27B` |
| `EMBEDDING_MODEL` | 嵌入模型 | `BAAI/bge-large-zh-v1.5` |
| `DATABASE_URL` | PostgreSQL 连接串（含 pgvector） | `postgresql+psycopg://user:pass@localhost:5432/KnowledgeBase` |
| `REDIS_URL` | Redis 连接串 | `redis://localhost:6379/0` |
| `CHAT_HISTORY_TTL` | 聊天历史过期时间（秒） | `1800` |
| `TAVILY_API_KEY` | Tavily 联网搜索 Key（用于 `web_search` 工具） | `your_key_here` |

> 注意：本项目 Redis 运行在本地（`localhost:6379`）且**未设置密码**。Java 端 `application.yml` 中的 Redis `password` 已注释，Python 端的 `REDIS_URL` 使用无密码格式 `redis://localhost:6379/0`，两端均按无密码连接。如需对外暴露 Redis 或启用密码，请同时：① Java 端取消注释 `password: ${REDIS_PASSWORD}` 并配置该环境变量；② Python 端将 `REDIS_URL` 改为 `redis://:password@localhost:6379/0`，确保两端密码一致。

---

## 4. 启动步骤

> 推荐启动顺序：**基础设施 → Python 入库 → Python 服务 → Java 服务**。

### 4.1 启动基础设施
确保 MySQL、PostgreSQL（已装 pgvector）、Redis 均已启动，并创建好对应数据库：
- MySQL 建库 `big_event`
- PostgreSQL 建库 `KnowledgeBase`，并执行 `CREATE EXTENSION IF NOT EXISTS vector;`

### 4.2 启动 Python 知识库服务（含入库接口）

```bash
cd KnowledgeBase

# 安装依赖（建议使用虚拟环境）
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env             # 然后编辑 .env 填入真实值

# 启动服务（main.py 已聚合 ingest 与 chat 两个子应用，统一监听 8000）
# main.py 内部 include_router 挂载了：
#   - POST /documents/ingest   （文档向量化入库，对应 ingest.py）
#   - chat 相关接口            （对应 chat.py）
uvicorn KnowledgeBase.main:app --host 0.0.0.0 --port 8000
# 或用包内 __main__ 入口：
# python -m KnowledgeBase.main
```

### 4.2.1 触发文档入库
入库不是命令行脚本，而是调用已启动服务的 HTTP 接口。服务起来后，向 `POST http://127.0.0.1:8000/documents/ingest` 发送 `IngestRequest`（字段见 `KnowledgeBase/schemas.py`）即可触发向量化入库，例如：

```bash
curl -X POST http://127.0.0.1:8000/documents/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "doc_id": 1,
    "file_url": "https://your-oss-bucket/doc.pdf",
    "file_name": "doc.pdf",
    "file_type": "pdf",
    "collection_name": "KnowledgeBase"
  }'
```
> `IngestRequest` 字段：`doc_id`(int)、`file_url`(str)、`file_name`(str)、`file_type`(str)、`collection_name`(str)，详见 `KnowledgeBase/schemas.py`。

### 4.3 启动 Java 后端

先设置环境变量（以 PowerShell 为例，Linux/macOS 用 `export`）：

```powershell
$env:DB_PASSWORD="你的MySQL密码"
$env:JWT_KEY="一段足够长的随机字符串"
$env:OSS_ACCESS_KEY_ID="你的OSS_ID"
$env:OSS_ACCESS_KEY_SECRET="你的OSS_SECRET"
```

然后使用 Maven 启动：

```bash
cd e:/IdeaProjects/springboot
./mvnw spring-boot:run          # 或 Windows: mvnw.cmd spring-boot:run
```

启动成功后，Java 后端监听 `http://localhost:8071`，并通过 `agent.base-url` 调用 Python 端的 `http://127.0.0.1:8000/`。

---

## 5. 关键对接点说明

1. **跨端调用**：Java 端 `AgentController` / `AgentService` 通过 `application.properties` 中的 `agent.base-url=http://127.0.0.1:8000/` 调用 Python 端。Python 端未启动时，相关接口会超时（`agent.timeout=5000`，`agent.read-timeout=60000`）。
2. **数据库分离**：业务数据（用户/文章/分类等）在 MySQL，知识库向量与文档在 PostgreSQL + pgvector，两者互不干扰。
3. **Redis 分离**：Java 端用 Redis 维护登录态 / JWT 校验；Python 端用 Redis 缓存聊天历史（TTL 1800s）。两端均连接本地 `localhost:6379`，且当前 Redis **未启用密码**，按无密码方式连接。
4. **大模型代理**：Python 端通过硅基流动（`api.siliconflow.cn`）的 OpenAI 兼容接口访问 Qwen 系列模型，并非直连 OpenAI。

---

## 5.1 Agent 工具调用与请求上下文

Python 端的对话 Agent 由 LangGraph `create_agent` 构建，注册了以下两个工具，由模型**自主决定**是否调用、调用哪个（不再做强制检索）：

| 工具 | 作用 | 触发场景 |
|------|------|----------|
| `knowledge_base_search` | 调用 `retriever.retrieve` 在 pgvector 中做向量召回（Top-K=4，相似度阈值默认 0.5） | 用户问题涉及私人 / 本地知识库内容 |
| `web_search` | 封装 Tavily 联网搜索（Top-5，`search_depth=basic`） | 需要实时 / 互联网信息，或知识库无相关内容 |

**全局单例 + 请求上下文**：`graph.py` 在模块加载时即执行一次 `create_agent`，得到全局唯一的 `AGENT`；`chat.py` 通过 `get_agent()` 获取该实例，并调用 `set_request_context(collection_name, score_threshold=0.5)` 把「本次请求命中的知识库集合」与「相似度阈值」写入 `contextvars`。两个 `@tool` 函数在被模型调用时再读取 `contextvars` 中的集合名与阈值，从而避免在每次请求都重建 Agent 实例。

请求体（`ChatRequest`）字段：`session_id`(str)、`user_id`(int)、`question`(str)、`collection_name`(str)。Java 端透传即可，无需解析工具返回的来源。

---

## 6. 常见问题

- **Java 启动报 `Could not resolve placeholder 'DB_PASSWORD'`**：未设置环境变量。请按 4.3 设置 `DB_PASSWORD` 等必填变量。
- **Python 端调用模型报错 401**：检查 `.env` 中 `OPENAI_API_KEY` 是否为真实硅基流动 Key。
- **pgvector 报错 `relation "..." does not exist` / 无 vector 扩展**：确认已在 `KnowledgeBase` 库执行 `CREATE EXTENSION vector;`。
- **Agent 接口超时**：确认 Python 服务已在 8000 端口启动，且 `agent.base-url` 可达。

---

## 7. 目录结构（简要）

```
springboot/
├── src/main/java/com/example/springboot/   # Spring Boot 后端
│   ├── Controller/                         # REST 控制器
│   ├── Service/impl/                        # 业务实现
│   ├── pojo/                               # 实体 / 请求对象（含 ChatRequest）
│   └── resources/
│       ├── application.yml                 # 主配置（已纳入版本管理，无明文密码）
│       └── application.properties          # OSS / Agent / JWT 配置
├── KnowledgeBase/                          # Python 知识库 / 智能体服务
│   ├── .env.example                        # 环境变量模板（.env 被忽略）
│   ├── requirements.txt
│   └── *.py                                # 入库 / 服务 / Agent 逻辑
├── springboot-01-start/                    # 日志输出目录
└── pom.xml
```
