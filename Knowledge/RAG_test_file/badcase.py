# analyze_badcases.py — python analyze_badcases.py
import os, json, asyncio
from dotenv import load_dotenv
from KnowledgeBase.retriever import retrieve

load_dotenv()

COLLECTION = "kb_default"
TESTSET = "testset.jsonl"

def load_testset():
    with open(TESTSET, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]

async def main():
    testset = load_testset()
    all_scores, misses = [], []
    for item in testset:
        results = await retrieve(item["question"], COLLECTION,
                                 k=8, score_threshold=None)
        all_scores += [r["score"] for r in results]
        if not any(r["file_name"] == item["source_file"] for r in results):
            misses.append({
                "question": item["question"],
                "expected_file": item["source_file"],
                "top4": [{"file": r["file_name"],
                          "score": round(r["score"], 3),
                          "text": r["content"][:80]}
                         for r in results[:4]],
            })

    s = sorted(all_scores)
    n = len(s)
    print(f"Top-8 分数分布: min={s[0]:.3f} P25={s[n//4]:.3f} "
          f"中位={s[n//2]:.3f} P75={s[3*n//4]:.3f} max={s[-1]:.3f}")
    print(f"Top-8 未命中: {len(misses)}/{len(testset)} 条")

    with open("badcases.jsonl", "w", encoding="utf-8") as f:
        for m in misses:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    print("未命中样本已导出 → badcases.jsonl")

asyncio.run(main())
