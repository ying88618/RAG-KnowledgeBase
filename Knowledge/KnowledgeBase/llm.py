import os
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model=os.getenv("MODEL_NAME"),
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
    streaming=True,
    temperature=0.3,
)

SYSTEM_PROMPT = """你是一个智能助手，你的任务是回答用户的问题。
当用户问题需要知识库资料时，调用 knowledge_base_search 工具获取相关资料后再回答；
需要实时信息（如最新资讯、当前数据）时，调用 web_search 工具联网检索。
如果工具都找不到相关信息，请明确告知用户，不要编造。
"""