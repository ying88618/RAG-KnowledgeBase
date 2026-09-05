# 混合检索通道
import os
import re

import jieba
from pymilvus import MilvusClient
from rank_bm25 import BM25Okapi

_MILVUS_URL = os.getenv("MILVUS_URI", "https://localhost:19530")


def tokenize(text: str) -> list[str]:
    """中英文分开治理，英文保留术语，中文走jieba"""
    text = (text or "").lower()
    tokens = re.findall(r"[a-z0-9_+#.@-]+", text)
    zh = re.sub(r"[^\u4e00-\u9fff]", "", text)
    tokens += [t for t in jieba.cut(zh) if t.strip()]
    return tokens


def _load_all_chunks(collection_name: str) -> list[dict]:
    """从Milvus拉chunk"""
    client = MilvusClient(uri=_MILVUS_URL)
    rows = client.query(
        collection_name=collection_name,
        filter="",
        output_fields=["text", "doc_id", "file_name"],
        limit=5000,
    )
    return [
        {
            "content": r.get("text", ""),
            "file_name": r.get("file_name", "未知"),
            "doc_id": r.get("doc_id"),
        }
        for r in rows
    ]


class Bm25Index:
    def __init__(self, collection_name: str):
        chunks = _load_all_chunks(collection_name)
        self.chunks = chunks
        self.bm25 = BM25Okapi([tokenize(c["content"]) for c in chunks])

    def search(self, query: str, k: int = 20) -> list[dict]:
        if not self.chunks:
            return []
        toks = tokenize(query)
        if not toks:
            return []
        scores = self.bm25.get_scores(toks)
        top = sorted(range(len(scores)), key=lambda i: -scores[i])[:k]
        out = []
        for i in top:
            c = dict(self.chunks[i])
            c["bm25_score"] = float(scores[i])
            out.append(c)
        return out


_BM25_CACHE: dict[str, Bm25Index] = {}


def get_bm25(collection_name: str) -> Bm25Index:
    if collection_name not in _BM25_CACHE:
        _BM25_CACHE[collection_name] = Bm25Index(collection_name)
    return _BM25_CACHE[collection_name]
