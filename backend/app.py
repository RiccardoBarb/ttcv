from datetime import datetime,timezone
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from backend.inference.flow import get_rag_flow
from backend.inference.retriever import Retriever
from dotenv import load_dotenv
import logging
import yaml
import json
import os


load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Lifespan: load heavy objects once at startup ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    with open("backend/cfg.yml", "r") as c:
        app.state.cfg = yaml.load(c, Loader=yaml.SafeLoader)
    with open("backend/prompts.yml", "r") as p:
        app.state.prompts = yaml.load(p, Loader=yaml.SafeLoader)
    app.state.retriever = Retriever(app.state.cfg)
    app.state.rag = get_rag_flow()
    yield

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(lifespan=lifespan)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:8080"],
                   allow_methods=["POST"],allow_headers=["Content-Type"])
app.state.limiter = limiter


class QueryRequest(BaseModel):
    query: str
    history: list = []


class QueryResponse(BaseModel):
    answer: str
    history: list

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429,content={"detail": "too many requests, slow down"})


@app.post("/ask", response_model=QueryResponse)
@limiter.limit("10/minute;100/day")
def ask(request: Request, body: QueryRequest):
    shared = {"query": body.query, "history": body.history, "retriever": request.app.state.retriever,
              "cfg": request.app.state.cfg, "prompts": request.app.state.prompts}
    request.app.state.rag.run(shared)
    chs = shared.get("history", [])
    if len(chs)>0:
        chs = chs[:-1]
    logger.info(json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(), "ip": request.client.host,
                            "query": body.query,"contextualized_query":shared["query"],
                            "answer": shared["generated_answer"],"route": shared.get("route"),
                            "relevance": shared.get("relevance"),"history": chs,
                            "retrieved_context": shared.get("retrieved_context",{}).get('context'),
                            'read_document':shared.get('read_document')}))
    return QueryResponse(answer=shared["generated_answer"], history=shared["history"])