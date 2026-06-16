"""End-to-end: rough notes -> generated documentation -> PHI-guarded note."""
from .generator import generate_note
from .guardrails import scan, redact

def process_note(rough_notes: str, client_first_name=None) -> dict:
    generated = generate_note(rough_notes, client_first_name)
    findings = scan(generated, client_first_name)
    redacted, applied = redact(generated, findings)
    return {
        "input": rough_notes,
        "generated": generated,
        "redacted": redacted,
        "findings": applied,
        "phi_count": len(applied),
    }
