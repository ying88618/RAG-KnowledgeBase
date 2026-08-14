import traceback

from fastapi import FastAPI
from .schemas import IngestRequest, IngestResponse
from .pipeline import run_ingest


app = FastAPI(title="Knowledge Ingest")


@app.post("/documents/ingest", response_model=IngestResponse)
async def ingest(request: IngestRequest):
    try:
        chunk_count = await run_ingest(request)
        return IngestResponse(success=True, chunk_count=chunk_count)
    except Exception as e:
        traceback.print_exc()
        return IngestResponse(success=False, chunk_count=0, message=repr(e))


# uvicorn KnowledgeBase.ingest:app --reload
