"""Per-ticker fundamentals (market cap, P/E, 52-week range, volume, analyst
target) via yfinance's get_info(). Refreshed once daily by the cron job and
read straight from the ticker table at request time — never fetched live
on page load.
"""

import sqlite3
from datetime import datetime, timezone

import yfinance as yf

FIELDS = [
    ("market_cap", "marketCap"),
    ("trailing_pe", "trailingPE"),
    ("forward_pe", "forwardPE"),
    ("week52_low", "fiftyTwoWeekLow"),
    ("week52_high", "fiftyTwoWeekHigh"),
    ("avg_volume", "averageVolume"),
    ("target_mean_price", "targetMeanPrice"),
    ("recommendation_key", "recommendationKey"),
    ("dividend_yield", "dividendYield"),
]


def refresh_fundamentals_for_watchlist(conn: sqlite3.Connection) -> int:
    tickers = [r["symbol"] for r in conn.execute("SELECT symbol FROM ticker WHERE is_watchlist = 1")]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    count = 0
    for symbol in tickers:
        try:
            info = yf.Ticker(symbol).get_info()
        except Exception:
            continue
        values = [info.get(src) for _, src in FIELDS]
        set_clause = ", ".join(f"{col} = ?" for col, _ in FIELDS)
        conn.execute(
            f"UPDATE ticker SET {set_clause}, fundamentals_updated_at = ? WHERE symbol = ?",
            (*values, now, symbol),
        )
        count += 1
    conn.commit()
    return count


def get_fundamentals(conn: sqlite3.Connection, symbol: str) -> "sqlite3.Row | None":
    return conn.execute(
        """
        SELECT market_cap, trailing_pe, forward_pe, week52_low, week52_high,
               avg_volume, target_mean_price, recommendation_key, dividend_yield,
               fundamentals_updated_at
        FROM ticker WHERE symbol = ?
        """,
        (symbol,),
    ).fetchone()


def _fmt_large(value: "float | None") -> "str | None":
    if value is None:
        return None
    abs_v = abs(value)
    if abs_v >= 1e12:
        return f"${value / 1e12:.2f}T"
    if abs_v >= 1e9:
        return f"${value / 1e9:.2f}B"
    if abs_v >= 1e6:
        return f"${value / 1e6:.2f}M"
    return f"${value:,.0f}"


def _fmt_volume(value: "float | None") -> "str | None":
    if value is None:
        return None
    abs_v = abs(value)
    if abs_v >= 1e9:
        return f"{value / 1e9:.2f}B"
    if abs_v >= 1e6:
        return f"{value / 1e6:.1f}M"
    if abs_v >= 1e3:
        return f"{value / 1e3:.1f}K"
    return f"{value:,.0f}"


def build_fundamentals_view(row: "sqlite3.Row | None", current_price: "float | None") -> "dict | None":
    if row is None or row["fundamentals_updated_at"] is None:
        return None

    week_range_pct = None
    if row["week52_low"] is not None and row["week52_high"] is not None and current_price is not None:
        span = row["week52_high"] - row["week52_low"]
        if span > 0:
            week_range_pct = max(0.0, min(100.0, (current_price - row["week52_low"]) / span * 100))

    return {
        "market_cap": _fmt_large(row["market_cap"]),
        "trailing_pe": f"{row['trailing_pe']:.1f}" if row["trailing_pe"] is not None else None,
        "forward_pe": f"{row['forward_pe']:.1f}" if row["forward_pe"] is not None else None,
        "week52_low": row["week52_low"],
        "week52_high": row["week52_high"],
        "week_range_pct": week_range_pct,
        "avg_volume": _fmt_volume(row["avg_volume"]),
        "target_mean_price": row["target_mean_price"],
        "recommendation_key": (row["recommendation_key"] or "").replace("_", " ").title() or None,
        "dividend_yield": f"{row['dividend_yield']:.2f}%" if row["dividend_yield"] is not None else None,
    }
