from .vectorstore import build_vs


async def retrieve(
    question: str,
    collection_name: str,
    k: int = 4,
    score_threshold: float | None = None,
) -> list[dict]:
    """从向量库检索与问题最相关的 k 个 chunk,返回带元数据的片段"""
    vs = build_vs(collection_name)

    docs_and_scores = await vs.asimilarity_search_with_score(question, k=k)
    results = []
    for doc, score in docs_and_scores:
        s = float(score)
        if score_threshold is not None and s > score_threshold:
            continue
        results.append(
            {
                "content": doc.page_content,
                "file_name": doc.metadata.get("file_name", "未知"),
                "doc_id": doc.metadata.get("doc_id"),
                "score": float(score),
            }
        )
    return results
