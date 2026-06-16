"""Eval metrics: PHI-leakage detection and LLM-judge quality scoring."""
import re
import json
from care_assistant.config import complete, JUDGE_MODEL

def phi_leaks(final_text: str, phi_items: list) -> list:
    """Return PHI strings that survived (still appear) in the final output."""
    leaked, low = [], final_text.lower()
    for item in phi_items:
        if not item:
            continue
        if re.fullmatch(r"[A-Za-z .'-]+", item):  # name-like -> word boundary
            if re.search(r"\b" + re.escape(item.lower()) + r"\b", low):
                leaked.append(item)
        else:  # has digits/punctuation -> substring
            if item.lower() in low:
                leaked.append(item)
    return leaked

JUDGE_SYSTEM = """You are a clinical documentation quality auditor for home-care progress notes.
Score the FINAL note on a 1-5 integer scale per dimension:
- objectivity: only observable behavior; no interpretation, labels, or judgment
- completeness: captures supports provided, the individual's response, and any events
- professional_tone: person-first, respectful, appropriate clinical register
- no_fabrication: nothing stated that isn't supported by the source notes
Return ONLY JSON: {"objectivity": n, "completeness": n, "professional_tone": n, "no_fabrication": n}"""

def _parse_obj(raw: str):
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*", "", raw).rsplit("```", 1)[0].strip()
    try:
        return json.loads(raw)
    except Exception:
        return {}

def judge_quality(source_note: str, final_note: str) -> dict:
    user = f"SOURCE rough notes:\n{source_note}\n\nFINAL note:\n{final_note}\n\nScore it."
    resp = complete(JUDGE_MODEL, max_tokens=200, temperature=0,
                    system=JUDGE_SYSTEM, messages=[{"role": "user", "content": user}])
    scores = _parse_obj(resp.content[0].text)
    dims = ["objectivity", "completeness", "professional_tone", "no_fabrication"]
    clean = {d: float(scores.get(d, 0) or 0) for d in dims}
    clean["overall"] = round(sum(clean.values()) / len(dims), 2)
    return clean
