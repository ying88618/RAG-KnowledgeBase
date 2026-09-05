import json
import asyncio
from fastapi import FastAPI
from sse_starlette.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel

from .llm import SYSTEM_PROMPT
from .graph import get_agent, set_request_context
from .memory import load_history, append_turn

app = FastAPI(title="Knowledge Chat")


class ChatRequest(BaseModel):
    session_id: str
    user_id: int
    question: str
    collection_name: str


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):

    history = load_history(req.user_id, req.session_id, n=6)
    append_turn(req.user_id, req.session_id, "user", req.question)

    agent = get_agent()
    config = {"configurable": {"score_threshold": 0.25}}

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += history
    messages.append({"role": "user", "content": req.question})

    async def event_generator():
        set_request_context(req.collection_name, score_threshold=0.25)

        full = []
        try:
            async for msg_chunk, _meta in agent.astream(
                {"messages": messages},
                config=config,
                stream_mode="messages",
            ):
                text = getattr(msg_chunk, "content", "")
                if text and isinstance(text, str):
                    full.append(text)
                    yield ServerSentEvent(
                        data={"type": "token", "content": text}
                    )

            append_turn(req.user_id, req.session_id, "assistant", "".join(full))
            yield ServerSentEvent(
                data={"type": "done", "content": "".join(full)}
            )

        except asyncio.CancelledError:
            logger = __import__("logging").getLogger("knowledge_agent")
            logger.info("SSE client disconnected, abort streaming.")
            raise

    return EventSourceResponse(
        event_generator(),
        media_type="text/event-stream",
        ping=15,          
    )