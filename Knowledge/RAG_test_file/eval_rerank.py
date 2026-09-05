# eval_rerank.py — python eval_rerank.py
import os, json, asyncio
import httpx
from dotenv import load_dotenv
from KnowledgeBase.retriever import retrieve

load_dotenv()

COLLECTION = "kb_default"
TESTSET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Test_result", "testset.jsonl")
RECALL_K = 20          # 召回候选数
FINAL_K = 4            # rerank 后保留
API = os.getenv("OPENAI_BASE_URL", "https://api.siliconflow.cn/v1").rstrip("/")
KEY = os.getenv("OPENAI_API_KEY")

def rerank(query, docs, top_n):
    resp = httpx.post(f"{API}/rerank",
        headers={"Authorization": f"Bearer {KEY}"},
        json={"model": "BAAI/bge-reranker-v2-m3",
              "query": query,
              "documents": docs,
              "top_n": top_n,
              "return_documents": False},
        timeout=30)
    resp.raise_for_status()
    return resp.json()["results"]   # [{"index": i, "relevance_score": s}, ...] 降序

def load_testset():
    with open(TESTSET, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]

async def main():
    testset = load_testset()
    hits, mrr_sum = 0, 0.0
    for i, item in enumerate(testset):
        cands = await retrieve(item["question"], COLLECTION,
                               k=RECALL_K, score_threshold=None)
        # 调试：检查前3条数据的召回情况
        if i < 3:
            print(f"\n[DEBUG] 第{i+1}条数据:")
            print(f"  问题: {item['question'][:60]}...")
            print(f"  标准文件: {item.get('source_file', 'N/A')}")
            print(f"  召回数量: {len(cands) if cands else 0}")
            if cands:
                print(f"  召回文件: {[c.get('file_name', 'N/A') for c in cands[:5]]}")
        if cands:
            ranked = rerank(item["question"],
                            [c["content"] for c in cands], FINAL_K)
            if i < 3:
                print(f"  ranked 返回: {ranked}")
                print(f"  ranked indices: {[r['index'] for r in ranked]}")
            top = [cands[r["index"]] for r in ranked]
            if i < 3:
                print(f"  top filenames: {[x.get('file_name', 'N/A') for x in top]}")
            ranks = [j for j, x in enumerate(top)
                     if x["file_name"] == item["source_file"]]
            if ranks:
                hits += 1
                mrr_sum += 1.0 / (ranks[0] + 1)
        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(testset)}")
    n = len(testset)
    print(f"\nrerank({RECALL_K}→{FINAL_K}):  HitRate@{FINAL_K} = {hits/n:.1%}   MRR = {mrr_sum/n:.3f}")
    print(f"对比 无rerank Top-4:  HitRate = 45.8%   MRR = 0.304")

asyncio.run(main())