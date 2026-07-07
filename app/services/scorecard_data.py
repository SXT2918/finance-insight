"""Quality scorecard: 6 dimensions, 0-3 each. User scores are entered
manually and persisted; the AI suggestion is one cached Anthropic call
per ticker (not per dimension) shown alongside for comparison.
"""

import json
import re
import sqlite3
from datetime import datetime, timezone

import anthropic

from app.services.ticker_context import format_context_block, get_ticker_context

MODEL = "claude-haiku-4-5-20251001"

DIMENSIONS = [
    ("moat", "Moat", "pricing power, switching costs, network effects"),
    ("business_model", "Business model", "how durable is the way it makes money"),
    ("growth_runway", "Growth runway", "can revenue compound for 5+ years"),
    ("balance_sheet", "Balance sheet", "net cash, debt load, interest cover"),
    ("management", "Management", "capital allocation track record"),
    ("valuation", "Valuation", "price vs. what the business earns"),
]


def get_scorecard(conn: sqlite3.Connection, symbol: str) -> "list[dict]":
    rows = {
        r["dimension"]: r
        for r in conn.execute("SELECT * FROM scorecard WHERE ticker = ?", (symbol,)).fetchall()
    }
    return [
        {
            "key": key,
            "label": label,
            "desc": desc,
            "user_score": rows[key]["user_score"] if key in rows else None,
            "ai_score": rows[key]["ai_score"] if key in rows else None,
        }
        for key, label, desc in DIMENSIONS
    ]


def save_user_scores(conn: sqlite3.Connection, symbol: str, scores: "dict[str, int]") -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for key, _, _ in DIMENSIONS:
        if key not in scores:
            continue
        conn.execute(
            """
            INSERT INTO scorecard (ticker, dimension, user_score, ai_score, updated_at)
            VALUES (?, ?, ?, NULL, ?)
            ON CONFLICT(ticker, dimension) DO UPDATE SET user_score = excluded.user_score, updated_at = excluded.updated_at
            """,
            (symbol, key, scores[key], now),
        )
    conn.commit()


def generate_ai_scores(conn: sqlite3.Connection, symbol: str, api_key: str) -> None:
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")

    ctx = get_ticker_context(conn, symbol)
    context_block = format_context_block(ctx)
    dims_desc = "\n".join(f"- {key}: {label} ({desc})" for key, label, desc in DIMENSIONS)

    prompt = f"""You are scoring {symbol} on a 6-dimension quality scorecard for an educational
research site, 0-3 on each dimension (0 = weak, 3 = strong). Base this only on the verified data
below plus general knowledge of the company's business — do not invent specific financial figures.
This is not investment advice. Respond with STRICT JSON only, no markdown fences, mapping each key
to an integer 0-3:

Dimensions:
{dims_desc}

Verified data:
{context_block}
"""
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(model=MODEL, max_tokens=200, messages=[{"role": "user", "content": prompt}])
    raw = "".join(b.text for b in resp.content if b.type == "text").strip()
    raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.MULTILINE).strip()
    scores = json.loads(raw)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for key, _, _ in DIMENSIONS:
        value = scores.get(key)
        if not isinstance(value, int) or not (0 <= value <= 3):
            continue
        conn.execute(
            """
            INSERT INTO scorecard (ticker, dimension, user_score, ai_score, updated_at)
            VALUES (?, ?, NULL, ?, ?)
            ON CONFLICT(ticker, dimension) DO UPDATE SET ai_score = excluded.ai_score, updated_at = excluded.updated_at
            """,
            (symbol, key, value, now),
        )
    conn.commit()
