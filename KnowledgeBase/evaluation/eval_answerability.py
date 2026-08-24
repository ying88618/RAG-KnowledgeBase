# eval_answerability.py — python eval_answerability.py
import os, re, json, asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI
from KnowledgeBase.retriever import retrieve
import httpx   # 顶部加

API = os.getenv("OPENAI_BASE_URL", "https://api.siliconflow.cn/v1").rstrip("/")

def rerank(query, docs, top_n):
    resp = httpx.post(f"{API}/rerank",
        headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
        json={"model": "BAAI/bge-reranker-v2-m3",
              "query": query, "documents": docs,
              "top_n": top_n, "return_documents": False},
        timeout=30)
    resp.raise_for_status()
    return resp.json()["results"]

load_dotenv()

COLLECTION = "kb_chunk300"
TESTSET = "testset.jsonl"
K = 4                    # 与线上 graph.py 的 k=4 一致
CONCURRENCY = 5
OUT = "answerability.jsonl"

llm = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"),
                  base_url=os.getenv("OPENAI_BASE_URL"))
MODEL = os.getenv("MODEL_NAME")

JUDGE_PROMPT = """你是检索质量评估员。判断下面的检索片段能否回答用户问题。

判断规则:
1. 只能依据片段内容判断, 禁止使用你自己掌握的知识(即使你知道答案, 片段里没有就算不能);
2. yes = 片段包含足够回答问题的关键信息;
3. partial = 片段沾边但信息不完整, 只能回答一部分;
4. no = 片段与问题基本无关;
5. 只输出 JSON, 不要其他文字: {{"verdict": "yes|partial|no", "reason": "一句话理由"}}

用户问题: {question}

检索片段:
{contexts}"""

def load_testset():
    with open(TESTSET, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]

async def judge(sem, item, contexts):
    async with sem:
        try:
            resp = await llm.chat.completions.create(
                model=MODEL, temperature=0,
                messages=[{"role": "user", "content":
                    JUDGE_PROMPT.format(question=item["question"],
                                        contexts=contexts)}])
            content = resp.choices[0].message.content or ""
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.S)
            start, end = content.find("{"), content.rfind("}")
            verdict = json.loads(content[start:end+1]).get("verdict", "no")
            return verdict if verdict in ("yes", "partial", "no") else "no"
        except Exception as e:
            print("裁判失败:", e)
            return "error"

async def main():
    testset = load_testset()
    print(f"测试集 {len(testset)} 条, K={K}, 开始检索 + 裁判 ...")
    sem = asyncio.Semaphore(CONCURRENCY)

    records = []
    for i, item in enumerate(testset):
        results = await retrieve(item["question"], COLLECTION,
                                 k=20, score_threshold=None)   # 召回 20
        ranked = rerank(item["question"],
                        [r["content"] for r in results], 4)     # 精排取 4
        results = [results[r["index"]] for r in ranked]         # 换成重排结果
        contexts = "\n\n".join(
            f"[片段{j+1} 来源:{r['file_name']}]\n{r['content']}"
            for j, r in enumerate(results))
        records.append((item, contexts))
        if (i + 1) % 20 == 0:
            print(f"  检索完成 {i+1}/{len(testset)}")

    tasks = [judge(sem, item, ctx) for item, ctx in records]
    verdicts = await asyncio.gather(*tasks)

    n = len(testset)
    yes = verdicts.count("yes")
    partial = verdicts.count("partial")
    no = verdicts.count("no")
    err = verdicts.count("error")

    print(f"\n===== 内容级可回答率 (Top-{K}) =====")
    print(f"完全可回答 (yes):     {yes:3d} 条 ({yes/n:.1%})")
    print(f"部分可回答 (partial): {partial:3d} 条 ({partial/n:.1%})")
    print(f"不能回答 (no):        {no:3d} 条 ({no/n:.1%})")
    if err:
        print(f"裁判失败 (error):     {err:3d} 条 (建议重跑)")
    print(f"可回答率(宽松 yes+partial):       {(yes+partial)/n:.1%}")
    print(f"可回答率(加权 yes+0.5*partial):   {(yes+0.5*partial)/n:.1%}")

    with open(OUT, "w", encoding="utf-8") as f:
        for (item, ctx), v in zip(records, verdicts):
            f.write(json.dumps({"question": item["question"],
                                "source_file": item["source_file"],
                                "verdict": v}, ensure_ascii=False) + "\n")
    print(f"\n明细已导出 → {OUT}")

asyncio.run(main())
