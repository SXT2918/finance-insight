"""Compute RSI(14), MACD, and SMA50/200 from stored OHLCV closes.

All figures come from our own stored prices — never invented or pulled from
model memory. These are the numbers fed to the AI research desk prompts.
"""

import sqlite3

import pandas as pd


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(100)


def _macd(close: pd.Series):
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal


def compute_for_symbol(conn: sqlite3.Connection, symbol: str) -> int:
    """Compute indicators for every date we have OHLCV for and upsert them."""
    df = pd.read_sql_query(
        "SELECT date, close FROM ohlcv WHERE symbol = ? ORDER BY date", conn, params=(symbol,)
    )
    if df.empty:
        return 0

    close = df["close"]
    df["rsi14"] = _rsi(close)
    df["macd"], df["macd_signal"] = _macd(close)
    df["sma50"] = close.rolling(window=50, min_periods=50).mean()
    df["sma200"] = close.rolling(window=200, min_periods=200).mean()

    rows = [
        {
            "symbol": symbol,
            "date": r.date,
            "rsi14": None if pd.isna(r.rsi14) else float(r.rsi14),
            "macd": None if pd.isna(r.macd) else float(r.macd),
            "macd_signal": None if pd.isna(r.macd_signal) else float(r.macd_signal),
            "sma50": None if pd.isna(r.sma50) else float(r.sma50),
            "sma200": None if pd.isna(r.sma200) else float(r.sma200),
        }
        for r in df.itertuples()
    ]

    conn.executemany(
        """
        INSERT INTO indicator (symbol, date, rsi14, macd, macd_signal, sma50, sma200)
        VALUES (:symbol, :date, :rsi14, :macd, :macd_signal, :sma50, :sma200)
        ON CONFLICT(symbol, date) DO UPDATE SET
            rsi14=excluded.rsi14, macd=excluded.macd, macd_signal=excluded.macd_signal,
            sma50=excluded.sma50, sma200=excluded.sma200
        """,
        rows,
    )
    conn.commit()
    return len(rows)


def latest(conn: sqlite3.Connection, symbol: str) -> "sqlite3.Row | None":
    return conn.execute(
        "SELECT * FROM indicator WHERE symbol = ? ORDER BY date DESC LIMIT 1", (symbol,)
    ).fetchone()
