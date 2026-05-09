"""Slice-4 page data helpers — raw SQL until Slice 0 ships richer db.py.

Each function opens its own short-lived connection. Tests monkey-patch
these functions on the module to keep AppTest runs DB-free; the
postgres-marked tests exercise the real SQL.
"""

from __future__ import annotations

import os

from models import ActionProposal


def _connect():
    import psycopg

    return psycopg.connect(os.environ["DATABASE_URL"])


def fetch_latest_trace(business_id):  # noqa: ARG001
    return None


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
