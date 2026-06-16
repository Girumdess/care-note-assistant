"""PHI guardrails: detect and redact protected health information.

Two-layer detection:
  1. Deterministic regex for structured identifiers (SSN, phone, email, address, MRN)
  2. An LLM pass for contextual PHI (third-party names, locations, DOB, IDs)
"""
import re
import json
from .config import complete, JUDGE_MODEL

STRUCTURED_PATTERNS = {
    "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
    "PHONE": r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    "ADDRESS": r"\b\d{1,5}\s+[A-Za-z0-9.]+(?:\s+[A-Za-z0-9.]+){0,3}\s+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Way|Place|Pl)\b\.?",
    "MRN": r"\b(?:MRN|MR#|Medical Record(?:\s*(?:Number|No\.?|#))?)\s*:?\s*[A-Za-z0-9-]{3,}\b",
}

CONTEXTUAL_PROMPT = """You are a PHI (Protected Health Information) detector for home-care documentation.

This note is part of the record for the individual named: {client}. Their own first name is NOT something to flag.

Identify every span of text that is PHI belonging to ANYONE ELSE, or any direct identifier:
- Names of third parties (family, friends, other individuals served, staff)
- Street addresses or specific locations that could identify a person
- Organizations/facilities named in an identifying way
- Dates of birth, or an age paired with other identifiers
- Any account numbers, record numbers, or IDs

Return ONLY a JSON array. Each element: {{"text": "<exact substring from the note>", "type": "<THIRD_PARTY_NAME|LOCATION|ORGANIZATION|DATE_OF_BIRTH|IDENTIFIER>"}}. Return [] if none. No prose, no code fences."""

def detect_structured(text: str) -> list:
    findings = []
    for label, pattern in STRUCTURED_PATTERNS.items():
        for m in re.finditer(pattern, text):
            findings.append({"text": m.group(0), "type": label, "source": "regex"})
    return findings

def _parse_json_array(raw: str):
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*", "", raw).rsplit("```", 1)[0].strip()
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except Exception:
        return []

def detect_contextual(text: str, client_first_name=None) -> list:
    system = CONTEXTUAL_PROMPT.format(client=client_first_name or "[not specified]")
    resp = complete(JUDGE_MODEL, max_tokens=600, temperature=0,
                    system=system, messages=[{"role": "user", "content": text}])
    out = []
    for it in _parse_json_array(resp.content[0].text):
        if isinstance(it, dict) and it.get("text"):
            out.append({"text": it["text"], "type": it.get("type", "OTHER"), "source": "llm"})
    return out

def scan(text: str, client_first_name=None) -> list:
    findings = detect_structured(text) + detect_contextual(text, client_first_name)
    seen, unique = set(), []
    for f in findings:
        key = (f["text"], f["type"])
        if key in seen or f["text"] not in text:
            continue
        seen.add(key)
        unique.append(f)
    return unique

def redact(text: str, findings: list):
    applied = []
    for f in sorted(findings, key=lambda x: len(x["text"]), reverse=True):
        placeholder = f"[REDACTED: {f['type']}]"
        if f["text"] in text:
            text = text.replace(f["text"], placeholder)
            applied.append({**f, "placeholder": placeholder})
    return text, applied
