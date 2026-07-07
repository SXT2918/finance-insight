"""Dashboard extras: top movers from the watchlist and a major-index
snapshot strip. Both computed from stored OHLCV — indices are ingested
daily by the cron job just like the watchlist/sector ETFs, not fetched
live on page load.
"""

import sqlite3

from app.services.price_stats import get_price_and_changes

INDEX_SYMBOLS = [
    ("S&P 500", "SPY"),
    ("Nasdaq 100", "QQQ"),
    ("Dow 30", "DIA"),
    ("Russell 2000", "IWM"),
]


def get_index_snapshots(conn: sqlite3.Connection) -> "list[dict]":
    snapshots = []
    for label, symbol in INDEX_SYMBOLS:
        stats = get_price_and_changes(conn, symbol, spark_n=2)
        snapshots.append(
            {
                "label": label,
                "symbol": symbol,
                "price": stats["price"] if stats else None,
                "d1": stats["d1"] if stats else None,
            }
        )
    return snapshots


def get_movers(conn: sqlite3.Connection, top_n: int = 5) -> dict:
    tickers = conn.execute(
        "SELECT symbol, name FROM ticker WHERE is_watchlist = 1 ORDER BY symbol"
    ).fetchall()

    rows = []
    for t in tickers:
        stats = get_price_and_changes(conn, t["symbol"], spark_n=2)
        if stats is None or stats["d1"] is None:
            continue
        rows.append({"symbol": t["symbol"], "name": t["name"], "price": stats["price"], "d1": stats["d1"]})

    gainers = sorted(rows, key=lambda r: r["d1"], reverse=True)[:top_n]
    losers = sorted(rows, key=lambda r: r["d1"])[:top_n]
    return {"gainers": gainers, "losers": losers}
