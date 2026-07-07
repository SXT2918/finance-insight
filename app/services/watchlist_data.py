"""Assembles the Watchlist table rows from stored OHLCV + indicators."""

import sqlite3


def _sparkline_points(closes: "list[float]", width=112, height=28, pad=2) -> str:
    if len(closes) < 2:
        return ""
    lo, hi = min(closes), max(closes)
    span = (hi - lo) or 1
    n = len(closes)
    pts = []
    for i, v in enumerate(closes):
        x = pad + i * (width - 2 * pad) / (n - 1)
        y = height - pad - (height - 2 * pad) * (v - lo) / span
        pts.append(f"{x:.1f},{y:.1f}")
    return " ".join(pts)


def build_watchlist_rows(conn: sqlite3.Connection) -> "list[dict]":
    tickers = conn.execute(
        "SELECT symbol, name FROM ticker WHERE is_watchlist = 1 ORDER BY symbol"
    ).fetchall()

    rows = []
    for t in tickers:
        symbol = t["symbol"]
        closes = conn.execute(
            "SELECT date, close FROM ohlcv WHERE symbol = ? ORDER BY date DESC LIMIT 30",
            (symbol,),
        ).fetchall()
        closes = list(reversed(closes))  # oldest -> newest

        if not closes:
            rows.append(
                {
                    "symbol": symbol, "name": t["name"], "price": None, "d1": None, "m1": None,
                    "rsi": None, "spark_points": "", "spark_up": True, "sentiment": None,
                }
            )
            continue

        close_vals = [c["close"] for c in closes]
        price = close_vals[-1]
        d1 = (price / close_vals[-2] - 1) * 100 if len(close_vals) >= 2 else None

        month_ago = conn.execute(
            "SELECT close FROM ohlcv WHERE symbol = ? ORDER BY date DESC LIMIT 1 OFFSET 21",
            (symbol,),
        ).fetchone()
        m1 = (price / month_ago["close"] - 1) * 100 if month_ago else None

        rsi_row = conn.execute(
            "SELECT rsi14 FROM indicator WHERE symbol = ? ORDER BY date DESC LIMIT 1",
            (symbol,),
        ).fetchone()
        rsi = rsi_row["rsi14"] if rsi_row else None

        rows.append(
            {
                "symbol": symbol,
                "name": t["name"],
                "price": price,
                "d1": d1,
                "m1": m1,
                "rsi": rsi,
                "spark_points": _sparkline_points(close_vals),
                "spark_up": close_vals[-1] >= close_vals[0],
                "sentiment": None,  # populated once news ingestion (Phase 5) is built
            }
        )
    return rows
