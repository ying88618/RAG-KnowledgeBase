from langchain.agents import create_agent

from langchain_core.tools import tool
from .retriever import retrieve
from .web_search import web_search as tavily_web_search
from .llm import llm
import logging
import contextvars

_current_collection: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_collection"
)
_current_threshold: contextvars.ContextVar[float] = contextvars.ContextVar(
    "current_threshold", default=0.5
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("knowledge_agent")


@tool
async def knowledge_base_search(query: str):
    """当用户需要私人知识库信息时调用"""
    collection_name = _current_collection.get()
    score_threshold = _current_threshold.get()
    logger.info("[TOOL CALLED] knowledge_base_search query=%r", query)
    results = await retrieve(
        query, collection_name, k=4, score_threshold=score_threshold
    )
    logger.info(
        "[TOOL RETURNED] %d docs (threshold=%.2f)", len(results), score_threshold
    )
    if not results:
        return "(知识库中未找到相关资料)"
    return "\n\n".join(f"来源:{r['file_name']}\n{r['content']}" for r in results)


@tool
async def web_search(query: str):
    """当需要实时/互联网信息，或知识库无相关内容时调用，返回联网检索结果"""
    logger.info("[TOOL CALLED] web_search query=%r", query)
    return await tavily_web_search(query)


def set_request_context(collection_name: str, score_threshold: float = 0.5):
    _current_collection.set(collection_name)
    _current_threshold.set(score_threshold)


AGENT = create_agent(llm, tools=[web_search, knowledge_base_search])


def get_agent():
    """返回全局唯一agent实例"""
    return AGENT
