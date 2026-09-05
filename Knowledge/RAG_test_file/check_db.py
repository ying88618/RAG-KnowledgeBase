# check_db.py — python check_db.py
import os
from dotenv import load_dotenv
from pymilvus import MilvusClient

load_dotenv()
print("MILVUS_URI =", os.getenv("MILVUS_URI"))
print("EMBEDDING_MODEL =", os.getenv("EMBEDDING_MODEL"))

client = MilvusClient(uri=os.getenv("MILVUS_URI", "http://localhost:19530"))
for col in client.list_collections():
    print(col, "→ row_count =", client.get_collection_stats(col)["row_count"])
