# Repo Ops

A small system that, given a GitHub repo URL, reads the repo, indexes its files for search, then uses GPT-5 with retrieval (RAG) to:
- Explain how to run it locally
- Show how to test it
- Propose how to deploy it
- Summarize what it does and its tech stack
- Answer relevant questions about the repo with citations to specific files and lines

## Features

- GitHub URL ingest with shallow clone
- Lightweight indexing using BM25 over chunked files
- Minimal LLM usage for file tagging and a repo map
- Evidence-backed answers with inline citations
- Mode-aware blueprints: Run, Test, Deploy, Understand, Tech Stack
- Clean separation between Streamlit frontend and FastAPI backend
- OpenAI-compatible provider (AI/ML API) using ChatGPT-5 only

## Architecture

- Frontend (Streamlit) calls the backend over HTTP
- Backend (FastAPI) performs cloning, indexing, retrieval, and LLM calls
- Storage is per repo under `data/<repo_id>/`
- All LLM calls are made to AI/ML API with the ChatGPT-5 model

```
[Streamlit UI]  ->  [FastAPI API]  ->  [Indexer + Retriever]  ->  [AI/ML API ChatGPT-5]
                           |                     |
                          disk                 disk
                       data/<repo_id>      data/<repo_id>
```

## Endpoints

- `POST /ingest`  
  Body: `{ "repo_url": "https://github.com/org/repo" }`  
  Returns: `{ ok, repo_id, source_url, modes, n_files, n_chunks, sample_paths }`  
  `modes` is a map like `{ run, test, deploy, understand, stack }`  
  `sample_paths` previews the first few indexed files to confirm the right repo

- `POST /blueprints`  
  Body: `{ "repo_id": "<id>", "mode": "run" | "test" | "deploy" | "understand" | "stack" }`  
  Returns: `{ ok, mode, answer }` where `answer` is a mode-specific plan with citations

- `POST /ask`  
  Body: `{ "repo_id": "<id>", "query": "<question>", "mode": "explain" | "stack" | "run" | "deploy" | "test" }`  
  Returns: `{ ok, answer }`

## Data layout

All artifacts for a given repository live under `data/<repo_id>/`:

```
data/
  <repo_id>/
    corpus.jsonl         # chunked text with metadata
    tokenized.json       # tokenized form for BM25
    files.json           # LLM-tagged top files (path, brief_summary, tags, language)
    sample_paths.json    # small preview to verify correct repo
    repo_map.json        # optional architecture map
```

## Configuration

Create `.env` in the project root:

```
AIML_API_KEY=YOUR_AIML_API_KEY
AIML_API_BASE=https://api.aimlapi.com/v1
CHAT_MODEL_ID=openai/gpt-5-2025-08-07

# Optional
INDEX_ROOT=data
TOP_TAG_FILES=20
KEEP_CLONE=0
```

Create `.streamlit/secrets.toml` for the frontend:

```
API_URL = "http://localhost:8000"
```

## Running locally

```
REM ----- Setup -----
py -3.10 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

REM Create .streamlit folder
mkdir .streamlit

REM Copy example files - [FILL IN]
copy .env.example .env
copy .streamlit\secrets.toml.example .streamlit\secrets.toml

REM Delete example files to keep things clean
del .env.example
del .streamlit\secrets.toml.example

REM ----- Run Backend -----
uvicorn backend.api:app --reload --port 8000

REM ----- Run Frontend -----
streamlit run streamlit_app.py
```

## Alternative shell setup (macOS and Linux)

```
python3.10 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

mkdir -p .streamlit
cp .env.example .env
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
rm .env.example .streamlit/secrets.toml.example

uvicorn backend.api:app --reload --port 8000
# new terminal
streamlit run streamlit_app.py
```

## How it works

1. Ingest  
   The backend clones the target repo with `git clone --depth 1` to a temp directory by default. It reads files by glob patterns, deduplicates common files, skips binaries and very large files, chunks text, then builds a BM25 index saved under `data/<repo_id>/`. It optionally tags the top N largest files using a single ChatGPT-5 pass per file and writes `sample_paths.json` for quick verification.

2. Retrieval and answers  
   For a blueprint or a direct question, the backend retrieves the top K chunks with BM25, builds a concise instruction, and passes the context to ChatGPT-5. The API returns an evidence-backed answer with inline citations that reference the retrieved paths and chunks.

## Modes

- Run: install and start commands for local development including likely entrypoints
- Test: how to run tests with pytest and coverage when applicable
- Deploy: minimal Docker and ASGI serving plan; if there is no Dockerfile, provide a minimal one and a single-service compose
- Understand: high level description of modules and data flow
- Tech Stack: frameworks, libraries, and configuration files with versions when available

## Provider
I used AI/ML API with the following config:
- API base: `https://api.aimlapi.com/v1`
- Model: `openai/gpt-5-2025-08-07`


## Project layout

```
.streamlit/
  secrets.toml.example  # Example minimum st.secrets needed  

backend/
  api.py                # FastAPI app and endpoints
  blueprint.py          # prebuilt prompts for Run, Test, Deploy, Understand, Stack
  detectors.py          # simple signals to set mode availability
  llm.py                # raw requests client for AI/ML API ChatGPT-5
  repo_indexer.py       # clone, read, chunk, tag, and write index artifacts
  retriever.py          # BM25 retrieval and answer generation

streamlit_app.py        # Streamlit UI
.env.example            # Example minimum env vars needed
.gitignore
requirements.txt
README.md
```

## Example usage

```
curl -s -X POST http://localhost:8000/ingest   -H "Content-Type: application/json"   -d '{"repo_url":"https://github.com/tiangolo/fastapi"}' | jq .

curl -s -X POST http://localhost:8000/blueprints   -H "Content-Type: application/json"   -d '{"repo_id":"fastapi","mode":"deploy"}' | jq .

curl -s -X POST http://localhost:8000/ask   -H "Content-Type: application/json"   -d '{"repo_id":"fastapi","mode":"run","query":"Give exact local run steps"}' | jq .
```

## License

This project is licensed under the [MIT License](https://github.com/abodeza/repo_ops/blob/main/LICENSE).
