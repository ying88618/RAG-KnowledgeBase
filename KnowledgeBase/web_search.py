import os
from tavily import TavilyClient

_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


async def web_search(query: str) -> str:
    resp = _client.search(
        query=query,
        max_results=5,
        search_depth="basic",
        topic="general",
    )
    results = resp.get("results", [])

    if not results:
        return "(联网搜索未找到相关内容)"
    return "\n\n".join(
        f"标题:{r.get('title','')}\n来源:{r.get('url','')}\n摘要:{r.get('content','')}"
        for r in results
    )
