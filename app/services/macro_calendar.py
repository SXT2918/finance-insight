"""Macro calendar: real upcoming earnings dates for the watchlist, pulled
from yfinance. CPI/FOMC/etc. need a dedicated macro-data source we don't
have wired up yet, so we only show what we can verify rather than
guessing at economic-release dates.
"""

import sqlite3
from datetime import date

import yfinance as yf


def refresh_earnings_events(conn: sqlite3.Connection) -> int:
    tickers = [r["symbol"] for r in conn.execute("SELECT symbol FROM ticker WHERE is_watchlist = 1")]
    today = date.today()
    count = 0
    for symbol in tickers:
        try:
            df = yf.Ticker(symbol).get_earnings_dates(limit=4)
        except Exception:
            continue
        if df is None or df.empty:
            continue
        for ts in df.index:
            event_date = ts.date()
            if event_date < today:
                continue
            conn.execute(
                "INSERT OR IGNORE INTO macro_event (date, name, importance) VALUES (?, ?, 'high')",
                (event_date.isoformat(), f"{symbol} earnings"),
            )
            count += 1
    conn.commit()
    return count


def get_upcoming_events(conn: sqlite3.Connection, limit: int = 8) -> "list[sqlite3.Row]":
    today = date.today().isoformat()
    return conn.execute(
        "SELECT date, name, importance FROM macro_event WHERE date >= ? ORDER BY date LIMIT ?",
        (today, limit),
    ).fetchall()
