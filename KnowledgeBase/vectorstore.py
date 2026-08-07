import os
from langchain_postgres import PGVector
from langchain_core.documents import Document
from .embeddings import embeddings

CONNECTION = os.getenv("DATABASE_URL")


def _build_vs(collection_name: str) -> PGVector:
    return PGVector(
        embeddings=embeddings,
        collection_name=collection_name,
        connection=CONNECTION,
        async_mode=True,
        create_extension=False,
        pre_delete_collection=False,
    )


async def store_chunks(chunks, *, doc_id, file_name, collection_name) -> None:
    docs = [
        Document(page_content=c, metadata={"doc_id": doc_id, "file_name": file_name})
        for c in chunks
    ]
    vs = _build_vs(collection_name)
    await vs.aadd_texts(
        [d.page_content for d in docs],
        metadatas=[d.metadata for d in docs],
    )