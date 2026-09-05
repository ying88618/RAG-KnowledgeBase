import os
from langchain_milvus import Milvus
from langchain_core.documents import Document
from .embeddings import embeddings

MILVUS_URI = os.getenv("MILVUS_URI", "localhost:19530")


def build_vs(collection_name: str) -> Milvus:
    return Milvus(
        embedding_function=embeddings,
        collection_name=collection_name,
        connection_args={"uri": MILVUS_URI},
        auto_id=True,                 
        index_params={"index_type": "AUTOINDEX", "metric_type": "COSINE"},
        search_params={"metric_type": "COSINE"},
        drop_old=False,               
    )




async def store_chunks(chunks, *, doc_id, file_name, collection_name) -> None:
    docs = [
        Document(page_content=c, metadata={"doc_id": doc_id, "file_name": file_name})
        for c in chunks
    ]
    vs = build_vs(collection_name)
    await vs.aadd_texts(
        [d.page_content for d in docs],
        metadatas=[d.metadata for d in docs],
    )
