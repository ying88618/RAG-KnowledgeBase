import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
load_dotenv()

embeddings = OpenAIEmbeddings(
    model=os.getenv("EMBEDDING_MODEL","BAAI/bge-large-zh-v1.5"),
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL"),
)