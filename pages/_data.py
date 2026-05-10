"""Slice-4 page data helpers — raw SQL until Slice 0 ships richer db.py.

Each function opens its own short-lived connection. Tests monkey-patch
these functions on the module to keep AppTest runs DB-free; the
postgres-marked tests exercise the real SQL.
"""

from __future__ import annotations

import os

from models import ActionProposal, ReActStep, ReActTrace


def _connect():
    import psycopg

    return psycopg.connect(os.environ["DATABASE_URL"])


def fetch_latest_trace(business_id: str) -> ReActTrace | None:
    proposal = fetch_pending_proposal(business_id)
    if proposal is None:
        with _connect() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT proposal FROM proposals WHERE business_id = %s "
                "ORDER BY proposed_at DESC LIMIT 1",
                (business_id,),
            )
            row = cur.fetchone()
        if row is None:
            return None
        proposal = ActionProposal.model_validate(row[0])
    f = proposal.forecast
    steps = [
        ReActStep(step_index=0, agent_role="Demand Forecaster",
                  thought="Pull weather.", tool_called="get_tool_result",
                  tool_input={"tool": "weather"},
                  observation=f"{f.weather.condition} · {f.weather.precipitation_mm}mm"),
        ReActStep(step_index=1, agent_role="Demand Forecaster",
                  thought="Pull events.", tool_called="get_tool_result",
                  tool_input={"tool": "events"},
                  observation=f"{len(f.events)} event(s)"),
        ReActStep(step_index=2, agent_role="Demand Forecaster",
                  thought="Pull airbnb.", tool_called="get_tool_result",
                  tool_input={"tool": "airbnb"},
                  observation=f"pressure={f.accommodation.occupancy_pressure}"),
        ReActStep(step_index=3, agent_role="Demand Forecaster",
                  thought="Synthesize forecast.", tool_called=None, tool_input=None,
                  observation=f"multiplier={f.demand_multiplier:.2f}× trend={f.demand_trend}"),
        ReActStep(step_index=4, agent_role="Demand Modeler",
                  thought="Translate multiplier to quantities.",
                  tool_called="get_tool_result", tool_input={"tool": "inventory"},
                  observation=f"modelling {f.demand_multiplier:.2f}× demand"),
        ReActStep(step_index=5, agent_role="Logistics Agent",
                  thought="Produce inventory + staffing.", tool_called=None, tool_input=None,
                  observation=f"{len(proposal.inventory_actions)} inv, {len(proposal.staffing_actions)} staff"),
        ReActStep(step_index=6, agent_role="Communications Agent",
                  thought="Draft comms.", tool_called=None, tool_input=None,
                  observation=f"{len(proposal.communications)} draft(s)"),
        ReActStep(step_index=7, agent_role="Operations Manager",
                  thought="Merge into ActionProposal.", tool_called=None, tool_input=None,
                  observation=f"priority={proposal.priority} confidence={proposal.confidence:.2f}",
                  is_final=True),
    ]
    return ReActTrace(
        task_id=proposal.proposal_id, business_id=business_id,
        agent_role="Operations Manager", steps=steps,
        final_output_type="ActionProposal",
    )


def list_proposals(business_id: str) -> list[dict]:
    """Past proposals for the History page, newest first.

    Joins action_feedback so the History row carries the owner's rating.
    Each row is shaped for `st.dataframe`: proposed_at, summary_for_owner,
    status, rating.
    """
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                p.proposed_at::text,
                p.proposal->>'summary_for_owner' AS summary_for_owner,
                p.status,
                f.rating
            FROM proposals p
            LEFT JOIN action_feedback f ON f.proposal_id = p.proposal_id
            WHERE p.business_id = %s
            ORDER BY p.proposed_at DESC
            """,
            (business_id,),
        )
        rows = cur.fetchall()
    return [
        {
            "proposed_at": proposed_at,
            "summary_for_owner": summary,
            "status": status,
            "rating": rating,
        }
        for proposed_at, summary, status, rating in rows
    ]


def update_proposal_status(proposal_id: str, status: str) -> None:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE proposals SET status = %s WHERE proposal_id = %s",
            (status, proposal_id),
        )
        conn.commit()


def fetch_pending_proposal(business_id: str) -> ActionProposal | None:
    with _connect() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT proposal FROM proposals "
            "WHERE business_id = %s AND status = 'pending' "
            "ORDER BY proposed_at DESC LIMIT 1",
            (business_id,),
        )
        row = cur.fetchone()
    return ActionProposal.model_validate(row[0]) if row else None
