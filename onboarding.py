"""Owner onboarding (Slice 4)."""

from __future__ import annotations


def render_onboarding() -> None:
    import os

    import streamlit as st

    name_to_id = {
        "Nusa Adventures": "nusa_adventures",
        "Kopi Nusa Café": "kopi_nusa_cafe",
    }

    st.header("Welcome to OpsScout")
    if os.environ.get("DEMO_MODE", "true") == "false":
        st.button("Connect Shopify", disabled=True)
        st.button("Connect Google", disabled=True)
        st.button("Connect Slack", disabled=True)
    else:
        choice = st.radio("Pick a demo business", list(name_to_id.keys()))
        if choice is not None:
            st.session_state["business_id"] = name_to_id[choice]
