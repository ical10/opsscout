"""History page (Slice 4) — past proposals + status + feedback rating."""

from __future__ import annotations

import streamlit as st

from pages import _data

st.title("History")

business_id = st.session_state.get("business_id")
if business_id:
    rows = _data.list_proposals(business_id)
    if rows:
        st.dataframe(rows)
