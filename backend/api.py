import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Literal
from .repo_indexer import build_index
from .retriever import Retriever

app = FastAPI(title="Repo-Ops API")
DATA_DIR = Path(os.getenv("INDEX_DIR", "data"))

class IngestRequest(BaseModel):
    repo_url: str

class AskRequest(BaseModel):
    query: str
    mode: Literal["explain","stack","run","deploy"] = "explain"

@app.post("/ingest")
def ingest(req: IngestRequest):
    DATA_DIR.mkdir(exist_ok=True, parents=True)
    try:
        stats = build_index(req.repo_url, DATA_DIR)
        return {"ok": True, **stats}
    except Exception as e:
        raise HTTPException(400, f"Ingest failed: {e}")

@app.post("/ask")
def ask(req: AskRequest):
    try:
        r = Retriever(DATA_DIR)
        out = r.answer(req.query, mode=req.mode)
        return {"ok": True, "answer": out}
    except Exception as e:
        raise HTTPException(400, f"Answer failed: {e}")
