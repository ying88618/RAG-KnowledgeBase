import os
import httpx
from .vectorstore import build_vs
from .bm25_index import get_bm25

RERANK_API = os.getenv("OPENAI_BASE_URL", "https://api.siliconflow.cn/v1").rstrip("/")
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")


def _rerank(query: str, docs: list[str], top_n: int):
    """调用 rerank API, 返回 [{"index": i, "relevance_score": s}, ...]; 失败返回 None"""
    try:
        resp = httpx.post(
            f"{RERANK_API}/rerank",
            headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"},
            json={
                "model": RERANK_MODEL,
                "query": query,
                "documents": docs,
                "top_n": top_n,
                "return_documents": False,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["results"]
    except Exception:
        return None  # 失败时降级为双塔排序


def _rrf_fusion(lists: list[list[dict]], rank_constant: int = 60) -> list[dict]:
    """按排名融合检索结果"""
    scores: dict[str, float] = {}
    items: dict[str, dict] = {}
    for lst in lists:
        for rank, item in enumerate(lst):
            key = item["content"][:200]
            scores[key] = scores.get(key, 0.0) + 1.0 / (rank_constant + rank + 1)
            items[key] = item
    ordered = sorted(scores, key=lambda k: -scores[k])
    return [items[k] for k in ordered]


async def retrieve(
    question: str,
    collection_name: str,
    k: int = 4,
    score_threshold: float | None = None,
    recall_k: int = 20,
    hybrid: bool = False,
) -> list[dict]:
    """两阶段检索: 向量召回 Top-recall_k → rerank 精排 → 取 Top-k"""
    vs = build_vs(collection_name)
    docs_and_scores = await vs.asimilarity_search_with_score(question, k=recall_k)
    vec_cands = [
        {
            "content": d.page_content,
            "file_name": d.metadata.get("file_name", "未知"),
            "doc_id": d.metadata.get("doc_id"),
            "score": float(s),
        }
        for d, s in docs_and_scores
    ]

    if hybrid:
        bm_cands = get_bm25(collection_name).search(question, k=recall_k)
        candidates = _rrf_fusion([vec_cands, bm_cands])[:recall_k]
    else:
        candidates = vec_cands

    if not candidates:
        return []

    ranked = _rerank(question, [c["content"] for c in candidates], k)
    if ranked is not None:
        results = []
        for r in ranked:
            c = dict(candidates[r["index"]])
            c["score"] = float(r["relevance_score"])
            results.append(c)
    else:
        results = candidates[:k]  # 降级: 双塔
        if score_threshold is not None:
            results = [r for r in results if r["score"] >= score_threshold]
    return results
