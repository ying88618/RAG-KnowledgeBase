from .schemas import IngestRequest
from .loaders import download_file, parse_bytes
from .chunker import split
from .vectorstore import store_chunks


async def run_ingest(req: IngestRequest) -> int:
    raw = await download_file(req.file_url)
    text = parse_bytes(raw, req.file_type)
    chunks = split(text)
    chunk_count = len(chunks)
    await store_chunks(
        chunks,
        doc_id=req.doc_id,
        file_name=req.file_name,
        collection_name=req.collection_name,
    )
    return chunk_count
