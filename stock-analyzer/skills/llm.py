"""
LLM Client — Ollama
Wraps the local Ollama API so any agent can call Qwen for reasoning.
Ollama must be running at http://localhost:11434
"""

import json
import urllib.request
import urllib.error

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "qwen2.5:7b"


def call(prompt: str, model: str = DEFAULT_MODEL, temperature: float = 0.3) -> str:
    """
    Send a prompt to the local Ollama model and return the response text.
    temperature: 0.0–1.0. Lower = more focused/consistent. 0.3 is good for analysis.
    """
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": 600,
        }
    }).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read().decode("utf-8")
        data = json.loads(raw)
        return data.get("response", "").strip()
    except urllib.error.URLError as e:
        raise ConnectionError(
            f"Cannot reach Ollama at {OLLAMA_URL}.\n"
            f"Make sure Ollama is running: open a terminal and run 'ollama serve'\n"
            f"Original error: {e}"
        )


def list_models() -> list:
    """Return list of models available in this Ollama instance."""
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def check_model(model: str) -> tuple[bool, str]:
    """
    Check if a model is available. Returns (available, suggestion).
    """
    available = list_models()
    if not available:
        return False, "Ollama is not running or not reachable"
    if model in available:
        return True, model
    # Try fuzzy match — e.g. 'qwen2.5:7b' matches 'qwen2.5:7b-instruct-q4_K_M'
    for m in available:
        if model.split(":")[0] in m:
            return True, m
    return False, f"Model '{model}' not found. Available: {', '.join(available)}"


if __name__ == "__main__":
    print("Available models:", list_models())
    print("\nTest call...")
    response = call("Say hello in one sentence.")
    print("Response:", response)
