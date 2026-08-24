import os
import json
from dotenv import load_dotenv
from requests import session

load_dotenv()

import redis

_redis = redis.Redis.from_url(
    os.getenv("REDIS_URL"),
    decode_responses=True,
)

HISTORY_TTL = int(os.getenv("CHAT_HISTORY_TTL", "1800"))


def _key(user_id: int, session_id: str) -> str:
    return f"user_memory:{user_id}:{session_id}"


def load_history(user_id: int, session_id: str, n: int = 6) -> list[dict]:
    """取最近n条对话，按时间正序返回[{role,content}]"""
    raw = _redis.lrange(_key(user_id, session_id), -n, -1)
    out = []
    for item in raw:
        try:
            out.append(json.loads(item))
        except json.JSONDecodeError:
            continue
    return out


def append_turn(user_id: int, session_id: str, role: str, content: str) -> None:
    """追加一条对话，并刷新TTL"""
    _redis.rpush(
        _key(user_id, session_id),
        json.dumps({"role": role, "content": content}, ensure_ascii=False),
    )

    _redis.expire(_key(user_id, session_id), HISTORY_TTL)
