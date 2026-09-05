# eval_self_correct.py — 评测自纠正闭环, 与 eval_generation.py 基线对比
import json, re, asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
from openai import AsyncOpenAI
from KnowledgeBase.self_correct import self_correct_answer

API = os.getenv("OPENAI_BASE_URL", "https://api.siliconflow.cn/v1").rstrip("/")
COLLECTION = "kb_default"
TESTSET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Test_result", "testset.jsonl")
BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Test_result", "gen_result.jsonl")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Test_result", "gen_result_selfcorrect.jsonl")
CONCURRENCY = 3
LIMIT = None   # 调试: 先跑前 10 条; 验证通过后改为 None 跑全量

llm = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"))
MODEL = os.getenv("MODEL_NAME")

# 判官口径与基线完全一致
CORRECT_PROMPT = """判断【回答】与【标准答案】是否语义一致(等价信息即可, 不需逐字一致)。
只输出 JSON: {{"verdict": "correct|wrong", "reason": "一句话"}}
标准答案: {gold}
回答: {answer}"""


async def judge(sem, gold, answer):
    async with sem:
        try:
            resp = await asyncio.wait_for(
                llm.chat.completions.create(
                    model=MODEL, temperature=0,
                    messages=[{"role": "user", "content":
                        CORRECT_PROMPT.format(gold=gold, answer=answer)}]),
                timeout=60.0,          # 判官调用同样加硬超时
            )
            content = resp.choices[0].message.content or ""
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.S)
            content = re.sub(r"```(?:json)?|```", "", content)
            start, end = content.find("{"), content.rfind("}")
            try:
                return json.loads(content[start:end + 1])
            except json.JSONDecodeError:
                m = re.search(r'"verdict"\s*:\s*"(\w+)"', content)
                return {"verdict": m.group(1), "reason": "正则兜底"} if m else \
                       {"verdict": "error", "reason": "无法解析"}
        except Exception as e:
            return {"verdict": "error", "reason": str(e)}


async def main():
    all_rows = [json.loads(l) for l in open(TESTSET, encoding="utf-8") if l.strip()]
    testset = all_rows[:LIMIT] if LIMIT else all_rows
    baseline_rows = [json.loads(l) for l in open(BASELINE, encoding="utf-8") if l.strip()]
    base_correct = sum(1 for r in baseline_rows if r.get("correct") == "correct")
    base_n = len(baseline_rows)
    print(f"基线: 答案正确率 {base_correct}/{base_n} = {base_correct/base_n:.1%}")

    sem = asyncio.Semaphore(CONCURRENCY)

    async def run(item, idx):
        async with sem:
            print(f"  [{idx + 1}/{len(testset)}] 开始 ...", flush=True)
            try:
                res = await asyncio.wait_for(
                    self_correct_answer(item["question"], COLLECTION, max_attempts=2),
                    timeout=180,          # 单条 3 分钟硬超时, 防止整批卡死
                )
            except asyncio.TimeoutError:
                print(f"  [{idx + 1}/{len(testset)}] 超时, 跳过", flush=True)
                return {"question": item["question"], "answer": "(单条超时)",
                        "chunks": [], "attempts": -1, "corrected": False}
            print(f"  [{idx + 1}/{len(testset)}] 完成 (attempts={res['attempts']})", flush=True)
            return res

    print(f"测试集 {len(testset)} 条, 开始自纠正评测 ...")
    results = await asyncio.gather(
        *[run(it, i) for i, it in enumerate(testset)],
        return_exceptions=True,       # 单条异常不拖垮整体
    )
    results = [
        r if not isinstance(r, Exception) else {
            "question": it["question"], "answer": "(评测异常)",
            "chunks": [], "attempts": -1, "corrected": False,
        }
        for it, r in zip(testset, results)
    ]

    verdicts = await asyncio.gather(*[
        judge(sem, it["answer"], r["answer"]) for it, r in zip(testset, results)])

    n = len(testset)
    correct = sum(1 for v in verdicts if v.get("verdict") == "correct")
    err = sum(1 for v in verdicts if v.get("verdict") == "error")
    corrected_cases = sum(1 for r in results if r["corrected"])
    print(f"\n===== 自纠正后 (max_attempts=2) =====")
    print(f"答案正确率:      {correct}/{n} = {correct/n:.1%}   (基线 {base_correct/base_n:.1%})")
    print(f"触发纠正:        {corrected_cases} 条")
    print(f"裁判失败:        {err} 条")

    with open(OUT, "w", encoding="utf-8") as f:
        for it, r, v in zip(testset, results, verdicts):
            f.write(json.dumps({
                "question": it["question"], "gold": it["answer"],
                "answer": r["answer"], "attempts": r["attempts"],
                "corrected": r["corrected"], "correct": v.get("verdict"),
                "reason_c": v.get("reason", ""),
            }, ensure_ascii=False) + "\n")
    print(f"明细已导出 → {OUT}")

asyncio.run(main())
