"""PostgreSQL helpers — Slice 0 owns schema, Slice 5 may extend.

Schema mirrors spec §11a (seed.py listing). All writes go through these
helpers so the agents and Streamlit pages don't sprinkle raw SQL.
"""

from __future__ import annotations


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
