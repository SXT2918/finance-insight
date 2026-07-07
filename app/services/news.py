"""News ingestion via yfinance's built-in news feed (real Yahoo Finance
data, no separate paid news API key required)."""

import sqlite3
from datetime import datetime, timezone

import yfinance as yf


def _pick_thumbnail(thumbnail: dict) -> "str | None":
    if not thumbnail:
        return None
    resolutions = thumbnail.get("resolutions") or []
    # prefer a small/medium resolution over the full-size original
    candidates = [r for r in resolutions if r.get("tag") != "original"]
    pool = candidates or resolutions
    if not pool:
        return thumbnail.get("originalUrl")
    pool = sorted(pool, key=lambda r: r.get("width", 0))
    return pool[0]["url"]


def _normalize(item: dict) -> "dict | None":
    content = item.get("content") or {}
    title = content.get("title")
    url = (content.get("canonicalUrl") or {}).get("url") or (content.get("clickThroughUrl") or {}).get("url")
    if not title or not url:
        return None
    provider = content.get("provider") or {}
    return {
        "url": url,
        "title": title,
        "source": provider.get("displayName", "Yahoo Finance"),
        "published_at": content.get("pubDate") or datetime.now(timezone.utc).isoformat(),
        "image_url": _pick_thumbnail(content.get("thumbnail")),
    }


def fetch_news_for_ticker(symbol: str, limit: int = 8) -> "list[dict]":
    raw = yf.Ticker(symbol).news or []
    items = [_normalize(i) for i in raw[:limit]]
    return [i for i in items if i is not None]


def _upsert_news_item(conn: sqlite3.Connection, item: dict) -> int:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.execute(
        """
        INSERT INTO news_item (url, title, source, published_at, image_url, fetched_at)
        VALUES (:url, :title, :source, :published_at, :image_url, :fetched_at)
        ON CONFLICT(url) DO UPDATE SET
            title=excluded.title, source=excluded.source,
            published_at=excluded.published_at, image_url=excluded.image_url
        """,
        {**item, "fetched_at": now},
    )
    row = conn.execute("SELECT id FROM news_item WHERE url = ?", (item["url"],)).fetchone()
    return row["id"]


def ingest_news_for_watchlist(conn: sqlite3.Connection) -> int:
    """Fetch and tag news for every watchlist ticker. Returns count of items touched."""
    tickers = [r["symbol"] for r in conn.execute("SELECT symbol FROM ticker WHERE is_watchlist = 1")]
    count = 0
    for symbol in tickers:
        try:
            items = fetch_news_for_ticker(symbol)
        except Exception:
            continue
        for item in items:
            news_id = _upsert_news_item(conn, item)
            conn.execute(
                "INSERT OR IGNORE INTO news_tag (news_id, tag, tag_type) VALUES (?, ?, 'ticker')",
                (news_id, symbol),
            )
            count += 1
    conn.commit()
    return count
