import os, re, json, subprocess, tempfile
from pathlib import Path
from typing import List, Dict, Any, Iterable
from tiktoken import get_encoding
from .llm import chat

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

def _shallow_clone(repo_url: str, workdir: Path) -> Path:
    repo_dir = workdir / "repo"
    subprocess.check_call(["git","clone","--depth","1", repo_url, str(repo_dir)])
    return repo_dir

def _read_files(repo_dir: Path) -> Iterable[Dict[str,Any]]:
    seen: set[str] = set()
    for pat in DEFAULT_GLOB:
        for p in repo_dir.glob(pat):
            if not p.is_file(): 
                continue
            rel = p.relative_to(repo_dir).as_posix()
            if rel in seen:       # <— dedupe (README.md etc.)
                continue
            if BINARY_PAT.search(rel):
                continue
            seen.add(rel)
            try:
                txt = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if len(txt) > 200_000:
                continue
            yield {"path": rel, "text": txt, "size": len(txt)}

def _chunk(text: str, max_tokens=450) -> List[str]:
    toks = ENC.encode(text)
    return [ENC.decode(toks[i:i+max_tokens]) for i in range(0, len(toks), max_tokens)]

def build_index(repo_url: str, out_dir: Path) -> Dict[str, Any]:
    # Always write index INSIDE out_dir (per-repo)
    out_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        repo_dir = _shallow_clone(repo_url, Path(td))
        docs = list(_read_files(repo_dir))

    # sample preview to prove we're indexing the right repo
    sample_paths = [d["path"] for d in docs[:10]]
    (out_dir / "sample_paths.json").write_text(json.dumps(sample_paths, indent=2), encoding="utf-8")

    # LLM tag pass on top-N files (uses your AIML ChatGPT-5 client)
    tag_targets = sorted(docs, key=lambda d: d["size"], reverse=True)[:min(TOP_TAG_FILES, len(docs))]
    file_summaries = []
    for f in tag_targets:
        msg = [
            {"role":"system","content":"Label repository files for RAG. Output strict JSON."},
            {"role":"user","content":(
                f"Path: {f['path']}\n\nSample:\n{f['text'][:1600]}\n\n"
                "Return JSON keys: path, brief_summary (<=25 words), "
                "tags (<=5, e.g., data-loader, docker, training-loop, infra, api, tests), language."
            )},
        ]
        try:
            content = chat(msg, temperature=0.0)
            content = re.sub(r"^```json|```$", "", content.strip(), flags=re.M)
            js = json.loads(content)
            js["path"] = f["path"]
        except Exception:
            js = {"path": f["path"], "brief_summary":"", "tags": [], "language":"unknown"}
        file_summaries.append(js)

    (out_dir / "files.json").write_text(json.dumps(file_summaries, ensure_ascii=False, indent=2), encoding="utf-8")

    # Build BM25 corpus (ALL files → chunks)
    from rank_bm25 import BM25Okapi
    corpus, meta = [], []
    tag_map = {x["path"]: x for x in file_summaries}
    for f in docs:
        for idx, ch in enumerate(_chunk(f["text"])):
            corpus.append(ch)
            meta.append({
                "path": f["path"],
                "chunk_id": idx,
                "tags": tag_map.get(f["path"], {}).get("tags", []),
                "summary": tag_map.get(f["path"], {}).get("brief_summary",""),
            })
    tokenized = [c.lower().split() for c in corpus]
    bm25 = BM25Okapi(tokenized)

    # Persist inside out_dir
    (out_dir / "corpus.jsonl").write_text(
        "\n".join(json.dumps({"text":t, "meta":m}) for t,m in zip(corpus, meta)),
        encoding="utf-8"
    )
    (out_dir / "tokenized.json").write_text(json.dumps(tokenized), encoding="utf-8")

    # Repo map (nice to have)
    try:
        repo_map = chat(
            [
                {"role":"system","content":"Produce a concise architecture map. Output JSON only."},
                {"role":"user","content": json.dumps(file_summaries) + 
                 "\nSummarize the repo: components[], entry_points[], services[], dependencies[], deployment[]"}
            ],
            temperature=0.0
        )
        repo_map = re.sub(r"^```json|```$", "", repo_map.strip(), flags=re.M)
        (out_dir / "repo_map.json").write_text(repo_map, encoding="utf-8")
    except Exception:
        pass

    return {"n_files": len(docs), "n_chunks": len(corpus), "sample_paths": sample_paths}
