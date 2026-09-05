# debug_judge.py — python debug_judge.py
import os, re, json, asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI
from KnowledgeBase.retriever import retrieve

load_dotenv()

llm = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"),
                  base_url=os.getenv("OPENAI_BASE_URL"))
MODEL = os.getenv("MODEL_NAME")

# 与 eval_answerability.py 完全一致的 prompt
JUDGE_PROMPT = """你是检索质量评估员。判断下面的检索片段能否回答用户问题。

判断规则:
1. 只能依据片段内容判断, 禁止使用你自己掌握的知识(即使你知道答案, 片段里没有就算不能);
2. yes = 片段包含足够回答问题的关键信息;
3. partial = 片段沾边但信息不完整, 只能回答一部分;
4. no = 片段与问题基本无关;
5. 只输出 JSON, 不要其他文字: {{"verdict": "yes|partial|no", "reason": "一句话理由"}}

用户问题: {question}

检索片段:
{contexts}"""

async def main():
    with open("testset.jsonl", encoding="utf-8") as f:
        items = [json.loads(l) for l in f if l.strip()][:3]   # 取前 3 条

    for item in items:
        results = await retrieve(item["question"], "kb_default",
                                 k=4, score_threshold=None)
        contexts = "\n\n".join(
            f"[片段{j+1} 来源:{r['file_name']}]\n{r['content']}"
            for j, r in enumerate(results))
        resp = await llm.chat.completions.create(
            model=MODEL, temperature=0,
            messages=[{"role": "user", "content":
                JUDGE_PROMPT.format(question=item["question"],
                                    contexts=contexts)}])
        raw = resp.choices[0].message.content or ""
        print("=" * 60)
        print("问题:", item["question"][:50])
        print("Top-1 内容前 60 字:", (results[0]["content"][:60] if results else "(空)"))
        print("裁判原始回复:")
        print(repr(raw[:400]))

asyncio.run(main())
