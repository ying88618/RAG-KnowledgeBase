import io
import httpx
from fastapi import HTTPException


async def download_file(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content


def parse_bytes(raw: bytes, file_type: str) -> str:
    ft = file_type.lower()
    if ft == "pdf":
        import pdfplumber

        parts = []
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            for page in pdf.pages:
                parts.append(page.extract_text() or "")
        return "\n".join(parts)

    if ft == "docx":
        import docx

        doc = docx.Document(io.BytesIO(raw))
        return "\n".join(p.text for p in doc.paragraphs)

    if ft in ("md", "txt"):
        return raw.decode("utf-8", errors="ignore")

    raise HTTPException(status_code=400, detail=f"不支持此文件类型:{file_type}")
