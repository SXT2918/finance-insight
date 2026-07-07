"""Price series for the dashboard/analysis line charts.

1W/1M/1Y come from our own stored daily OHLCV. 1D needs intraday bars that
the daily job doesn't store, so it's fetched live (with a short cache) and
falls back to "unavailable" rather than inventing data if the market is
closed or the source errors out.
"""

import sqlite3

import yfinance as yf

from app.services.cache import cache

TIMEFRAME_DAYS = {"1W": 5, "1M": 22, "1Y": 252}

INTRADAY_TTL_SECONDS = 120


def _fetch_intraday(symbol: str):
    df = yf.Ticker(symbol).history(period="1d", interval="5m", auto_adjust=False)
    if df.empty:
        return []
    return [{"t": idx.strftime("%H:%M"), "c": float(row.Close)} for idx, row in df.iterrows()]


def get_series(conn: sqlite3.Connection, symbol: str, timeframe: str):
    """Returns (points, is_stale) where points is a list of {t, c} dicts."""
    if timeframe == "1D":
        points, stale = cache.get_or_fetch(f"intraday:{symbol}", INTRADAY_TTL_SECONDS, lambda: _fetch_intraday(symbol))
        return points, stale

    n = TIMEFRAME_DAYS.get(timeframe, 22)
    rows = conn.execute(
        "SELECT date, close FROM ohlcv WHERE symbol = ? ORDER BY date DESC LIMIT ?",
        (symbol, n),
    ).fetchall()
    rows = list(reversed(rows))
    return [{"t": r["date"], "c": r["close"]} for r in rows], False
