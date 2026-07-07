"""Shared price/change lookups used by Watchlist and Analysis."""

import sqlite3

MONTH_OFFSET = 21  # ~1 trading month


def get_price_and_changes(conn: sqlite3.Connection, symbol: str, spark_n: int = 30):
    """Returns dict(price, d1, m1, close_vals) or None if we have no price history."""
    closes = conn.execute(
        "SELECT close FROM ohlcv WHERE symbol = ? ORDER BY date DESC LIMIT ?",
        (symbol, spark_n),
    ).fetchall()
    if not closes:
        return None
    close_vals = [c["close"] for c in reversed(closes)]

    price = close_vals[-1]
    d1 = (price / close_vals[-2] - 1) * 100 if len(close_vals) >= 2 else None

    month_ago = conn.execute(
        "SELECT close FROM ohlcv WHERE symbol = ? ORDER BY date DESC LIMIT 1 OFFSET ?",
        (symbol, MONTH_OFFSET),
    ).fetchone()
    m1 = (price / month_ago["close"] - 1) * 100 if month_ago else None

    return {"price": price, "d1": d1, "m1": m1, "close_vals": close_vals}
