# Repo Ops
---
## Description
A small system that, given a GitHub repo URL, reads the repo, indexes its files for search, then uses GPT-5 with retrieval (RAG) to: 
* Explain how to run it locally, 
* Show how to test it, 
* Propose how to deploy it, 
* Summarize what it does and its tech stack, 
* And answers relevant questions about the repo with citations to exact file/lines.

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