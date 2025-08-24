import os, requests, streamlit as st

st.set_page_config(page_title="Repo-Ops", page_icon="🛠️", layout="wide")
st.title("Repo-Ops — GitHub RAG for ML Engineers")

api = os.getenv("API_URL", "http://localhost:8000")

with st.sidebar:
    st.header("1) Ingest a GitHub repo")
    repo_url = st.text_input("GitHub URL", placeholder="https://github.com/org/repo")
    if st.button("Ingest / Rebuild Index", use_container_width=True):
        with st.spinner("Cloning & indexing..."):
            r = requests.post(f"{api}/ingest", json={"repo_url": repo_url})
        if r.ok and r.json().get("ok"):
            st.success(f"Ingested ✅  files:{r.json()['n_files']} chunks:{r.json()['n_chunks']}")
        else:
            st.error(f"Failed: {r.text}")

mode = st.radio("Mode", ["explain","stack","run","deploy"], horizontal=True)
q = st.text_input("Your question", placeholder="Explain the training loop; or: give a deploy plan to GCP Cloud Run")

if st.button("Ask", type="primary"):
    with st.spinner("Thinking with ChatGPT-5..."):
        r = requests.post(f"{api}/ask", json={"query": q, "mode": mode})
    if r.ok and r.json().get("ok"):
        st.markdown(r.json()["answer"])
    else:
        st.error(r.text)
