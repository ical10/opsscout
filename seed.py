from __future__ import annotations

import math
import os
from datetime import date, timedelta
from pathlib import Path

import psycopg

FIXTURES_DIR = Path(__file__).parent / "mock" / "fixtures"


def seed() -> None:
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor() as cur:
            for biz_id in ("kopi_nusa_cafe", "nusa_adventures"):
                profile = (FIXTURES_DIR / biz_id / "business.json").read_text()
                cur.execute(
                    "INSERT INTO businesses (business_id, profile) "
                    "VALUES (%s, %s::jsonb) "
                    "ON CONFLICT (business_id) DO UPDATE SET profile = EXCLUDED.profile",
                    (biz_id, profile),
                )
                for i in range(30):
                    day = date.today() - timedelta(days=30 - i)
                    multiplier = round(1.0 + 0.3 * math.sin(i / 3.0), 2)
                    cur.execute(
                        "INSERT INTO historical_demand "
                        "(business_id, date, actual_guests, demand_multiplier) "
                        "VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                        (biz_id, day.isoformat(), int(50 * multiplier), multiplier),
                    )
        conn.commit()
