"""
单配置版压测脚本：测试外部 Java 后端 localhost:8071 的 POST /stream (SSE) 接口。

关键点：
- Java 接口：POST /stream，produces=text/event-stream (SSE)
- 请求体 ChatRequest：sessionId / question / collectionName（驼峰）
- userId 由 Java 从 ThreadLocal 登录态注入，请求体不需传
- SSE 响应必须流式消费完，否则连接池耗尽导致假死
"""

import asyncio
import json
import time
from datetime import datetime

import httpx

# ===================== 配置区 =====================
BASE_URL = "http://localhost:8071"
PATH = "/chat/stream"
METHOD = "POST"  # 仅支持 POST
CONCURRENCY = 20  # 并发数
TOTAL_REQUESTS = 200  # 总请求数
TIMEOUT = 120  # 单请求超时（秒）
IS_SSE = True  # 是否为 SSE 流式接口
COLLECTION = "kb_default"  # collectionName
SESSION_PREFIX = "stress-test-session"  # sessionId 前缀
USER_ID = None  # Java userId 来自 ThreadLocal，不传；如需显式传可填字符串/数字

# 鉴权：若 Java 需要 Bearer Token，取消下一行注释并填入
AUTH_TOKEN ="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbGFpbXMiOnsiaWQiOjIwMTMyMDg1NzgsInVzZXJuYW1lIjoibGl1emltdSJ9LCJleHAiOjE3ODg3MTIwNzN9.QutycL5LsjZj6EwRUIIVRMaOIpueESUnm-JBdnEnAkA"

# 轮询的问题列表
QUESTIONS = [
    "什么是知识库检索？",
    "请介绍一下项目的核心功能。",
    "如何配置向量数据库连接？",
    "RAG 问答的流程是什么？",
    "重排序模型有什么作用？",
    "如何评估回答的可答性？",
]

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "text/event-stream",
}
if AUTH_TOKEN:
    HEADERS["Authorization"] =AUTH_TOKEN
# ==================================================


def build_payload(question: str, idx: int) -> dict:
    payload = {
        "sessionId": f"{SESSION_PREFIX}-{idx}",
        "question": question,
        "collectionName": COLLECTION,
    }
    if USER_ID is not None:
        payload["userId"] = USER_ID
    return payload


async def fire_once(client: httpx.AsyncClient, idx: int) -> dict:
    question = QUESTIONS[idx % len(QUESTIONS)]
    payload = build_payload(question, idx)
    record = {
        "idx": idx,
        "start": time.perf_counter(),
        "status": None,
        "ok": False,
        "error": None,
        "first_token_latency": None,
        "total_latency": None,
        "chunks": 0,
        "bytes": 0,
    }
    try:
        if IS_SSE:
            first_seen = False
            async with client.stream(
                METHOD, f"{BASE_URL}{PATH}", json=payload, headers=HEADERS
            ) as resp:
                record["status"] = resp.status_code
                async for chunk in resp.aiter_text():
                    if not chunk:
                        continue
                    record["bytes"] += len(chunk.encode("utf-8"))
                    record["chunks"] += 1
                    if not first_seen:
                        first_seen = True
                        record["first_token_latency"] = (
                            time.perf_counter() - record["start"]
                        )
                if resp.status_code < 400:
                    record["ok"] = True
        else:
            resp = await client.request(
                METHOD, f"{BASE_URL}{PATH}", json=payload, headers=HEADERS
            )
            record["status"] = resp.status_code
            record["bytes"] = len(resp.content)
            record["ok"] = resp.status_code < 400
        record["total_latency"] = time.perf_counter() - record["start"]
    except Exception as e:  # noqa: BLE001
        record["error"] = str(e)
        record["total_latency"] = time.perf_counter() - record["start"]
    return record


async def worker(
    client: httpx.AsyncClient, queue: asyncio.Queue, results: list, done: asyncio.Event
):
    while True:
        try:
            idx = queue.get_nowait()
        except asyncio.QueueEmpty:
            break
        rec = await fire_once(client, idx)
        results.append(rec)
        if len(results) % 20 == 0:
            print(f"  进度: {len(results)}/{TOTAL_REQUESTS}")
        queue.task_done()
        if queue.empty():
            done.set()


def _percentile(sorted_vals: list, pct: float) -> float:
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * pct
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


async def main():
    queue: asyncio.Queue = asyncio.Queue()
    for i in range(TOTAL_REQUESTS):
        queue.put_nowait(i)

    results: list = []
    done = asyncio.Event()

    limits = httpx.Limits(
        max_connections=CONCURRENCY * 2,
        max_keepalive_connections=CONCURRENCY * 2,
    )
    timeout_cfg = httpx.Timeout(TIMEOUT)

    wall_start = time.perf_counter()
    async with httpx.AsyncClient(timeout=timeout_cfg, limits=limits) as client:
        tasks = [
            asyncio.create_task(worker(client, queue, results, done))
            for _ in range(CONCURRENCY)
        ]
        await queue.join()
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    wall_elapsed = time.perf_counter() - wall_start

    # 统计
    total = len(results)
    ok = [r for r in results if r["ok"]]
    failed = total - len(ok)
    latencies = sorted(
        r["total_latency"] for r in results if r["total_latency"] is not None
    )
    first_latencies = sorted(
        r["first_token_latency"]
        for r in results
        if r["first_token_latency"] is not None
    )
    status_dist: dict = {}
    error_dist: dict = {}
    for r in results:
        if r["status"] is not None:
            status_dist[str(r["status"])] = status_dist.get(str(r["status"]), 0) + 1
        if r["error"]:
            error_dist[r["error"]] = error_dist.get(r["error"], 0) + 1

    print("\n==================== 压测结果 ====================")
    print(f"目标:        {METHOD} {BASE_URL}{PATH}")
    print(f"并发数:      {CONCURRENCY}")
    print(f"总请求数:    {TOTAL_REQUESTS}")
    print(f"实际完成:    {total}")
    print(f"成功:        {len(ok)}")
    print(f"失败:        {failed}")
    print(f"成功率:      {(len(ok) / total * 100) if total else 0:.2f}%")
    print(f"总耗时(墙钟): {wall_elapsed:.2f}s")
    print(f"实际 QPS:    {(total / wall_elapsed) if wall_elapsed else 0:.2f}")
    if latencies:
        print(f"总延迟 P50:  {_percentile(latencies, 0.50) * 1000:.1f} ms")
        print(f"总延迟 P90:  {_percentile(latencies, 0.90) * 1000:.1f} ms")
        print(f"总延迟 P95:  {_percentile(latencies, 0.95) * 1000:.1f} ms")
        print(f"总延迟 P99:  {_percentile(latencies, 0.99) * 1000:.1f} ms")
        print(f"总延迟 最大: {max(latencies) * 1000:.1f} ms")
    if first_latencies:
        print(f"首token P50: {_percentile(first_latencies, 0.50) * 1000:.1f} ms")
        print(f"首token P90: {_percentile(first_latencies, 0.90) * 1000:.1f} ms")
        print(f"首token P99: {_percentile(first_latencies, 0.99) * 1000:.1f} ms")
    if status_dist:
        print(f"状态码分布:  {status_dist}")
    if error_dist:
        print(f"错误分布:    {error_dist}")
    print("==================================================")

    # 明细导出
    out_file = f"stress_result_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
    with open(out_file, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"明细已导出: {out_file}")


if __name__ == "__main__":
    asyncio.run(main())
