"""Configuration, shared Anthropic client, and usage/cost tracking."""
import os
import threading
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

GENERATION_MODEL = "claude-sonnet-4-6"
JUDGE_MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024
TEMPERATURE = 0.2

PRICING = {
    "claude-sonnet-4-6": {"in": 3.0e-6, "out": 15.0e-6},
    "claude-haiku-4-5-20251001": {"in": 1.0e-6, "out": 5.0e-6},
}

_client = None
_lock = threading.Lock()
_usage = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}

def set_api_key(key: str):
    """Override the API key at runtime (used by the 'bring your own key' UI)."""
    global ANTHROPIC_API_KEY, _client
    ANTHROPIC_API_KEY = key
    _client = None

def get_client():
    import anthropic
    global _client
    if _client is None:
        if not ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY not set. Add a key in the app, or copy .env.example to .env.")
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client

def complete(model, **kwargs):
    """Call the API and record token usage + estimated cost (thread-safe)."""
    resp = get_client().messages.create(model=model, **kwargs)
    u = resp.usage
    price = PRICING.get(model, {"in": 0.0, "out": 0.0})
    with _lock:
        _usage["calls"] += 1
        _usage["input_tokens"] += u.input_tokens
        _usage["output_tokens"] += u.output_tokens
        _usage["cost_usd"] += u.input_tokens * price["in"] + u.output_tokens * price["out"]
    return resp

def get_usage():
    with _lock:
        return dict(_usage)

def reset_usage():
    with _lock:
        _usage.update(calls=0, input_tokens=0, output_tokens=0, cost_usd=0.0)
