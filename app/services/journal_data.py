"""Prediction journal: user logs a thesis against a benchmark ticker and a
horizon; once the horizon elapses, the call is auto-scored hit/miss against
real stored prices. Never scored by hand, never invented.
"""

import sqlite3
from datetime import date, datetime, timedelta, timezone


def get_benchmark_choices(conn: sqlite3.Connection) -> "list[str]":
    watchlist = [r["symbol"] for r in conn.execute("SELECT symbol FROM ticker WHERE is_watchlist = 1")]
    sectors = [r["etf_symbol"] for r in conn.execute("SELECT etf_symbol FROM sector_etf")]
    return sorted(set(watchlist + sectors + ["SPY"]))


def add_entry(conn: sqlite3.Connection, thesis: str, logged_date: str, benchmark: str, horizon_days: int, direction: str) -> None:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.execute(
        """
        INSERT INTO journal_entry (thesis, logged_date, benchmark, horizon_days, direction, status, result_pct, created_at)
        VALUES (?, ?, ?, ?, ?, 'open', NULL, ?)
        """,
        (thesis, logged_date, benchmark, horizon_days, direction, now),
    )
    conn.commit()


def _price_on_or_after(conn: sqlite3.Connection, symbol: str, target_date: str):
    return conn.execute(
        "SELECT close FROM ohlcv WHERE symbol = ? AND date >= ? ORDER BY date LIMIT 1", (symbol, target_date)
    ).fetchone()


def _latest_price(conn: sqlite3.Connection, symbol: str):
    return conn.execute("SELECT close FROM ohlcv WHERE symbol = ? ORDER BY date DESC LIMIT 1", (symbol,)).fetchone()


def rescore_open_entries(conn: sqlite3.Connection) -> None:
    today = date.today()
    for r in conn.execute("SELECT * FROM journal_entry WHERE status = 'open'").fetchall():
        start = _price_on_or_after(conn, r["benchmark"], r["logged_date"])
        latest = _latest_price(conn, r["benchmark"])
        if not start or not latest:
            continue
        change = (latest["close"] / start["close"] - 1) * 100
        due = date.fromisoformat(r["logged_date"]) + timedelta(days=r["horizon_days"])
        if today >= due:
            hit = (change > 0) if r["direction"] == "up" else (change < 0)
            conn.execute(
                "UPDATE journal_entry SET status = ?, result_pct = ? WHERE id = ?",
                ("hit" if hit else "miss", change, r["id"]),
            )
        else:
            conn.execute("UPDATE journal_entry SET result_pct = ? WHERE id = ?", (change, r["id"]))
    conn.commit()


def get_entries(conn: sqlite3.Connection) -> "list[sqlite3.Row]":
    rescore_open_entries(conn)
    return conn.execute("SELECT * FROM journal_entry ORDER BY logged_date DESC").fetchall()


def get_accuracy_stats(conn: sqlite3.Connection) -> dict:
    rows = conn.execute("SELECT status FROM journal_entry").fetchall()
    hit = sum(1 for r in rows if r["status"] == "hit")
    miss = sum(1 for r in rows if r["status"] == "miss")
    open_n = sum(1 for r in rows if r["status"] == "open")
    scored = hit + miss
    return {
        "hit": hit, "miss": miss, "open": open_n, "total": len(rows),
        "accuracy_pct": (hit / scored * 100) if scored else None,
    }


def get_your_avg_return(conn: sqlite3.Connection) -> "float | None":
    rows = conn.execute(
        "SELECT result_pct FROM journal_entry WHERE status IN ('hit', 'miss') AND result_pct IS NOT NULL"
    ).fetchall()
    if not rows:
        return None
    values = [r["result_pct"] for r in rows]
    return sum(values) / len(values)
