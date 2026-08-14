import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

llm = ChatOpenAI(
    model=os.getenv("MODEL_NAME"),
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
    streaming=True,
    temperature=0.3,
)

SYSTEM_PROMPT = """你是一个基于知识库回答问题的智能助手。
请根据下面提供的【参考资料】和对话历史回答用户问题。
【参考资料】中已经包含了检索到的相关内容，优先基于它回答。
仅当【参考资料】明显不足以回答、需要补充检索时，才调用工具获取更多资料；
如果参考资料和工具都找不到相关信息，请明确说“知识库中未找到相关信息”，不要编造。
【参考资料】
{context}
"""

