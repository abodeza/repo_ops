import os, time, json, requests
from dotenv import load_dotenv


load_dotenv()

AIML_API_KEY  = os.environ["AIML_API_KEY"]
AIML_API_BASE = os.getenv("AIML_API_BASE", "https://api.aimlapi.com/v1")
CHAT_MODEL    = os.getenv("CHAT_MODEL_ID", "openai/gpt-5-2025-08-07")

def _post(payload: dict, retries: int = 3, timeout: int = 60) -> dict:
    url = f"{AIML_API_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {AIML_API_KEY}",
        "Content-Type": "application/json",
    }
    for attempt in range(retries):
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        # simple backoff on transient errors
        if resp.status_code in (429, 500, 502, 503, 504) and attempt < retries - 1:
            time.sleep(1.5 * (attempt + 1))
            continue
        raise RuntimeError(f"AIML API error {resp.status_code}: {resp.text}")

def chat(messages: list[dict], temperature: float = 0.0) -> str:
    """
    messages = [{"role":"system"|"user"|"assistant", "content":"..."}]
    returns assistant text content
    """
    payload = {
        "model": CHAT_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    data = _post(payload)
    try:
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        raise RuntimeError(f"Unexpected AIML response: {json.dumps(data)[:500]}") from e
