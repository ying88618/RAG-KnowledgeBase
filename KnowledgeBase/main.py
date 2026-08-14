# KnowledgeBase/main.py
from fastapi import FastAPI
from .ingest import app as ingest_app
from .chat import app as chat_app

app = FastAPI(title="RAG Agent Service")
app.include_router(ingest_app.router)
app.include_router(chat_app.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

#uvicorn KnowledgeBase.main:app --reload
