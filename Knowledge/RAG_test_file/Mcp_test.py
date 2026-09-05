import asyncio
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    # 关键：用 -m 模块方式启动，保证 .retriever 相对导入能解析
    server_params = StdioServerParameters(
        command=sys.executable,   # 用当前 venv 的 python，避免找不到 mcp 包
        args=["-m", "KnowledgeBase.mcp_server"],
        env=None,                 # 需要的话传 {"MCP_DEFAULT_COLLECTION": "kb_default"}
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("=== TOOLS ===")
            for t in tools.tools:
                print(f"- {t.name}: {t.description}")

            # knowledge_search 的 query 是必填，必须传
            result = await session.call_tool(
                "knowledge_search",
                arguments={
                    "query": "什么是知识库检索？",
                    "collection_name": "kb_default",
                    "k": 4,
                },
            )
            print("=== RESULT ===")
            for c in result.content:
                print(c.text if hasattr(c, "text") else c)

asyncio.run(main())

