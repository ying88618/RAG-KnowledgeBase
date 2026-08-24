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
        import mammoth

        if not raw or raw[:2] != b"PK":
            raise HTTPException(
                status_code=400, detail="下载到的文件不是有效的 .docx（ZIP）格式"
            )
        try:
            result = mammoth.extract_raw_text(io.BytesIO(raw))
            return result.value
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"解析 docx 失败：{e}")


    if ft in ("md", "txt"):
        return raw.decode("utf-8", errors="ignore")

    raise HTTPException(status_code=400, detail=f"不支持此文件类型:{file_type}")
