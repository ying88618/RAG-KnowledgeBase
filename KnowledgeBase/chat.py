import json
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .llm import SYSTEM_PROMPT
from .graph import make_agent
from .memory import load_history, append_turn

app = FastAPI(title="Knowledge Chat")


class ChatRequest(BaseModel):
    session_id: str
    user_id: int
    question: str
    collection_name: str


def format_context(results: list[dict]) -> str:
    if not results:
        return "（无相关参考资料）"
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] 来源:{r['file_name']}\n{r['content']}")
    return "\n\n".join(lines)


def format_sources(results: list[dict]) -> list[dict]:
    return [{"file_name": r["file_name"], "score": r["score"]} for r in results]


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):

    history = load_history(req.user_id, req.session_id, n=10)
    append_turn(req.user_id, req.session_id, "user", req.question)

    agent = make_agent(req.collection_name)
    config = {"configurable": {"thread_id": req.session_id}}

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += history
    messages.append({"role": "user", "content": req.question})

    async def event_generator():

        full = []
        async for msg_chunk, _meta in agent.astream(
            {"messages": messages},
            config=config,
            stream_mode="messages",
        ):
            text = getattr(msg_chunk, "content", "")
            if text and isinstance(text, str):
                full.append(text)
                yield f"data: {json.dumps({'type': 'token', 'content': text}, ensure_ascii=False)}\n\n"

        answer = "".join(full)
        append_turn(req.user_id, req.session_id, "assistant", answer)
        yield f"data: {json.dumps({'type': 'done', 'content': ''.join(full)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
