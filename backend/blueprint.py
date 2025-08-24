from typing import Literal
from .retriever import Retriever

BlueprintMode = Literal["run","test","deploy","understand","stack"]

PROMPTS = {
    "run": (
        "Give exact local run steps: installation (pip/poetry/conda), "
        "env variables if evident, and the main entrypoint command. "
        "If alternatives exist, propose both. Cite file paths inline like [path:chunk]."
    ),
    "test": (
        "How to run the tests with pytest (and coverage if present). "
        "Show minimal commands. Cite evidence with [path:chunk]."
    ),
    "deploy": (
        "Propose a minimal Docker + uvicorn/ASGI deployment plan. "
        "If a Dockerfile exists, show build/run commands. If not, provide a minimal Dockerfile "
        "and a one-service docker-compose.yml exposing the correct port. "
        "Call out secrets/ports. Cite evidence with [path:chunk]."
    ),
    "understand": (
        "Explain briefly what this repo does: main modules, data flow, and entry points "
        "in ≤10 bullets. Cite evidence with [path:chunk]."
    ),
    "stack": (
        "List the main frameworks, ML libs, serving libs, data deps, and config files. "
        "Include versions when available (requirements/pyproject). Cite with [path:chunk]."
    ),
}

def generate_blueprint(repo_dir, mode: BlueprintMode) -> str:
    r = Retriever(repo_dir)
    instruction = PROMPTS[mode]
    # We pass the instruction as the 'query' so the model uses retrieved context
    return r.answer(query=instruction, mode={
        "understand": "explain"  # map to retriever's internal name
    }.get(mode, mode))
