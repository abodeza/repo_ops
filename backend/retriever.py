import json, os
from pathlib import Path
from typing import List, Dict, Any, Literal
from rank_bm25 import BM25Okapi
from .llm import chat

class Retriever:
    def __init__(self, repo_dir: Path):
        """
        repo_dir points to data/<repo_id>
        Requires corpus.jsonl and tokenized.json
        """
        self.repo_dir = Path(repo_dir)
        self._load()

    def _load(self):
        corpus_path = self.repo_dir / "corpus.jsonl"
        tok_path    = self.repo_dir / "tokenized.json"
        if not corpus_path.exists() or not tok_path.exists():
            raise FileNotFoundError(f"Missing index files in {self.repo_dir}")
        self.corpus = []
        self.meta = []
        with corpus_path.open("r", encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                self.corpus.append(row["text"])
                self.meta.append(row["meta"])
        tokenized = json.loads(tok_path.read_text(encoding="utf-8"))
        self.bm25 = BM25Okapi(tokenized)

    def topk(self, query:str, k:int=12)->List[Dict[str,Any]]:
        scores = self.bm25.get_scores(query.lower().split())
        idxs = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [{"text": self.corpus[i], "meta": self.meta[i], "score": float(scores[i])} for i in idxs]

    def answer(self, query:str, mode: Literal["explain","stack","run","deploy","test"]="explain", k:int=12)->str:
        ctx = self.topk(query, k=k)
        instruction = {
            "explain": "Explain concisely with evidence; cite paths inline like [path:chunk].",
            "stack":   "List frameworks/libs & versions from evidence.",
            "run":     "Give exact local run steps (install, env, entrypoint).",
            "deploy":  "Propose minimal Docker+service plan. Call out secrets and ports.",
            "test":    "Show how to run the tests (pytest/coverage) with minimal commands."
        }[mode]
        msgs = [
            {"role":"system","content":"You are Repo-Ops: concise, precise, evidence-backed. If unsure, give 2 options."},
            {"role":"user","content":
                f"{instruction}\n\nUser intent: {mode}\n\nContext:\n" +
                "\n\n".join(f"[{i}] PATH={c['meta']['path']} TAGS={c['meta'].get('tags',[])}\n{c['text']}"
                            for i,c in enumerate(ctx))
            }
        ]
        return chat(msgs, temperature=0.1)
