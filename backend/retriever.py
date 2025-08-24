import json, os
from pathlib import Path
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
from .llm import chat

DATA_DIR = Path(os.getenv("INDEX_DIR", "data"))

class Retriever:
    def __init__(self, data_dir:Path=DATA_DIR):
        self.data_dir = data_dir
        self._load()

    def _load(self):
        self.corpus = []
        self.meta = []
        with (self.data_dir / "corpus.jsonl").open("r", encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                self.corpus.append(row["text"])
                self.meta.append(row["meta"])
        tokenized = json.loads((self.data_dir / "tokenized.json").read_text(encoding="utf-8"))
        self.bm25 = BM25Okapi(tokenized)

    def topk(self, query:str, k:int=12)->List[Dict[str,Any]]:
        scores = self.bm25.get_scores(query.lower().split())
        idxs = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [{"text": self.corpus[i], "meta": self.meta[i], "score": float(scores[i])} for i in idxs]

    def answer(self, query:str, mode:str="explain", k:int=12)->str:
        ctx = self.topk(query, k=k)
        instruction = {
            "explain": "Explain briefly with evidence; cite paths inline like [path:chunk].",
            "stack":   "List frameworks/libs & versions from evidence.",
            "run":     "Give exact local run steps (install, env, entrypoint).",
            "deploy":  "Propose minimal Docker+service plan. Call out secrets and ports.",
        }[mode]
        msgs = [
            {"role":"system","content":"You are Repo-Ops: concise, precise, evidence-backed. If unsure, say so."},
            {"role":"user","content":
                f"{instruction}\n\nUser query: {query}\n\nContext:\n" +
                "\n\n".join(f"[{i}] PATH={c['meta']['path']} TAGS={c['meta'].get('tags',[])}\n{c['text']}"
                            for i,c in enumerate(ctx))
            }
        ]
        return chat(msgs, temperature=0.1)
