"""Dashboard — pending ActionProposal, presented as scannable cards."""

from __future__ import annotations

import streamlit as st

import graph
from pages import _data

st.title("Dashboard")

business_id = st.session_state.get("business_id")
if not business_id:
    st.info("Pick a business on the **Connect** page first.")
    st.stop()

proposal = _data.fetch_pending_proposal(business_id)
if proposal is None:
    st.success(f"No pending proposals for **{business_id}**.")
    st.stop()


_PRIORITY_COLOUR = {"low": "blue", "medium": "orange", "high": "red", "urgent": "violet"}

_ACTION_EMOJI = {
    "wetsuit": "🌊", "cycling": "🚴", "bike": "🚴",
    "trekking": "🥾", "hiking": "🥾",
    "staff": "👥", "guide": "👤", "driver": "🚐",
    "boat": "⛵", "raft": "🛶", "surf": "🏄",
    "coffee": "☕", "milk": "🥛", "pastry": "🥐",
    "cup": "🥤", "first aid": "⛑️",
}


def _emoji_for(name: str) -> str:
    lower = name.lower()
    for key, glyph in _ACTION_EMOJI.items():
        if key in lower:
            return glyph
    return "📦"


# ─── Header strip ────────────────────────────────────────────────────
st.subheader(f"Pending proposal — {business_id.replace('_', ' ').title()}")
st.caption(f"Proposal {proposal.proposal_id} · {proposal.proposed_at}")

cols = st.columns(4)
cols[0].metric("Priority", proposal.priority.upper())
cols[1].metric("Demand multiplier", f"{proposal.forecast.demand_multiplier:.1f}×")
cols[2].metric(
    "Occupancy pressure",
    proposal.forecast.accommodation.occupancy_pressure.replace("_", " ").title(),
)
cols[3].metric("Confidence", f"{int(proposal.confidence * 100)}%")

st.markdown(
    f":{_PRIORITY_COLOUR.get(proposal.priority, 'gray')}-background[{proposal.forecast.demand_trend.replace('_', ' ').title()}] · "
    f"trend for {proposal.forecast.forecast_for_date}"
)

# ─── Owner brief ─────────────────────────────────────────────────────
st.markdown("### 📋 Owner brief")
brief = proposal.summary_for_owner.strip()
short = brief.split(". ")[0].rstrip(".") + "."
st.write(short)
if len(brief) > len(short):
    with st.expander("Read the full brief"):
        st.write(brief)

# ─── Recommended actions ─────────────────────────────────────────────
actions = []
for item in proposal.inventory_actions:
    actions.append({
        "emoji": _emoji_for(item.name),
        "title": item.name,
        "headline": f"{int(item.suggested_order_quantity)} {item.unit}",
        "sub": (
            f"have {int(item.current_quantity)} {item.unit}"
            + (f" · ${int(item.estimated_cost_usd):,}" if item.estimated_cost_usd else "")
        ),
        "supplier": item.supplier_name,
    })
for s in proposal.staffing_actions:
    verb = {
        "add_shift": "+", "extend_shift": "extend ",
        "reduce_shift": "−", "cancel_shift": "cancel ",
    }.get(s.action, "")
    actions.append({
        "emoji": _emoji_for(s.role),
        "title": s.role,
        "headline": f"{verb}{s.count} {s.role.lower()}",
        "sub": s.reason,
        "supplier": s.date,
    })

st.markdown(f"### 🎯 Recommended actions ({len(actions)})")
if actions:
    grid = st.columns(min(len(actions), 3))
    for idx, action in enumerate(actions):
        with grid[idx % 3]:
            with st.container(border=True):
                st.markdown(
                    f"<div style='font-size:2.5rem;text-align:center;line-height:1.1'>{action['emoji']}</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(f"**{action['headline']}**")
                st.caption(action["title"])
                if action["sub"]:
                    st.caption(action["sub"])
                if action.get("supplier"):
                    st.caption(f"↳ {action['supplier']}")
else:
    st.info("No structured actions in this proposal.")

# ─── Communications drafts ───────────────────────────────────────────
if proposal.communications:
    st.markdown(f"### ✉️ Communications drafted ({len(proposal.communications)})")
    for draft in proposal.communications:
        with st.container(border=True):
            chan_glyph = {
                "email": "📧", "whatsapp": "💬",
                "sms": "📱", "instagram_caption": "📸",
            }.get(draft.channel, "💬")
            head_cols = st.columns([1, 4, 1])
            head_cols[0].markdown(
                f"<div style='font-size:1.8rem'>{chan_glyph}</div>",
                unsafe_allow_html=True,
            )
            head_cols[1].markdown(f"**To:** {draft.recipient}")
            head_cols[2].markdown(
                f":{_PRIORITY_COLOUR.get(draft.urgency, 'gray')}-background[{draft.urgency}]"
            )
            if draft.subject:
                st.markdown(f"**Subject:** {draft.subject}")
            st.write(draft.body)

# ─── Decision ────────────────────────────────────────────────────────
st.markdown("### Decision")
st.caption(":orange[**Nothing executes until you approve.**]")
left, right, _ = st.columns([1, 1, 4])
if left.button("✅ Approve", type="primary", key="approve"):
    _data.update_proposal_status(proposal.proposal_id, "approved")
    graph.run_for_business(business_id)
    st.rerun()
if right.button("❌ Reject", key="reject"):
    _data.update_proposal_status(proposal.proposal_id, "rejected")
    st.rerun()
