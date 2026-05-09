"""Slice 4 Streamlit page tests — uses streamlit.testing.v1.AppTest."""
from __future__ import annotations

from streamlit.testing.v1 import AppTest


def test_main_app_loads():
    app = AppTest.from_file("main.py").run()
    assert not app.exception
