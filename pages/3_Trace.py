"""Trace page (Slice 4) — ReAct steps in order for the latest run."""

from __future__ import annotations

import streamlit as st

from pages import _data

st.title("ReAct Trace")

business_id = st.session_state.get("business_id")
if business_id:
    trace = _data.fetch_latest_trace(business_id)
    if trace is not None:
        for step in trace.steps:
            icon = "✅" if step.is_final else "🤔"
            with st.expander(f"{icon} Step {step.step_index} — {step.agent_role}"):
                st.markdown(f"🤔 **Thought:** {step.thought}")
                if step.tool_called:
                    tool_input = step.tool_input or {}
                    st.markdown(f"🛠 **Tool:** `{step.tool_called}` {tool_input}")
                if step.observation:
                    st.markdown(f"👀 **Observation:** {step.observation}")
