from pydantic import BaseModel


class IngestRequest(BaseModel):
    doc_id: int
    file_url: str
    file_name: str
    file_type: str
    collection_name: str


class IngestResponse(BaseModel):
    success: bool
    chunk_count: int
    message: str = "向量化完成"