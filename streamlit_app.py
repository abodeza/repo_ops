import os
import requests
import streamlit as st

# ---- Config ----
st.set_page_config(page_title="Repo-Ops — RAG for ML Repos", page_icon="🛠️", layout="wide")

# API base (prefer Streamlit secrets; fallback to env; then localhost)
API_BASE = st.secrets.get("API_URL", os.getenv("API_URL", "http://localhost:8000"))

# ---- Helpers ----
def api_post(path: str, payload: dict):
    url = f"{API_BASE}{path}"
    try:
        r = requests.post(url, json=payload, timeout=120)
        if r.ok:
            return r.json(), None
        return None, f"{r.status_code}: {r.text}"
    except Exception as e:
        return None, str(e)

def show_modes(modes: dict):
    # Pretty chips; gray for False
    cols = st.columns(5)
    labels = [
        ("run", "▶️ Run"),
        ("test", "✅ Test"),
        ("deploy", "🚀 Deploy"),
        ("understand", "🧠 Understand"),
        ("stack", "🧩 Tech Stack"),
    ]
    for (key, label), col in zip(labels, cols):
        active = modes.get(key, True)
        style = "background-color:#16a34a;color:white" if active else "background-color:#a3a3a3;color:white"
        with col:
            st.markdown(
                f"<div style='padding:6px 10px;border-radius:12px;display:inline-block;{style}'>{label}</div>",
                unsafe_allow_html=True,
            )

def blueprint_block(tab, mode_key: str, label: str, repo_id: str, enabled: bool):
    with tab:
        st.caption(f"{label} plan generated from the repo context.")
        if st.button(f"Generate {label}", key=f"btn_{mode_key}", disabled=not enabled, use_container_width=True):
            with st.spinner("Generating…"):
                data, err = api_post("/blueprints", {"repo_id": repo_id, "mode": mode_key})
            if err:
                st.error(err)
            else:
                st.code(data.get("answer", ""), language="markdown")

# ---- Sidebar: Ingest ----
st.title("Repo-Ops — GitHub RAG for ML Engineers")

with st.sidebar:
    st.header("1) Ingest a GitHub repo")
    repo_url = st.text_input("GitHub URL", placeholder="https://github.com/org/repo")
    if st.button("Ingest / Rebuild Index", use_container_width=True):
        if not repo_url.strip():
            st.error("Please paste a valid GitHub repository URL.")
        else:
            with st.spinner("Cloning & indexing…"):
                data, err = api_post("/ingest", {"repo_url": repo_url.strip()})
            if err:
                st.error(err)
            else:
                st.session_state["repo"] = data
                st.success(f"✅ Ingested: {data.get('repo_id','(unknown)')}")
                st.toast("Index built", icon="✅")

# ---- Main: require an ingested repo ----
if "repo" not in st.session_state:
    st.info("Paste a GitHub repo URL in the sidebar and click **Ingest / Rebuild Index**.")
    st.stop()

repo = st.session_state["repo"]
repo_id = repo.get("repo_id", "repo")
modes = repo.get("modes", {"run": True, "test": True, "deploy": True, "understand": True, "stack": True})
n_files = repo.get("n_files", 0)
n_chunks = repo.get("n_chunks", 0)

# Top summary row
colA, colB, colC = st.columns([2, 1, 1])
with colA:
    st.subheader(f"📦 Repository: `{repo_id}`")
with colB:
    st.metric("Files Indexed", n_files)
with colC:
    st.metric("Chunks", n_chunks)

st.markdown("#### Capabilities detected")
show_modes(modes)
st.divider()

# ---- Tabs ----
tabs = st.tabs(["Run", "Test", "Deploy", "Understand", "Tech Stack", "Chat"])

# Run / Test / Deploy / Understand / Stack blueprints
blueprint_block(tabs[0], "run", "Run Locally", repo_id, modes.get("run", True))
blueprint_block(tabs[1], "test", "Test Suite", repo_id, modes.get("test", True))
blueprint_block(tabs[2], "deploy", "Deploy (Docker/ASGI)", repo_id, modes.get("deploy", True))

with tabs[3]:
    st.caption("High-level explanation of what this repository does.")
    if st.button("Explain Repository", use_container_width=True):
        with st.spinner("Generating…"):
            data, err = api_post("/blueprints", {"repo_id": repo_id, "mode": "understand"})
        if err:
            st.error(err)
        else:
            st.code(data.get("answer", ""), language="markdown")

with tabs[4]:
    st.caption("List the key frameworks, libraries, and config files with evidence.")
    if st.button("Show Tech Stack", use_container_width=True):
        with st.spinner("Generating…"):
            data, err = api_post("/blueprints", {"repo_id": repo_id, "mode": "stack"})
        if err:
            st.error(err)
        else:
            st.code(data.get("answer", ""), language="markdown")

# Chat tab
with tabs[5]:
    st.caption("Ask anything about this repo. Choose an intent to steer the answer.")
    chat_col1, chat_col2 = st.columns([3, 1])
    with chat_col1:
        q = st.text_area("Your question", placeholder="e.g., Where is the training loop defined? How do I enable GPU?")
    with chat_col2:
        intent = st.selectbox(
            "Intent",
            options=["explain", "run", "deploy", "stack", "test"],
            index=0,
            help="This guides retrieval & prompting.",
        )
    if st.button("Ask", type="primary", use_container_width=True):
        if not q.strip():
            st.error("Please enter a question.")
        else:
            with st.spinner("Thinking…"):
                data, err = api_post("/ask", {"repo_id": repo_id, "query": q.strip(), "mode": intent})
            if err:
                st.error(err)
            else:
                st.markdown(data.get("answer", ""))

# Footer tip
st.markdown(
    "<hr/><small>Set your backend URL via <code>st.secrets</code> "
    "(<code>.streamlit/secrets.toml</code> → <code>API_URL</code>) or the <code>API_URL</code> env var. "
    "Default: <code>http://localhost:8000</code>.</small>",
    unsafe_allow_html=True,
)
