"""Dashboard page (Slice 4) — pending ActionProposal card + Approve / Reject."""

from __future__ import annotations

import streamlit as st

import graph
from pages import _data

st.title("Dashboard")

business_id = st.session_state.get("business_id")
if business_id:
    proposal = _data.fetch_pending_proposal(business_id)
    if proposal is not None:
        with st.container(border=True):
            st.subheader(proposal.summary_for_owner)
            st.markdown(f"**Priority:** `{proposal.priority}`")
            cols = st.columns(2)
            if cols[0].button("Approve", key="approve"):
                _data.update_proposal_status(proposal.proposal_id, "approved")
                graph.run_for_business(business_id)
            cols[1].button("Reject", key="reject")
