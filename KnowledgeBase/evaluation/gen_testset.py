
import os, json, asyncio, random, re
from openai import AsyncOpenAI
from dotenv import load_dotenv
from pymilvus import MilvusClient

load_dotenv()

COLLECTION = "kb_default"   # ← 同上
SAMPLE_PER_FILE = 6      # 每个文件抽几个 chunk(防止大文件霸占测试集)
QA_PER_CHUNK = 2
CONCURRENCY = 5
OUT = "testset_raw.jsonl"

client = MilvusClient(uri=os.getenv("MILVUS_URI", "http://localhost:19530"))
llm = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"),
                  base_url=os.getenv("OPENAI_BASE_URL"))
MODEL = os.getenv("MODEL_NAME")

PROMPT = """你是测试集生成器。基于下面的文档片段生成 {n} 个中文问答对,要求:
1. 答案必须能仅凭这个片段回答,禁止使用片段外的知识;
2. 问题不要直接复述片段原句(换一种问法),但答案要忠实于原文;
3. 难度混合:偏简单(直接找得到)和偏理解(需要归纳)都要有;
4. 只输出 JSON 数组,不要任何其他文字:
[{{"question": "...", "answer": "...", "difficulty": "easy|hard"}}]

文档片段(来自文件《{fname}》):
{chunk}"""

def fetch_chunks():
    res = client.query(collection_name=COLLECTION, filter="doc_id >= 0",
                       output_fields=["text", "file_name", "doc_id"], limit=16384)
    random.seed(42)
    by_file = {}
    for r in res:
        if len(r["text"].strip()) >= 120:   # 跳过太短的碎片
            by_file.setdefault(r["file_name"], []).append(r)
    sampled = []
    for fname, chunks in by_file.items():
        random.shuffle(chunks)
        sampled += chunks[:SAMPLE_PER_FILE]
    return sampled

async def gen_for_chunk(sem, r):
    async with sem:
        try:
            resp = await llm.chat.completions.create(
                model=MODEL, temperature=0.2,
                messages=[{"role": "user", "content":
                    PROMPT.format(n=QA_PER_CHUNK, fname=r["file_name"], chunk=r["text"])}])
            content = resp.choices[0].message.content or ""
            # 去掉思考标签(如有)
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.S)
            # 用 find/rfind 定位 JSON 数组, 不用正则转义, 复制安全
            start, end = content.find("["), content.rfind("]")
            if start == -1 or end <= start:
                raise ValueError("回复里没有 JSON 数组")
            items = json.loads(content[start:end+1])
            return [{"question": str(it.get("question", "")).strip(),
                     "answer": str(it.get("answer", "")).strip(),
                     "source_file": r["file_name"],
                     "source_doc_id": r["doc_id"]}
                    for it in items
                    if str(it.get("question", "")).strip() and str(it.get("answer", "")).strip()]
        except Exception as e:
            print("跳过一个 chunk:", e)
            return []

async def main():
    chunks = fetch_chunks()
    print(f"抽样 {len(chunks)} 个 chunk, 开始生成 QA ...")
    sem = asyncio.Semaphore(CONCURRENCY)
    results = await asyncio.gather(*(gen_for_chunk(sem, r) for r in chunks))
    n = 0
    with open(OUT, "w", encoding="utf-8") as f:
        for batch in results:
            for item in batch:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                n += 1
    print(f"完成: {n} 条 QA → {OUT}")

asyncio.run(main())