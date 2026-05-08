"""PostgreSQL helpers — Slice 0 owns schema, Slice 5 may extend.

Schema mirrors spec §11a (seed.py listing). All writes go through these
helpers so the agents and Streamlit pages don't sprinkle raw SQL.
"""

from __future__ import annotations

from models import ActionFeedback, ActionProposal


_SCHEMA = """
CREATE TABLE IF NOT EXISTS businesses (
    business_id TEXT PRIMARY KEY,
    profile     JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS proposals (
    proposal_id  TEXT PRIMARY KEY,
    business_id  TEXT NOT NULL,
    proposed_at  TIMESTAMPTZ NOT NULL,
    proposal     JSONB NOT NULL,
    status       TEXT DEFAULT 'pending'
);
CREATE TABLE IF NOT EXISTS action_feedback (
    feedback_id  TEXT PRIMARY KEY,
    proposal_id  TEXT NOT NULL,
    business_id  TEXT NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL,
    rating       TEXT NOT NULL,
    free_text    TEXT,
    was_accurate BOOLEAN
);
CREATE TABLE IF NOT EXISTS historical_demand (
    business_id      TEXT NOT NULL,
    date             DATE NOT NULL,
    actual_guests    INT,
    demand_multiplier FLOAT,
    PRIMARY KEY (business_id, date)
);
"""


def create_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(_SCHEMA)
    conn.commit()


def get_business(conn, business_id: str) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT profile FROM businesses WHERE business_id = %s",
            (business_id,),
        )
        row = cur.fetchone()
    if row is None:
        raise KeyError(f"business not found: {business_id}")
    return row[0]


def get_proposal(conn, proposal_id: str) -> ActionProposal:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT proposal FROM proposals WHERE proposal_id = %s",
            (proposal_id,),
        )
        row = cur.fetchone()
    return ActionProposal.model_validate(row[0])


def save_proposal(conn, proposal: ActionProposal) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO proposals (proposal_id, business_id, proposed_at, proposal) "
            "VALUES (%s, %s, %s, %s::jsonb)",
            (
                proposal.proposal_id,
                proposal.business_id,
                proposal.proposed_at,
                proposal.model_dump_json(),
            ),
        )
    conn.commit()


def save_feedback(conn, feedback: ActionFeedback) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO action_feedback "
            "(feedback_id, proposal_id, business_id, submitted_at, rating, free_text, was_accurate) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                feedback.feedback_id,
                feedback.proposal_id,
                feedback.business_id,
                feedback.submitted_at,
                feedback.rating,
                feedback.free_text,
                feedback.was_accurate,
            ),
        )
    conn.commit()
