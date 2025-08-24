import json
from pathlib import Path
from typing import Dict

def detect_modes(repo_dir: Path) -> Dict[str, bool]:
    """
    Heuristic mode detection using files.json (LLM tags) and filenames.
    Returns keys expected by the frontend: run, test, deploy, understand, stack.
    """
    files_json = repo_dir / "files.json"
    tags_by_path = {}
    if files_json.exists():
        try:
            arr = json.loads(files_json.read_text(encoding="utf-8"))
            for row in arr:
                tags_by_path[row.get("path","")] = set(
                    (row.get("tags") or [])
                )
        except Exception:
            pass

    has_tests = False
    has_docker = False
    has_fastapi_or_uvicorn = False

    # Scan tags and filenames (cheap & robust)
    for p, tags in tags_by_path.items():
        pl = p.lower()
        if "test" in pl or "tests/" in pl or "pytest" in tags:
            has_tests = True
        if "docker" in tags or "dockerfile" in pl:
            has_docker = True
        if "fastapi" in tags or "uvicorn" in tags or "fastapi" in pl or "uvicorn" in pl:
            has_fastapi_or_uvicorn = True

    # Fallback: a quick filename pass if files.json is absent/sparse
    if not files_json.exists() or not tags_by_path:
        for p in (repo_dir.parent / repo_dir.name).rglob("*"):
            if not p.is_file(): 
                continue
            pl = p.name.lower()
            if pl.startswith("dockerfile") or pl == "dockerfile":
                has_docker = True
            if "test" in pl:
                has_tests = True
            if pl.endswith(".py"):
                txt = ""
                try:
                    txt = p.read_text(encoding="utf-8", errors="ignore")[:8000]
                except Exception:
                    pass
                low = txt.lower()
                if "fastapi(" in low or "uvicorn" in low:
                    has_fastapi_or_uvicorn = True

    modes = {
        "run": True,                   # always possible to propose local run steps
        "test": has_tests,
        "deploy": has_docker or has_fastapi_or_uvicorn,
        "understand": True,
        "stack": True
    }
    return modes
