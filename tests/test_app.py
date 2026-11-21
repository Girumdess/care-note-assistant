"""Smoke tests for the Streamlit app in browse mode (no API key).

These check that a first-time visitor sees every tab render without errors,
that recorded examples work offline, and that each visitor's records are
kept separate.
"""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture
def app(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    assert not at.exception, at.exception
    return at


def test_every_tab_renders(app):
    labels = [t.label for t in app.tabs]
    assert labels == ["Write a note", "Weekly summary", "Client history",
                      "Health overview", "How it's tested", "About"]


def test_recorded_examples_work_without_a_key(app):
    box = [s for s in app.selectbox if s.label == "Example"][0]
    for i in range(len(box.options)):
        box.select_index(i).run()
        assert not app.exception, app.exception


def test_each_client_renders(app):
    clients = [s for s in app.selectbox if s.label == "Client"][0]
    for i in range(len(clients.options)):
        clients.select_index(i).run()
        assert not app.exception, app.exception


def test_live_buttons_are_disabled_without_a_key(app):
    app.segmented_control(key="note_mode").set_value("Your own notes").run()
    assert not app.exception
    write = [b for b in app.button if b.label == "Write the note"][0]
    assert write.disabled


def test_added_clients_stay_in_one_session(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    first = AppTest.from_file(APP, default_timeout=30)
    first.run()
    first.text_input(key="nc_name").input("Test Visitor").run()
    [b for b in first.button if b.label == "Add client"][0].click().run()
    assert "Test Visitor" in [s for s in first.selectbox if s.label == "Client"][0].options

    second = AppTest.from_file(APP, default_timeout=30)
    second.run()
    assert "Test Visitor" not in [s for s in second.selectbox if s.label == "Client"][0].options


def _box(at, label):
    return [s for s in at.selectbox if s.label == label][0]


def _text(at):
    parts = [m.value for m in at.markdown] + [c.value for c in at.caption]
    parts += [i.value for i in at.info]
    return "\n".join(str(p) for p in parts)


def test_front_page_has_no_test_numbers(app):
    # The header leads with the product; figures live in the "How it's tested" tab.
    head = app.markdown[1].value if len(app.markdown) > 1 else ""
    page = _text(app)
    assert "objective, professional progress notes" in page
    assert "PHI leakage" not in head


def test_every_week_of_every_client(app):
    clients = _box(app, "Client")
    for i in range(len(clients.options)):
        clients.select_index(i).run()
        weeks = _box(app, "Week")
        for w in range(len(weeks.options)):
            weeks.select_index(w).run()
            assert not app.exception, app.exception
            assert "Pre-generated from this record" in _text(app)


def test_example_ledger_matches_eval_results(app):
    import json
    cases = {r["id"]: r for r in json.loads(
        (Path(APP).parent / "reports" / "eval_results.json").read_text())["results"]}
    box = _box(app, "Example")
    box.select("A family call and a case worker's email").run()
    page = _text(app)
    assert cases["c11"]["final"].split(".")[0] in page
    assert "<b>3</b> private details" in page and "<b>0</b> in the" in page


def test_eval_tab_shows_method_and_all_cases(app):
    page = _text(app)
    assert "0 of 14" in page and "4.26 / 5" in page
    assert "isn't a clinical validation" in page
    assert len(app.dataframe[0].value) == 18


def test_new_client_with_no_notes(app):
    app.text_input(key="nc_name").input("Empty Client").run()
    [b for b in app.button if b.label == "Add client"][0].click().run()
    _box(app, "Client").select("Empty Client").run()
    assert not app.exception, app.exception
    assert "No notes yet for this client." in _text(app)


def test_client_name_is_escaped(app):
    app.text_input(key="nc_name").input("<b>Bold</b>").run()
    [b for b in app.button if b.label == "Add client"][0].click().run()
    _box(app, "Client").select("<b>Bold</b>").run()
    assert not app.exception
    assert "&lt;b&gt;Bold&lt;/b&gt;" in _text(app)


def test_live_flow_with_a_stubbed_model(monkeypatch):
    """Write a note, see it screened, and save it, without calling the API."""
    from care_assistant import pipeline, config

    def fake_process(rough, first_name=None):
        return {"input": rough, "generated": "Eleanor spoke with Sarah by phone.",
                "redacted": "Eleanor spoke with [REDACTED: THIRD_PARTY_NAME] by phone.",
                "findings": [{"text": "Sarah", "type": "THIRD_PARTY_NAME", "source": "llm"}],
                "phi_count": 1}

    monkeypatch.setattr(pipeline, "process_note", fake_process)
    monkeypatch.setattr(config, "set_api_key", lambda key: None)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    assert at.segmented_control(key="note_mode").value == "Your own notes"
    before = len([e for e in at.expander if "Week of" in e.label])
    at.text_area(key="rough").input("talked to sarah on phone").run()
    [b for b in at.button if b.label == "Write the note"][0].click().run()
    assert not at.exception, at.exception
    page = _text(at)
    assert 'class="redact"' in page and "1 private detail removed." in page
    [b for b in at.button if b.label.startswith("Save to")][0].click().run()
    assert not at.exception, at.exception
    assert len([e for e in at.expander if "Week of" in e.label]) == before + 1
