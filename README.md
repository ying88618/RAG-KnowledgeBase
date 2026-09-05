# 私域文档知识库（RAG + 多工具 Agent）

> Java + Python 双服务架构的私域知识库问答系统：LangGraph 多工具 Agent 自主决策「本地知识库检索 / 联网搜索」，向量（bge-m3）+ BM25 关键词双通道召回、RRF 融合 + bge-reranker 精排的混合检索，SSE 流式输出，并配套一套覆盖检索与生成双端的 RAG 评测体系。

## 项目亮点

- **混合检索**：Milvus（bge-m3）向量召回 Top-20 + BM25（jieba 分词）关键词召回 Top-20，RRF 排名融合 → bge-reranker-v2-m3 精排 Top-4，rerank 服务异常时自动降级双塔排序
- **数据驱动优化**：自建 120 条 QA 评测集（LLM 生成 + 人工筛选 + LLM-as-a-Judge），检索 + 生成双端量化：**Hit Rate@4 45.8% → 68.3% → 96.7%，MRR 0.304 → 0.584 → 0.896；混合检索下答案正确率 29.2% → 90.0%（幻觉率 1.7%）**
- **多工具 Agent**：LangGraph `create_agent` 全局单例 + `contextvars` 请求级上下文隔离，并发请求零串库
- **全链路流式**：sse-starlette 实现 token 级 SSE 输出、心跳保活、断连处理，Java 端透传转发
- **独立完成双端开发**：Java 侧用户/权限/文件上传/OSS 全套业务 + Python 侧 AI 服务，独立联调

## 架构

```
┌──────────────┐  HTTP + SSE (8071 → 8000)  ┌────────────────────┐
│  Spring Boot │ ──────────────────────────► │  FastAPI Agent 服务 │
│  (Java 21)   │                             │  (uvicorn :8000)   │
│  :8071       │                             │  LangGraph Agent   │
└──────┬───────┘                             └─────────┬──────────┘
       │                                               │
       │        ┌──────────────┬───────────┐          │ 工具调用
       ▼        ▼              ▼           ▼          ▼
┌────────────┐ ┌──────────┐ ┌─────────┐ ┌──────────────┐ ┌──────────────┐
│ MySQL      │ │ Redis    │ │ 阿里 OSS │ │ Milvus       │ │ 硅基流动 API  │
│ 业务数据    │ │ 登录态/  │ │ 文件存储 │ │ 向量库        │ │ Qwen / bge-m3│
│            │ │ 聊天历史 │ │          │ │ (混合检索)      │ │ / reranker   │
└────────────┘ └──────────┘ └─────────┘ └──────────────┘ │ / Tavily     │
                                                        └──────────────┘
```

**检索链路**：

```
用户问题 → Agent 自主选择工具
  ├─ knowledge_base_search（私域问题）
  │    → 双通道召回：Milvus 向量 Top-20（bge-m3）+ BM25 关键词 Top-20
  │    → RRF 排名融合 → bge-reranker-v2-m3 精排 Top-4（失败自动降级）
  └─ web_search（实时/联网问题）→ Tavily
```

## 核心设计

### 1. 混合检索（`KnowledgeBase/retriever.py` + `KnowledgeBase/bm25_index.py`）

生成端评测定位到纯向量检索的术语召回缺陷后（`GetPri`/`HikariCP`/`dishes` 等精确词 Top-10 都召不回），引入 BM25 关键词通道：

- **召回阶段（双通道）**：Milvus + bge-m3（COSINE）向量召回 Top-20；BM25（jieba 中英混合分词、英文术语整词保留）关键词召回 Top-20
- **融合**：RRF（Reciprocal Rank Fusion）按排名融合双通道结果，不依赖分数量纲，chunk 按内容去重
- **精排阶段**：bge-reranker-v2-m3 对融合结果逐对打分，取 Top-4
- **容错**：rerank API 异常时自动降级为双塔排序，检索服务不中断

双通道互补：向量通道兜底语义改写问题，BM25 通道兜底精确术语/专有名词召回——评测答案正确率由 29.2% 提升至 90.0%。

### 2. Agent 并发隔离（`KnowledgeBase/graph.py`）

Agent 以模块级全局单例构建（`create_agent` 仅执行一次）；请求级的「知识库集合名 / 阈值」通过 `contextvars` 注入，在 SSE 生成器内部 set（保证与生成器同 task），工具函数执行时再读取——多个并发请求各自隔离、互不串库，且无需每次请求重建 Agent。

### 3. 流式输出（`KnowledgeBase/chat.py`）

基于 sse-starlette 的 `EventSourceResponse`：token 级推送、15s 心跳保活、`CancelledError` 捕获处理客户端断连；聊天历史存 Redis（TTL 1800s），多轮对话携带最近 6 轮上下文。

## 评测体系

> 评测脚本见 `RAG_test_file/`，测试集与结果见 `Test_result/`（在 `Knowledge/` 目录下用 venv 运行；`COLLECTION` / `.env` 路径请按实际环境调整）。

**方法论**：

- **测试集**：120 条 QA，LLM 从入库文档自动生成（要求问题不复述原文措辞，避免词汇重叠导致指标虚高）+ 人工筛选
- **文件级指标**：Hit Rate@K（Top-K 是否命中来源文档）、MRR
- **内容级指标**：LLM-as-a-Judge 可回答率（裁判判断 Top-4 内容能否回答问题；裁判仅可依据片段判断、禁止使用自身知识，结果经人工抽检校准）
- **对照实验**：分块参数、检索策略均为单变量对照

**结果**：

| 配置 | Hit Rate@4 | MRR | 内容可回答率* |
|---|---|---|---|
| 基线：向量检索 Top-4（分块 400/120） | 45.8% | 0.304 | 27.5% |
| 对照：分块 300/80 | 40.8% | 0.250 | 20.0% |
| 两阶段：召回 Top-20 + 精排 Top-4 | 68.3% | 0.584 | 48.3% |
| **混合检索：向量 + BM25 双通道 + RRF 融合** | **96.7%** | **0.896** | **96.7%** |

\* 可回答率为宽松口径（yes + partial；加权口径 yes + 0.5×partial：两阶段 39.2%、混合检索 94.6%）；语料为 13 份高相似度中文文档，裁判口径偏严格。混合检索下 HitRate@4 与可回答率一致（均为 96.7%），说明 Top-4 命中文档即片段可回答，检索端漏斗损耗已消除。

**生成端评测**（LLM 基于 Top-4 片段生成答案，LLM-as-Judge 双判定：groundedness「答案是否有片段依据」+ correctness「与标准答案语义一致」，judge 仅依据片段/标准答案、禁止使用自身知识，口径与可回答率评测一致）：

| 检索策略 | 幻觉率 | 答案正确率 |
|---|---|---|
| 纯向量检索 Top-4 | 1.7% | 29.2% |
| **混合检索（向量 + BM25 + RRF → rerank Top-4）** | **1.7%** | **90.0%** |

\* 幻觉率 = 无片段依据的答案占比；prompt 强制"片段不足即拒答"使幻觉率始终极低。片段覆盖（可回答率）由 48.3% 提升至 96.7% 后，答案正确率由 29.2% 升至 90.0%——正确率与可回答率的落差即生成端损耗，混合检索下两者已接近（96.7% vs 90.0%），说明瓶颈已从检索覆盖转向生成端。

**结论**：

1. 分块 300/80 为负优化（双指标一致下降），确认 400/120 处于最优区间——小 chunk 语义密度不足，改写后的问题与碎片化片段相似度下降；
2. 检索瓶颈在双塔排序而非召回（MRR 低 + 分数挤压），两阶段检索三指标全面提升；
3. 剩余未命中样本中过半为多文档知识重叠导致的判据假阴性（内容可答但文件不同），内容级指标更贴近真实体验；
4. **生成端评测定位真实瓶颈**：纯向量下 70% wrong 为"Top-4 无答案 → 诚实拒答"（幻觉率仅 1.7%，拒答机制生效），问题集中在 `GetPri`/`HikariCP`/`dishes` 等精确术语与专有名词——命中来源文档 ≠ Top-4 覆盖答案 chunk；
5. 引入 **BM25 关键词通道（jieba 分词）与向量检索 RRF 融合**，检索与生成双端全面提升：Hit Rate@4 68.3% → **96.7%**、MRR 0.584 → **0.896**、片段可回答率 48.3% → **96.7%**、答案正确率 29.2% → **90.0%**（幻觉率维持 1.7% 不增），印证"纯向量检索对精确匹配/术语/专有名词召回失效"的经典问题；并基于 120 条测试集验证了 query 改写型自纠正对"库中无答案"类问题无效（72 次纠正仅净增 2 条），确认优化应聚焦检索覆盖而非生成。

## 快速开始

### 1. 基础设施

**Milvus**（docker-compose 含 etcd + MinIO，见 `docker/milvus-compose.yml`）：

```bash
docker compose -f docker/milvus-compose.yml up -d
```

另需：**MySQL 8**（建库 `big_event`）、**Redis 6+**。

### 2. Python 端（Agent 服务）

```bash
cd KnowledgeBase
python -m venv .venv
.venv\Scripts\activate        # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # 填入真实 API Key

uvicorn KnowledgeBase.main:app --host 0.0.0.0 --port 8000
```

**环境变量**（`Knowledge/.env`，`.env` 已被 gitignore）：

| 变量 | 说明 |
|---|---|
| `OPENAI_API_KEY` | 硅基流动 API Key |
| `OPENAI_BASE_URL` | 模型代理地址（默认 `https://api.siliconflow.cn/v1`） |
| `MODEL_NAME` | 对话模型 |
| `EMBEDDING_MODEL` | 嵌入模型（默认 `BAAI/bge-m3`） |
| `RERANK_MODEL` | 重排模型（默认 `BAAI/bge-reranker-v2-m3`） |
| `MILVUS_URI` | Milvus 地址（默认 `http://localhost:19530`） |
| `REDIS_URL` | Redis 连接串 |
| `CHAT_HISTORY_TTL` | 聊天历史过期时间（秒） |
| `TAVILY_API_KEY` | Tavily 联网搜索 Key |

### 3. Java 端（业务后端）

```powershell
$env:DB_PASSWORD="你的MySQL密码"
$env:JWT_KEY="一段足够长的随机字符串"
$env:OSS_ACCESS_KEY_ID="你的OSS_ID"
$env:OSS_ACCESS_KEY_SECRET="你的OSS_SECRET"

mvnw.cmd spring-boot:run
```

启动后监听 `http://localhost:8071`，通过 `agent.base-url` 调用 Python 服务。

### 4. 文档入库

```bash
curl -X POST http://127.0.0.1:8000/documents/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "doc_id": 1,
    "file_url": "https://your-oss-bucket/doc.pdf",
    "file_name": "doc.pdf",
    "file_type": "pdf",
    "collection_name": "kb_default"
  }'
```

支持 `pdf` / `docx` / `md` / `txt`。文档经下载 → 解析 → 分块（400 字符 / 120 重叠）→ bge-m3 向量化 → 写入 Milvus。

### 5. 流式对话

```bash
curl -N -X POST http://127.0.0.1:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "s1",
    "user_id": 1,
    "question": "这份文档里栈满的条件是什么？",
    "collection_name": "kb_default"
  }'
```

SSE 事件格式：

```
data: {"type": "token", "content": "栈满的"}
data: {"type": "token", "content": "条件是..."}
data: {"type": "done", "content": "完整回答文本"}
```

## 目录结构

```
├── src/main/java/...              # Spring Boot 后端（用户/权限/文件上传/OSS）
├── KnowledgeBase/                 # Python AI 服务
│   ├── main.py                    # FastAPI 入口（ingest + chat）
│   ├── chat.py                    # SSE 流式对话接口
│   ├── graph.py                   # LangGraph Agent + 工具注册 + contextvars 隔离
│   ├── retriever.py               # 混合检索（向量+BM25 召回 + RRF + rerank 精排）
│   ├── bm25_index.py              # BM25 关键词索引（jieba 分词, 从 Milvus 拉 chunk 建索引）
│   ├── vectorstore.py             # Milvus 封装
│   ├── embeddings.py / llm.py     # 模型接入（硅基流动 OpenAI 兼容）
│   ├── chunker.py / loaders.py    # 分块与文档解析（pdf/docx/md/txt）
│   ├── pipeline.py / ingest.py    # 入库流水线
│   ├── memory.py                  # Redis 聊天历史
│   ├── web_search.py              # Tavily 联网搜索
│   └── self_correct.py            # 自纠正闭环（拒答检测 → query改写 → 合并重检索）
└── pom.xml
```

## 踩坑记录

开发过程中实际踩过并解决的坑，供参考：

1. **rerank 分数并非 0~1 归一化**：bge-reranker-v2-m3 返回的 relevance_score 呈双峰分布（相关对趋近 1、不相关对趋近 0，中位数仅 0.004）。曾用 0.25 阈值过滤导致检索结果被全量滤除（线上表现为「未检索到」）。通过绕过 Agent 直调检索 + 全量分数分布统计定位根因，最终改为 Top-K 截断策略。教训：**第三方 API 的分数语义要先实测分布再使用**。
2. **Milvus `get_collection_stats` 的 row_count 异步滞后**：刚插入的数据统计显示为 0，验证入库应使用 `query` 实查计数。
3. **langchain-milvus 对不存在的 collection 会静默创建空库**：查询返回空结果但不报错，易与「检索无结果」混淆，需显式校验。
4. **SSE 生成器与 contextvars**：FastAPI 的 SSE 响应生成器运行在独立 task 中，`set_request_context` 必须在生成器内部调用，工具函数才能读到当前请求的参数。

## 相关技术

Java 21 / Spring Boot 3.x / MyBatis-Plus / MySQL / Redis / 阿里云 OSS · Python / FastAPI / LangGraph / Milvus / bge-m3 / bge-reranker-v2-m3 / BM25（rank_bm25 + jieba）/ Tavily / sse-starlette
