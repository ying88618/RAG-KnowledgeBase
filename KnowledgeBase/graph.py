from langchain.agents import create_agent
from langchain_core.tools import tool

from .retriever import retrieve
from .llm import llm, SYSTEM_PROMPT
import logging


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("knowledge_agent")

def make_agent(collection_name: str, checkpointer=None):
    """构建 agent 的工厂函数。"""

    @tool
    async def knowledge_base_search(query: str):
        """当用户的问题超出【参考资料】范围、需要更多知识库内容时调用。
        返回检索到的相关资料；若知识库中无相关内容则返回提示语。
        """
        logger.info("[TOOL CALLED] knowledge_base_search query=%r", query)
        results = await retrieve(query, collection_name, k=4, score_threshold=0.3)
        logger.info("[TOOL RETURNED] %d docs (threshold=0.3)", len(results))
        if not results:
            return "(知识库中未找到相关资料)"
        return "\n\n".join(f"来源:{r['file_name']}\n{r['content']}" for r in results)

    return create_agent(llm, tools=[knowledge_base_search], checkpointer=checkpointer)
