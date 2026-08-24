import os
import httpx
from .vectorstore import build_vs

RERANK_API = os.getenv(
    "OPENAI_BASE_URL", "https://api.siliconflow.cn/v1"
).rstrip("/")
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


async def retrieve(
    question: str,
    collection_name: str,
    k: int = 4,
    score_threshold: float | None = None,
    recall_k: int = 20,
) -> list[dict]:
    """两阶段检索: 向量召回 Top-recall_k → rerank 精排 → 取 Top-k"""
    vs = build_vs(collection_name)
    docs_and_scores = await vs.asimilarity_search_with_score(
        question, k=recall_k
    )

    candidates = [
        {
            "content": doc.page_content,
            "file_name": doc.metadata.get("file_name", "未知"),
            "doc_id": doc.metadata.get("doc_id"),
            "score": float(score),
        }
        for doc, score in docs_and_scores
    ]
    if not candidates:
        return []

    ranked = _rerank(question, [c["content"] for c in candidates], k)
    if ranked is not None:
        results = []
        for r in ranked:
            c = dict(candidates[r["index"]])
            c["score"] = float(r["relevance_score"])
            results.append(c)
        # rerank 分数为原始量级(非 0~1), 不做阈值过滤, 靠 Top-K 截断
        # "知识库无相关内容"的场景交给模型判断(片段不相关时模型会说没找到,
        # 且 Agent 有 web_search 兜底)
    else:
        results = candidates[:k]  # 降级: 双塔分数, 阈值过滤才有意义
        if score_threshold is not None:
            results = [r for r in results if r["score"] >= score_threshold]
    return results

