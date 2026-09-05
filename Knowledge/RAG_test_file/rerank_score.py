# check_rerank_scores.py — python check_rerank_scores.py
import json, asyncio
from dotenv import load_dotenv
from KnowledgeBase.retriever import retrieve

load_dotenv()
COLLECTION = "kb_default"

def load_testset():
    with open("testset.jsonl", encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]

async def main():
    testset = load_testset()
    all_scores = []
    for item in testset:
        results = await retrieve(item["question"], COLLECTION,
                                 k=4, score_threshold=None)
        all_scores += [r["score"] for r in results]  # 落地版: 已是 rerank 分数
    s = sorted(all_scores)
    n = len(s)
    print(f"Top-4 rerank 分数: min={s[0]:.4f} P25={s[n//4]:.3f} "
          f"中位={s[n//2]:.3f} P75={s[3*n//4]:.3f} max={s[-1]:.3f}")
    for th in (0.1, 0.25, 0.4, 0.5):
        kept = sum(1 for x in s if x >= th)
        print(f"阈值 {th}: 保留 {kept}/{n} ({kept/n:.0%}) 个 chunk")

asyncio.run(main())
