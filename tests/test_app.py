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
