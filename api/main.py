"""FastAPI server exposing the AskDSA tutor to the browser extension.

Run (from repo root):
    uvicorn api.main:app --reload --port 8000

Endpoints:
    GET  /health   -> {"status": "ok"}
    POST /tutor    -> {"answer": "..."}
         body: { "query": str, "level": 1-4, "url": "<problem url>" (optional) }
"""
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# make the sibling `rag` package importable when run as `uvicorn api.main:app`
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from rag.retrieve import Retriever
from rag import tutor as tutor_mod

STATE = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the embedding model + FAISS index ONCE at startup (the slow part),
    # then reuse it for every request.
    print("Loading retriever (model + index)...")
    STATE["retriever"] = Retriever()
    print("Ready.")
    yield
    STATE.clear()

app = FastAPI(title="AskDSA", lifespan=lifespan)

# Dev CORS: allow the extension's JS to call us. Tighten to the real origin later.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class TutorRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    level: int = Field(1, ge=1, le=4)
    url: Optional[str] = None

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/tutor")
def tutor_endpoint(req: TutorRequest):
    try:
        answer = tutor_mod.tutor(
            req.query, level=req.level, problem_url=req.url,
            retriever=STATE["retriever"],
        )
    except Exception as e:                     # LLM/network failure -> clean 502, not a crash
        raise HTTPException(status_code=502, detail=f"tutor failed: {e}")
    return {"answer": answer or "I couldn't generate a response — please try again."}