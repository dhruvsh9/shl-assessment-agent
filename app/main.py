from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.agent import respond
from app.catalog import load_catalog
from app.schemas import ChatRequest, ChatResponse



@asynccontextmanager
async def lifespan(app: FastAPI):
    load_catalog()
    yield


app = FastAPI(title="SHL Assessment Conversational Agent", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    return respond(request)
