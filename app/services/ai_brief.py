"""Daily brief generation: one Anthropic call per day, cached in daily_brief.

Never calls the LLM on page load — a route only triggers generate_brief()
when there's no cached entry for today and the user explicitly asks for one.
"""

import sqlite3
from datetime import date, datetime, timezone

import anthropic

from app.services.price_stats import get_price_and_changes

MODEL = "claude-haiku-4-5-20251001"


def _watchlist_moves(conn: sqlite3.Connection) -> "list[dict]":
    tickers = conn.execute(
        "SELECT symbol, name FROM ticker WHERE is_watchlist = 1 ORDER BY symbol"
    ).fetchall()
    moves = []
    for t in tickers:
        stats = get_price_and_changes(conn, t["symbol"])
        if stats is None:
            continue
        moves.append({"symbol": t["symbol"], "name": t["name"], "price": stats["price"], "d1": stats["d1"]})
    return moves


def _top_headlines(conn: sqlite3.Connection, limit: int = 8) -> "list[dict]":
    rows = conn.execute(
        """
        SELECT n.title, n.source, GROUP_CONCAT(DISTINCT t.tag) AS tags, s.label
        FROM news_item n
        JOIN news_tag t ON t.news_id = n.id
        LEFT JOIN news_sentiment s ON s.news_id = n.id
        GROUP BY n.id
        ORDER BY n.published_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [{"title": r["title"], "source": r["source"], "tags": r["tags"], "sentiment": r["label"]} for r in rows]


def _build_prompt(moves: "list[dict]", headlines: "list[dict]") -> str:
    moves_lines = "\n".join(
        f"- {m['symbol']} ({m['name']}): ${m['price']:.2f}, {m['d1']:+.2f}% today" if m["d1"] is not None
        else f"- {m['symbol']} ({m['name']}): ${m['price']:.2f}"
        for m in moves
    )
    headline_lines = "\n".join(
        f"- [{h['sentiment'] or 'neutral'}] {h['title']} ({h['source']}, tagged: {h['tags']})"
        for h in headlines
    ) or "- No tagged headlines available yet."

    return f"""You are writing the "Daily brief" digest for Finance Insight, an educational stock-analysis
site. Write exactly two short paragraphs (3-4 sentences each) summarizing today's watchlist moves and
the top tagged headlines below. Use only the figures given — never invent a price, percentage, or event
that isn't listed. Tone: professional, Yahoo-Finance-clean, factual, no hype, no investment advice or
recommendations to buy/sell. Do not add a title or signature, just the two paragraphs.

Watchlist moves today:
{moves_lines or '- No price data available.'}

Top tagged headlines:
{headline_lines}
"""


def generate_brief(conn: sqlite3.Connection, api_key: str) -> str:
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")

    moves = _watchlist_moves(conn)
    headlines = _top_headlines(conn)
    prompt = _build_prompt(moves, headlines)

    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=MODEL,
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in resp.content if block.type == "text").strip()


def get_cached_brief(conn: sqlite3.Connection, target_date: "date | None" = None):
    target_date = target_date or date.today()
    return conn.execute(
        "SELECT date, summary_text, generated_at FROM daily_brief WHERE date = ?",
        (target_date.isoformat(),),
    ).fetchone()


def generate_and_store_brief(conn: sqlite3.Connection, api_key: str):
    text = generate_brief(conn, api_key)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    today = date.today().isoformat()
    conn.execute(
        """
        INSERT INTO daily_brief (date, summary_text, generated_at) VALUES (?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET summary_text=excluded.summary_text, generated_at=excluded.generated_at
        """,
        (today, text, now),
    )
    conn.commit()
    return get_cached_brief(conn)
