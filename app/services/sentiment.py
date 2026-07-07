"""Lightweight lexicon-based sentiment scoring for headlines.

Deliberately not an LLM call: sentiment tagging runs over every ingested
headline, and an API call per article would be slow and costly. A keyword
scorer is enough to bucket bullish/bearish/neutral for the watchlist and
brief; the AI research desk (Phase 6) is where a model actually reasons
about a ticker.
"""

import sqlite3
from datetime import datetime, timezone

POSITIVE_WORDS = {
    "beat", "beats", "surge", "surges", "rally", "rallies", "record", "upgrade", "upgraded",
    "gain", "gains", "gained", "strong", "growth", "soar", "soars", "outperform", "bullish",
    "profit", "profits", "win", "wins", "jump", "jumps", "rise", "rises", "high", "boost",
    "boosts", "raise", "raises", "raised", "expand", "expands", "breakthrough", "optimistic",
}

NEGATIVE_WORDS = {
    "miss", "misses", "plunge", "plunges", "fall", "falls", "fallen", "downgrade", "downgraded",
    "loss", "losses", "weak", "slump", "slumps", "sink", "sinks", "underperform", "bearish",
    "cut", "cuts", "recall", "lawsuit", "delay", "delays", "delayed", "concern", "concerns",
    "warn", "warns", "warning", "layoff", "layoffs", "drop", "drops", "decline", "declines",
    "probe", "investigation", "fraud", "crash", "crashes", "sell-off", "selloff",
}


def score_title(title: str) -> "tuple[float, str]":
    words = {w.strip(".,!?()'\"").lower() for w in title.split()}
    pos = len(words & POSITIVE_WORDS)
    neg = len(words & NEGATIVE_WORDS)
    score = pos - neg
    if score > 0:
        label = "bullish"
    elif score < 0:
        label = "bearish"
    else:
        label = "neutral"
    return float(score), label


def score_unscored_news(conn: sqlite3.Connection) -> int:
    rows = conn.execute(
        """
        SELECT n.id, n.title FROM news_item n
        LEFT JOIN news_sentiment s ON s.news_id = n.id
        WHERE s.news_id IS NULL
        """
    ).fetchall()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for row in rows:
        score, label = score_title(row["title"])
        conn.execute(
            "INSERT INTO news_sentiment (news_id, score, label, scored_at) VALUES (?, ?, ?, ?)",
            (row["id"], score, label, now),
        )
    conn.commit()
    return len(rows)


def get_ticker_sentiment(conn: sqlite3.Connection, symbol: str) -> "dict | None":
    """Aggregate sentiment over a ticker's most recent tagged headlines."""
    rows = conn.execute(
        """
        SELECT s.label FROM news_sentiment s
        JOIN news_tag t ON t.news_id = s.news_id
        JOIN news_item n ON n.id = s.news_id
        WHERE t.tag = ? AND t.tag_type = 'ticker'
        ORDER BY n.published_at DESC LIMIT 10
        """,
        (symbol,),
    ).fetchall()
    if not rows:
        return None
    labels = [r["label"] for r in rows]
    bull = labels.count("bullish")
    bear = labels.count("bearish")
    if bull > bear:
        overall = "Bullish"
    elif bear > bull:
        overall = "Bearish"
    else:
        overall = "Neutral"
    return {"label": overall, "n": len(labels)}
