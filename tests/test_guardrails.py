"""Offline tests for the deterministic parts of the PHI guardrail.

These run without an API key: they cover the regex layer, redaction,
and the JSON parsing used for the LLM layer's output. The LLM layer
itself is measured by the eval harness in evals/.
"""
from care_assistant.guardrails import detect_structured, redact, _parse_json_array, scan
from care_assistant import guardrails


def types_found(text):
    return {f["type"] for f in detect_structured(text)}


def test_ssn():
    assert "SSN" in types_found("SSN on file is 123-45-6789.")


def test_phone_formats():
    for phone in ["503-555-0142", "(503) 555-0142", "503.555.0142", "+1 503 555 0142"]:
        assert "PHONE" in types_found(f"Call her at {phone} tomorrow."), phone


def test_email():
    assert "EMAIL" in types_found("Sent the update to jane.doe@example.org")


def test_street_address():
    assert "ADDRESS" in types_found("Picked him up at 1420 Maple Street after lunch.")


def test_record_number():
    assert "MRN" in types_found("Chart MRN: A55-1234 reviewed.")


def test_clean_note_has_no_findings():
    note = ("Client ate 75% of breakfast, walked twice in the hallway with staff, "
            "and reported no pain. Took evening medications as scheduled.")
    assert detect_structured(note) == []


def test_redact_replaces_every_finding():
    text = "SSN 123-45-6789, phone 503-555-0142."
    out, applied = redact(text, detect_structured(text))
    assert "123-45-6789" not in out
    assert "503-555-0142" not in out
    assert "[REDACTED: SSN]" in out
    assert len(applied) == 2


def test_redact_longest_first():
    findings = [{"text": "Maria", "type": "THIRD_PARTY_NAME"},
                {"text": "Maria Lopez", "type": "THIRD_PARTY_NAME"}]
    out, _ = redact("Sister Maria Lopez visited.", findings)
    assert out == "Sister [REDACTED: THIRD_PARTY_NAME] visited."


def test_parse_json_array_handles_fences_and_junk():
    assert _parse_json_array('```json\n[{"text": "Bob", "type": "X"}]\n```') == [{"text": "Bob", "type": "X"}]
    assert _parse_json_array("not json") == []
    assert _parse_json_array('{"text": "Bob"}') == []


def test_scan_drops_llm_spans_not_in_text(monkeypatch):
    fake = [{"text": "Bob", "type": "THIRD_PARTY_NAME", "source": "llm"},
            {"text": "Invented Name", "type": "THIRD_PARTY_NAME", "source": "llm"}]
    monkeypatch.setattr(guardrails, "detect_contextual", lambda text, client=None: fake)
    found = scan("Bob called at 503-555-0142.", "Ann")
    texts = {f["text"] for f in found}
    assert texts == {"Bob", "503-555-0142"}
