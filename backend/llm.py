"""Thin client for a local Ollama server.

Ollama runs open-source LLMs on your own machine (no API key, no cost).
Default model: llama3.2:3b  ->  install with `ollama pull llama3.2:3b`
"""
import json
import os
import re

import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "180"))


class LLMError(RuntimeError):
    pass


def health():
    """Return (ok, message) describing whether Ollama and the model are available."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        r.raise_for_status()
    except requests.RequestException:
        return False, f"Ollama is not running at {OLLAMA_URL}. Start it with `ollama serve`."
    names = [m.get("name", "") for m in r.json().get("models", [])]
    base = OLLAMA_MODEL.split(":")[0]
    if not any(n == OLLAMA_MODEL or n.startswith(base + ":") for n in names):
        return False, f"Model '{OLLAMA_MODEL}' is not installed. Run `ollama pull {OLLAMA_MODEL}`."
    return True, f"Connected to Ollama ({OLLAMA_MODEL})"


def _extract_json(text):
    """Parse JSON from a model reply, tolerating code fences or extra prose."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}|\[.*\]", text, flags=re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def chat_json(system, user, temperature=0.4, retries=2):
    """Send a chat request and return parsed JSON. Retries on malformed output."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "format": "json",
        "stream": False,
        "options": {"temperature": temperature},
    }
    last_err = None
    for _ in range(retries + 1):
        try:
            r = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=TIMEOUT)
            r.raise_for_status()
            content = r.json()["message"]["content"]
            return _extract_json(content)
        except requests.RequestException as e:
            raise LLMError(f"Could not reach Ollama: {e}") from e
        except (KeyError, ValueError) as e:
            last_err = e
    raise LLMError(f"Model returned invalid JSON: {last_err}")
