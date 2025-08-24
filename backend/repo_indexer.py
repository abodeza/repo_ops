import os, re, json, subprocess, tempfile
from pathlib import Path
from typing import List, Dict, Any, Iterable
from .llm import chat
from tiktoken import get_encoding

ENC = get_encoding("cl100k_base")
DEFAULT_GLOB = [
    "**/*.py","**/*.ipynb","**/*.md","**/*.txt",
    "**/*.js","**/*.ts","**/*.tsx","**/*.jsx",
    "**/*.go","**/*.rs","**/*.java","**/*.scala","**/*.kt",
    "**/*.c","**/*.cpp","**/*.h","**/*.hpp",
    "**/*.yaml","**/*.yml","**/*.toml","**/*.ini",
    "**/Dockerfile","**/Makefile","**/requirements.txt","**/pyproject.toml",
    "**/package.json","**/README*","**/LICENSE*"
]
BINARY_PAT = re.compile(r"\.(png|jpg|jpeg|gif|pdf|mp4|zip|tar|gz|tgz|7z|exe|dylib|so|bin)$", re.I)
TOP_TAG_FILES = int(os.getenv("TOP_TAG_FILES", "20"))

def _shallow_clone(repo_url:str, workdir:Path)->Path:
    repo_dir = workdir / "repo"
    subprocess.check_call(["git","clone","--depth","1",repo_url,str(repo_dir)])
    return repo_dir

def _read_files(repo_dir:Path)->Iterable[Dict[str,Any]]:
    for pat in DEFAULT_GLOB:
        for p in repo_dir.glob(pat):
            if not p.is_file():
                continue
            rel = p.relative_to(repo_dir).as_posix()
            if BINARY_PAT.search(rel):
                continue
            try:
                txt = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if len(txt) > 200_000:
                continue
            yield {"path": rel, "text": txt, "size": len(txt)}

def _chunk(text:str, max_tokens=450)->List[str]:
    toks = ENC.encode(text)
    chunks=[]
    for i in range(0, len(toks), max_tokens):
        sub = toks[i:i+max_tokens]
        chunks.append(ENC.decode(sub))
    return chunks

def _tag_file(path: str, sample: str) -> Dict[str,Any]:
    msg = [
        {"role":"system","content":"Label repository files for RAG. Output strict JSON."},
        {"role":"user","content":(
            f"Path: {path}\n\nSample:\n{sample[:1200]}\n\n"
            "Return JSON with keys: path, brief_summary (<=25 words), "
            "tags (<=5, e.g., data-loader, docker, training-loop, infra, api, tests), language."
        )},
    ]
    try:
        content = chat(msg, temperature=0.0)
        content = re.sub(r"^```json|```$", "", content.strip(), flags=re.M)
        data = json.loads(content)
        data["path"] = path
        return data
    except Exception:
        return {"path": path, "brief_summary":"", "tags": [], "language":"unknown"}

def build_index(repo_url:str, out_dir:Path)->Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        repo_dir = _shallow_clone(repo_url, Path(td))
        docs = list(_read_files(repo_dir))

    # Pick top-N "central" files by size (simple heuristic)
    docs_sorted = sorted(docs, key=lambda d: d["size"], reverse=True)
    tag_targets = docs_sorted[:min(TOP_TAG_FILES, len(docs_sorted))]

    file_summaries = []
    for f in tag_targets:
        file_summaries.append(_tag_file(f["path"], f["text"][:4000]))

    # Persist lightweight tags for retriever
    (out_dir / "files.json").write_text(json.dumps(file_summaries, ensure_ascii=False, indent=2), encoding="utf-8")

    # Build BM25 corpus
    from rank_bm25 import BM25Okapi
    corpus, meta = [], []
    tag_map = {x["path"]: x for x in file_summaries}
    for f in docs:
        chunks = _chunk(f["text"])
        for idx, ch in enumerate(chunks):
            corpus.append(ch)
            meta.append({
                "path": f["path"],
                "chunk_id": idx,
                "tags": tag_map.get(f["path"], {}).get("tags", []),
                "summary": tag_map.get(f["path"], {}).get("brief_summary",""),
            })
    tokenized = [c.lower().split() for c in corpus]
    bm25 = BM25Okapi(tokenized)

    # Save index
    (out_dir / "corpus.jsonl").write_text(
        "\n".join(json.dumps({"text":t, "meta":m}) for t,m in zip(corpus, meta)), encoding="utf-8"
    )
    (out_dir / "tokenized.json").write_text(json.dumps(tokenized), encoding="utf-8")

    # Repo map (single LLM call)
    map_msg = [
        {"role":"system","content":"Produce a concise architecture map. Output JSON only."},
        {"role":"user","content": json.dumps(file_summaries) + 
         "\nSummarize the repo: components[], entry_points[], services[], dependencies[], deployment[]"}
    ]
    repo_map = chat(map_msg, temperature=0.0)
    repo_map = re.sub(r"^```json|```$", "", repo_map.strip(), flags=re.M)
    (out_dir / "repo_map.json").write_text(repo_map, encoding="utf-8")

    return {"n_files": len(docs), "n_chunks": len(corpus)}
