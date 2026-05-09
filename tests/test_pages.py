"""Slice 4 Streamlit page tests — uses streamlit.testing.v1.AppTest."""
from __future__ import annotations

from streamlit.testing.v1 import AppTest


def test_main_app_loads():
    app = AppTest.from_file("main.py").run()
    assert not app.exception


def test_connect_page_demo_mode_picker(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    app = AppTest.from_file("pages/1_Connect.py").run()
    assert not app.exception
    options = app.radio[0].options
    assert "Nusa Adventures" in options
    assert "Kopi Nusa Café" in options


def test_connect_page_writes_business_id_on_select(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    app = AppTest.from_file("pages/1_Connect.py").run()
    app.radio[0].set_value("Nusa Adventures").run()
    assert app.session_state["business_id"] == "nusa_adventures"


def test_connect_page_shows_oauth_buttons_when_not_demo(monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "false")
    app = AppTest.from_file("pages/1_Connect.py").run()
    button_labels = [b.label for b in app.button]
    assert "Connect Shopify" in button_labels
    assert "Connect Google" in button_labels
    assert len(app.radio) == 0
