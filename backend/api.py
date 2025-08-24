import os, re
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Literal
from .repo_indexer import build_index
from .retriever import Retriever
from .detectors import detect_modes
from .blueprint import generate_blueprint

app = FastAPI(title="Repo-Ops API")
DATA_ROOT = Path(os.getenv("INDEX_ROOT", "data"))

class IngestRequest(BaseModel):
    repo_url: str

class AskRequest(BaseModel):
    repo_id: str
    query: str
    mode: Literal["explain","stack","run","deploy","test"] = "explain"

class BlueprintRequest(BaseModel):
    repo_id: str
    mode: Literal["run","test","deploy","understand","stack"]

@app.post("/ingest")
def ingest(req: IngestRequest):
    DATA_ROOT.mkdir(parents=True, exist_ok=True)

    # Derive a friendly repo_id from URL last segment
    repo_id = req.repo_url.rstrip("/").split("/")[-1]
    if repo_id.endswith(".git"):
        repo_id = repo_id[:-4]

    repo_dir = DATA_ROOT / repo_id
    try:
        stats = build_index(req.repo_url, repo_dir)  # writes into data/<repo_id>/*
        modes = detect_modes(repo_dir)
        return {"ok": True, "repo_id": repo_id, "modes": modes, **stats}
    except Exception as e:
        raise HTTPException(400, f"Ingest failed: {e}")

@app.post("/blueprints")
def blueprints(req: BlueprintRequest):
    repo_dir = DATA_ROOT / req.repo_id
    if not repo_dir.exists():
        raise HTTPException(404, f"Unknown repo_id: {req.repo_id}")
    try:
        answer = generate_blueprint(repo_dir, req.mode)
        return {"ok": True, "mode": req.mode, "answer": answer}
    except Exception as e:
        raise HTTPException(400, f"Blueprint failed: {e}")

@app.post("/ask")
def ask(req: AskRequest):
    repo_dir = DATA_ROOT / req.repo_id
    if not repo_dir.exists():
        raise HTTPException(404, f"Unknown repo_id: {req.repo_id}")
    try:
        r = Retriever(repo_dir)
        out = r.answer(req.query, mode=req.mode)
        return {"ok": True, "answer": out}
    except Exception as e:
        raise HTTPException(400, f"Answer failed: {e}")
