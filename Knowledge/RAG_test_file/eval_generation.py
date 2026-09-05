# 目标: 建立"生成端基线": 检索Top-4 → LLM生成答案 → groundedness判定 + 答案正确性判定
import os, re, json, asyncio, httpx, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
from openai import AsyncOpenAI
from KnowledgeBase.retriever import retrieve

load_dotenv()
API = os.getenv("OPENAI_BASE_URL", "https://api.siliconflow.cn/v1").rstrip("/")
COLLECTION = "kb_default"
TESTSET = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "Test_result", "testset.jsonl"
)
OUT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "Test_result", "gen_result.jsonl"
)
CONCURRENCY = 5
llm = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL")
)
MODEL = os.getenv("MODEL_NAME")


def rerank(query, docs, top_n):
    # 过滤空片段: SiliconFlow rerank 对空文档会返回 400, 需提前剔除
    docs = [d for d in docs if isinstance(d, str) and d.strip()]
    if not docs:  # 检索结果为空: 跳过 rerank, 不调 API
        return []
    try:
        resp = httpx.post(
            f"{API}/rerank",
            headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
            json={
                "model": "BAAI/bge-reranker-v2-m3",
                "query": query,
                "documents": docs,
                "top_n": min(top_n, len(docs)),
                "return_documents": False,
            },
            timeout=30,
        )
    except httpx.TimeoutException:
        print("rerank 超时, 降级为原始顺序")
        return [{"index": i} for i in range(min(top_n, len(docs)))]
    if resp.status_code != 200:  # 失败时打印原因并降级, 不中断整体评测
        print("rerank 失败:", resp.status_code, resp.text[:300])
        return [{"index": i} for i in range(min(top_n, len(docs)))]
    try:
        return resp.json()["results"]
    except (KeyError, ValueError):
        print("rerank 响应解析失败, 降级为原始顺序")
        return [{"index": i} for i in range(min(top_n, len(docs)))]


GEN_PROMPT = """基于下面的检索片段回答用户问题。
规则:
1. 只能使用片段中的信息, 禁止使用你自己的知识;
2. 片段信息不足时, 直接回复"知识库中暂无相关资料", 不要编造;
3. 回答要简洁。

用户问题: {question}
检索片段:
{contexts}"""

# 判定1: 答案是否有依据
GROUND_PROMPT = """你是质检员。判断【回答】是否能从【检索片段】中找到依据。
规则: 只能依据片段判断, 禁止使用自身知识。
- grounded = 回答内容片段中都有出处
- ungrounded = 回答编造了片段中不存在的关键信息
只输出 JSON: {{"verdict": "grounded|ungrounded", "reason": "一句话"}}
问题: {question}
片段:
{contexts}
回答: {answer}"""

# 判定2: 答案是否正确
CORRECT_PROMPT = """判断【回答】与【标准答案】是否语义一致(等价信息即可, 不需逐字一致)。
只输出 JSON: {{"verdict": "correct|wrong", "reason": "一句话"}}
标准答案: {gold}
回答: {answer}"""


async def judge(sem, prompt, **kw):
    async with sem:
        try:
            resp = await llm.chat.completions.create(
                model=MODEL,
                temperature=0,
                messages=[{"role": "user", "content": prompt.format(**kw)}],
            )
            content = resp.choices[0].message.content or ""
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.S)
            content = re.sub(r"```(?:json)?|```", "", content)  # 去掉代码块标记
            start, end = content.find("{"), content.rfind("}")
            try:
                return json.loads(content[start : end + 1])
            except json.JSONDecodeError:
                m = re.search(r'"verdict"\s*:\s*"(\w+)"', content)  # 兜底: 只抓 verdict
                return (
                    {"verdict": m.group(1), "reason": "json解析失败, 用正则兜底"}
                    if m
                    else {"verdict": "error", "reason": "judge输出无法解析"}
                )
        except Exception as e:  # 兜底: API 调用/解析异常
            return {"verdict": "error", "reason": f"judge异常: {e}"}


async def main():
    testset = [json.loads(l) for l in open(TESTSET, encoding="utf-8") if l.strip()]
    print(f"测试集 {len(testset)} 条, 开始 检索→生成→判定 ...")
    sem = asyncio.Semaphore(CONCURRENCY)

    # 1) 检索 + 生成(固定输入片段, 不走 Agent, 保证可控)
    async def _gen(item):
        async with sem:  # 限并发, 避免 rerank 被硅基流动限流
            results = await retrieve(item["question"], COLLECTION, k=20, hybrid=True)
            ranked = rerank(item["question"], [r["content"] for r in results], 4)
            results = [results[r["index"]] for r in ranked] if ranked else []
            contexts = (
                "\n\n".join(
                    f"[片段{j+1}]\n{r['content']}" for j, r in enumerate(results)
                )
                if results
                else "(检索无结果)"
            )
            resp = await llm.chat.completions.create(
                model=MODEL,
                temperature=0.3,
                messages=[
                    {
                        "role": "user",
                        "content": GEN_PROMPT.format(
                            question=item["question"], contexts=contexts
                        ),
                    }
                ],
            )
            return item, resp.choices[0].message.content or "", contexts

    gen_tasks = [_gen(item) for item in testset]

    samples = await asyncio.gather(*gen_tasks, return_exceptions=True)
    # 单条生成失败不应中断统计: 兜底为占位样本
    samples = [
        (item, f"(生成失败: {s})", "(检索无结果)") if isinstance(s, Exception) else s
        for item, s in zip(testset, samples)
    ]

    # 2) groundedness + 正确性 双判定
    g_tasks = [
        judge(sem, GROUND_PROMPT, question=i["question"], contexts=c, answer=a)
        for i, a, c in samples
    ]
    c_tasks = [
        judge(sem, CORRECT_PROMPT, gold=i["answer"], answer=a) for i, a, _ in samples
    ]
    gs, cs = await asyncio.gather(*[asyncio.gather(*g_tasks), asyncio.gather(*c_tasks)])

    # 3) 统计 + 导出
    n = len(samples)
    g_ok = sum(1 for g in gs if g.get("verdict") == "grounded")
    c_ok = sum(1 for c in cs if c.get("verdict") == "correct")
    print(f"\n===== 生成端基线 (Top-4) =====")
    print(f"grounded 有依据: {g_ok}/{n} = {g_ok/n:.1%}   → 幻觉率 {(n-g_ok)/n:.1%}")
    print(f"答案正确率:      {c_ok}/{n} = {c_ok/n:.1%}")
    with open(OUT, "w", encoding="utf-8") as f:
        for (i, a, _), g, cc in zip(samples, gs, cs):
            f.write(
                json.dumps(
                    {
                        "question": i["question"],
                        "gold": i["answer"],
                        "answer": a,
                        "grounded": g.get("verdict"),
                        "correct": cc.get("verdict"),
                        "reason_g": g.get("reason", ""),
                        "reason_c": cc.get("reason", ""),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    print(f"明细已导出 → {OUT}")


asyncio.run(main())

# set PYTHONPATH=e:\IdeaProjects\springboot\Knowledge
# .\venv\Scripts\python.exe RAG_test_file\eval_generation.py
