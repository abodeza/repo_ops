import streamlit as st
import requests

API = st.secrets.get("API_URL","http://localhost:8000")

st.set_page_config(page_title="RepoOps Copilot", layout="wide")
st.title("RepoOps Copilot")

with st.sidebar:
    repo_url = st.text_input("GitHub Repo URL", placeholder="https://github.com/user/repo")
    if st.button("Ingest", use_container_width=True) and repo_url:
        r = requests.post(f"{API}/ingest", json={"repo_url": repo_url})
        if r.ok:
            st.session_state["repo"] = r.json()
            st.success(f"Ingested: {st.session_state['repo']['repo_id']}")
        else:
            st.error(r.text)

if "repo" not in st.session_state:
    st.info("Enter a GitHub repo URL and click Ingest.")
    st.stop()

repo_id = st.session_state["repo"]["repo_id"]
modes = st.session_state["repo"]["modes"]
tabs = st.tabs(["Run","Test","Deploy","Understand","Stack","Chat"])

def blueprint(mode, tab):
    with tab:
        if not modes.get(mode, True):
            st.warning(f"{mode} signals not detected; still attempting.")
        if st.button(f"Generate {mode.title()} Plan", key=mode):
            r = requests.post(f"{API}/blueprints", json={"repo_id": repo_id, "mode": mode})
            if r.ok:
                st.code(r.json()["answer"])
            else:
                st.error(r.text)

blueprint("run", tabs[0])
blueprint("test", tabs[1])
blueprint("deploy", tabs[2])

with tabs[3]:
    if st.button("Explain Repo"):
        r = requests.post(f"{API}/blueprints", json={"repo_id": repo_id, "mode":"understand"})
        st.code(r.json()["answer"])

with tabs[4]:
    if st.button("Show Tech Stack"):
        r = requests.post(f"{API}/blueprints", json={"repo_id": repo_id, "mode":"stack"})
        st.code(r.json()["answer"])

with tabs[5]:
    q = st.text_area("Ask a question about the repo")
    if st.button("Ask"):
        r = requests.post(f"{API}/chat", json={"repo_id": repo_id, "question": q})
        if r.ok:
            data = r.json()
            st.markdown(data["answer"])
            with st.expander("Citations"):
                for c in data["citations"]:
                    st.write(f"{c['path']}:{c['start']}-{c['end']}")
        else:
            st.error(r.text)
