"""Fetch OHLCV price history via yfinance and persist it to the ohlcv table."""

import sqlite3
from datetime import datetime, timezone

import yfinance as yf


def fetch_ohlcv_history(symbol: str, period: str = "2y") -> "list[dict]":
    """Download daily OHLCV bars for a symbol. Returns a list of row dicts."""
    df = yf.Ticker(symbol).history(period=period, interval="1d", auto_adjust=False)
    if df.empty:
        return []
    df = df.reset_index()
    rows = []
    for _, r in df.iterrows():
        rows.append(
            {
                "symbol": symbol,
                "date": r["Date"].strftime("%Y-%m-%d"),
                "open": float(r["Open"]),
                "high": float(r["High"]),
                "low": float(r["Low"]),
                "close": float(r["Close"]),
                "volume": int(r["Volume"]),
            }
        )
    return rows


def upsert_ohlcv(conn: sqlite3.Connection, rows: "list[dict]") -> int:
    conn.executemany(
        """
        INSERT INTO ohlcv (symbol, date, open, high, low, close, volume)
        VALUES (:symbol, :date, :open, :high, :low, :close, :volume)
        ON CONFLICT(symbol, date) DO UPDATE SET
            open=excluded.open, high=excluded.high, low=excluded.low,
            close=excluded.close, volume=excluded.volume
        """,
        rows,
    )
    conn.commit()
    return len(rows)


def log_fetch(conn: sqlite3.Connection, source: str, status: str, error: str = None) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO fetch_log (source, fetched_at, status, error) VALUES (?, ?, ?, ?)",
        (source, datetime.now(timezone.utc).isoformat(timespec="seconds"), status, error),
    )
    conn.commit()


def refresh_symbol(conn: sqlite3.Connection, symbol: str, period: str = "2y") -> int:
    """Fetch and store history for one symbol. Logs success/failure to fetch_log."""
    try:
        rows = fetch_ohlcv_history(symbol, period=period)
        n = upsert_ohlcv(conn, rows)
        log_fetch(conn, f"ohlcv:{symbol}", "ok")
        return n
    except Exception as exc:  # yfinance/network errors shouldn't kill the whole job
        log_fetch(conn, f"ohlcv:{symbol}", "error", str(exc))
        return 0
