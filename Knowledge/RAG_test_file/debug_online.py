# debug_online.py — python debug_online.py
import asyncio
from dotenv import load_dotenv
load_dotenv()
from KnowledgeBase.retriever import retrieve

QUESTIONS = [
    "粘贴一个 answerability 里 verdict=yes 的问题",
    "粘贴一个 verdict=no 的问题",
]

async def main():
    for q in QUESTIONS:
        for th in (None, 0.25):
            results = await retrieve(q, "kb_default",
                                     k=4, score_threshold=th)
            desc = [(r["file_name"], round(r["score"], 3)) for r in results]
            print(f"threshold={th}: {len(results)} 条 -> {desc}")
        print()

asyncio.run(main())
