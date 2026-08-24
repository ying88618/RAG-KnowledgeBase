# eval_retrieval.py — python eval_retrieval.py
import os, json, asyncio
from dotenv import load_dotenv
from KnowledgeBase.retriever import retrieve

load_dotenv()   # 路径按你的实际情况

COLLECTION = "kb_chunk300"           # ← 你的库名
TESTSET = "testset.jsonl"
K_LIST = [2, 4, 6, 8]
TH_LIST = [None, 0.25, 0.30, 0.40]  # None = 不过滤
MAX_K = max(K_LIST)

def load_testset():
    with open(TESTSET, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]

async def main():
    testset = load_testset()
    print(f"测试集 {len(testset)} 条, 开始检索 ...")

    # 每题只查一次: 取 Top-MAX_K、不设阈值, 带着分数返回
    cache = []   # cache[i] = [(file_name, score), ...] 按相似度降序
    for i, item in enumerate(testset):
        results = await retrieve(item["question"], COLLECTION,
                                 k=MAX_K, score_threshold=None)
        cache.append([(r["file_name"], r["score"]) for r in results])
        if (i + 1) % 20 == 0:
            print(f"  已检索 {i+1}/{len(testset)}")

    # 本地计算网格
    print(f"\n{'K':>4} {'阈值':>6} {'HitRate':>9} {'MRR':>7} {'文档覆盖':>8}")
    for k in K_LIST:
        for th in TH_LIST:
            hits, mrr_sum, cov_sum = 0, 0.0, 0.0
            for item, ranked in zip(testset, cache):
                # 复现 retrieve 的行为: 先取前 k, 再滤掉低于阈值的
                top = ranked[:k]
                if th is not None:
                    top = [x for x in top if x[1] >= th]
                ranks = [i for i, x in enumerate(top)
                         if x[0] == item["source_file"]]
                if ranks:
                    hits += 1
                    mrr_sum += 1.0 / (ranks[0] + 1)
                cov_sum += len(set(x[0] for x in top))
            n = len(testset)
            th_str = "无" if th is None else f"{th:.2f}"
            print(f"{k:>4} {th_str:>6} {hits/n:>9.1%} {mrr_sum/n:>7.3f} {cov_sum/n:>8.2f}")

asyncio.run(main())
