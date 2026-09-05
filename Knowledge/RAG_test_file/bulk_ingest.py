# bulk_ingest.py — python bulk_ingest.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  # 和 RAG_QA.py 相同的加载方式

from KnowledgeBase.loaders import parse_bytes
from KnowledgeBase.vectorstore import store_chunks
from langchain_text_splitters import RecursiveCharacterTextSplitter

SRC_DIR = r"E:\RAG_test"   # ← 改成你的文档文件夹
COLLECTION = "kb_default"       # ← 实验A新库, 千万别写 kb_default
CHUNK_SIZE = 400                 # 实验A; baseline 是 400
OVERLAP = 120                     # 实验A; baseline 是 120

EXT_TYPE = {".pdf": "pdf", ".docx": "docx", ".md": "md", ".txt": "txt"}

async def main():
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=OVERLAP)
    files = sorted(p for p in Path(SRC_DIR).iterdir()
                   if p.suffix.lower() in EXT_TYPE)
    print(f"发现 {len(files)} 个文件 → 库 {COLLECTION} "
          f"(chunk={CHUNK_SIZE}, overlap={OVERLAP})")

    total = 0
    for i, fp in enumerate(files, 1):
        try:
            text = parse_bytes(fp.read_bytes(), EXT_TYPE[fp.suffix.lower()])
            chunks = splitter.split_text(text)
            if not chunks:
                print(f"[{i}/{len(files)}] 跳过(无内容): {fp.name}")
                continue
            await store_chunks(chunks, doc_id=i, file_name=fp.name,
                               collection_name=COLLECTION)
            total += len(chunks)
            print(f"[{i}/{len(files)}] {fp.name}: {len(chunks)} chunks")
        except Exception as e:
            print(f"[{i}/{len(files)}] 失败 {fp.name}: {e}")

    print(f"\n完成: 共 {total} chunks → {COLLECTION}")

asyncio.run(main())
