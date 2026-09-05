# check_ingest.py
import os
from collections import Counter
from dotenv import load_dotenv
from pymilvus import MilvusClient

load_dotenv()
COLLECTION = "kb_default"  # ← 改成你实际用的 collection 名

client = MilvusClient(uri=os.getenv("MILVUS_URI", "localhost:19530"))

stats = client.get_collection_stats(COLLECTION)
print("总行数:", stats["row_count"])

res = client.query(
    collection_name=COLLECTION,
    filter="doc_id >= 0",
    output_fields=["file_name"],
    limit=16384,
)
counter = Counter(r["file_name"] for r in res)
for name, n in counter.most_common():
    print(f"{n:5d} chunks  {name}")
print(f"共 {len(counter)} 个文件, {sum(counter.values())} 个 chunk")
