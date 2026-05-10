"""Connect page (Slice 4) — DEMO_MODE business picker, production OAuth shell."""

from __future__ import annotations

import os

import streamlit as st

NAME_TO_ID = {
    "Nusa Adventures": "nusa_adventures",
    "Kopi Nusa Café": "kopi_nusa_cafe",
}

choice = st.radio("Pick a demo business", list(NAME_TO_ID.keys()))
if choice is not None:
    st.session_state["business_id"] = NAME_TO_ID[choice]

if os.environ.get("DEMO_MODE", "true") == "false":
    st.button("Connect Shopify", disabled=True)
    st.button("Connect Google", disabled=True)
    st.button("Connect Slack", disabled=True)
