"""AI research desk: one Anthropic call per analyst role, then a Portfolio
Manager synthesis call. Cached per ticker per day in ai_desk_report, so
re-visiting the page never re-triggers the calls.
"""

import json
import re
import sqlite3
from datetime import date

import anthropic

from app.services.ticker_context import format_context_block, get_ticker_context

MODEL = "claude-haiku-4-5-20251001"

ROLES = ["Technical Analyst", "Fundamental Analyst", "Sentiment Analyst", "Risk Manager"]
PM_ROLE = "Portfolio Manager"

ROLE_INSTRUCTIONS = {
    "Technical Analyst": "Focus only on price action and the technical indicators given (RSI, MACD, moving averages). 2-3 sentences.",
    "Fundamental Analyst": "Focus on what can reasonably be inferred from the price/news data given. Do not invent revenue, earnings, or other financial figures that aren't provided. If fundamental data is limited, say so plainly. 2-3 sentences.",
    "Sentiment Analyst": "Focus only on the tagged news headlines and sentiment labels provided. 2-3 sentences.",
    "Risk Manager": "Identify the key risk(s) an investor should weigh given the technical/news data provided, and how position sizing or timing might address it. 2-3 sentences.",
}

RATING_OPTIONS = ["Overweight", "Neutral", "Underweight"]


def _client(api_key: str) -> anthropic.Anthropic:
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")
    return anthropic.Anthropic(api_key=api_key)


def _text(resp) -> str:
    return "".join(block.text for block in resp.content if block.type == "text").strip()


def _call_role(client: anthropic.Anthropic, role: str, context_block: str) -> str:
    prompt = f"""You are the {role} on an educational research desk for Finance Insight, a stock-analysis
learning site. This is not investment advice. Use ONLY the verified data below — never invent a price,
percentage, or event not listed. {ROLE_INSTRUCTIONS[role]}

{context_block}
"""
    resp = client.messages.create(model=MODEL, max_tokens=200, messages=[{"role": "user", "content": prompt}])
    return _text(resp)


def _call_pm(client: anthropic.Anthropic, symbol: str, role_texts: dict, context_block: str) -> dict:
    notes = "\n\n".join(f"{role}: {text}" for role, text in role_texts.items())
    prompt = f"""You are the Portfolio Manager synthesizing the analyst notes below for {symbol} on an
educational research desk. This is not investment advice — frame the rating as an educational
"weight" label only. Respond with STRICT JSON only, no markdown code fences, matching exactly:
{{"rating": "Overweight" | "Neutral" | "Underweight", "thesis": "2-3 sentence synthesis", "horizon": "e.g. 3-6 months"}}

Analyst notes:
{notes}

Verified data:
{context_block}
"""
    resp = client.messages.create(model=MODEL, max_tokens=300, messages=[{"role": "user", "content": prompt}])
    raw = _text(resp)
    raw = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    data = json.loads(raw)
    if data.get("rating") not in RATING_OPTIONS:
        data["rating"] = "Neutral"
    return data


def generate_desk_report(conn: sqlite3.Connection, symbol: str, api_key: str) -> dict:
    client = _client(api_key)
    ctx = get_ticker_context(conn, symbol)
    context_block = format_context_block(ctx)

    role_texts = {role: _call_role(client, role, context_block) for role in ROLES}
    pm = _call_pm(client, symbol, role_texts, context_block)

    today = date.today().isoformat()
    for role, text in role_texts.items():
        conn.execute(
            """
            INSERT INTO ai_desk_report (ticker, generated_date, role, content, rating, horizon)
            VALUES (?, ?, ?, ?, NULL, NULL)
            ON CONFLICT(ticker, generated_date, role) DO UPDATE SET content = excluded.content
            """,
            (symbol, today, role, text),
        )
    conn.execute(
        """
        INSERT INTO ai_desk_report (ticker, generated_date, role, content, rating, horizon)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(ticker, generated_date, role) DO UPDATE SET
            content = excluded.content, rating = excluded.rating, horizon = excluded.horizon
        """,
        (symbol, today, PM_ROLE, pm["thesis"], pm["rating"], pm["horizon"]),
    )
    conn.commit()
    return get_cached_desk_report(conn, symbol)


def get_cached_desk_report(conn: sqlite3.Connection, symbol: str, target_date: "str | None" = None):
    target_date = target_date or date.today().isoformat()
    rows = conn.execute(
        "SELECT role, content, rating, horizon FROM ai_desk_report WHERE ticker = ? AND generated_date = ?",
        (symbol, target_date),
    ).fetchall()
    if not rows:
        return None
    by_role = {r["role"]: r for r in rows}
    if not all(r in by_role for r in ROLES + [PM_ROLE]):
        return None
    return {
        "roles": [(role, by_role[role]["content"]) for role in ROLES],
        "pm": {
            "thesis": by_role[PM_ROLE]["content"],
            "rating": by_role[PM_ROLE]["rating"],
            "horizon": by_role[PM_ROLE]["horizon"],
        },
        "generated_date": target_date,
    }
