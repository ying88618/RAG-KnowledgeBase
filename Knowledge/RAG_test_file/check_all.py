# check_all.py — 在 D:\Knowledge 下运行
import os
import time
from collections import Counter
from dotenv import load_dotenv
from pymilvus import MilvusClient

load_dotenv()

client = MilvusClient(uri=os.getenv("MILVUS_URI", "http://localhost:19530"))


def ensure_loaded(col: str, timeout: int = 60) -> bool:
    """确保 collection 已 load 到内存; Milvus 重启后必须重新 load 才能查询"""
    print(f"  load_state: {client.get_load_state(col)}")
    client.load_collection(col)  # 已加载时调用是无害的 no-op
    deadline = time.time() + timeout
    while time.time() < deadline:
        if "Loaded" in str(client.get_load_state(col)):
            return True
        time.sleep(2)
    return False


for col in client.list_collections():
    stats = client.get_collection_stats(col)
    print(f"\n=== collection: {col}  (row_count={stats['row_count']}) ===")

    if not ensure_loaded(col):
        print("  ✗ load 超时, 检查 Milvus 是否完全启动 (docker ps / 等 1 分钟)")
        continue

    try:
        res = client.query(
            collection_name=col,
            filter="doc_id >= 0",
            output_fields=["file_name"],
            limit=16384,
        )
        counter = Counter(r["file_name"] for r in res)
        for name, n in counter.most_common():
            print(f"  {n:5d} chunks  {name}")
        print(f"  → 共 {len(counter)} 个文件")
    except Exception as e:
        print("  无法读取:", e)
