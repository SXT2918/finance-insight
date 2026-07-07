"""User-facing paper-trading simulator: $10,000 fake cash, real prices,
no real money anywhere. Mechanically mirrors the AI agent's portfolio
(app/services/agent.py) but trades are placed manually via the Portfolio
page rather than proposed by the model. Fills use the latest stored
closing price - not live intraday execution.
"""

import sqlite3
from datetime import date, datetime, timezone

STARTING_CASH = 10000.0


def get_open_positions(conn: sqlite3.Connection) -> "list[sqlite3.Row]":
    return conn.execute(
        "SELECT * FROM user_trade WHERE action = 'buy' AND status = 'open' ORDER BY trade_date"
    ).fetchall()


def get_all_trades(conn: sqlite3.Connection) -> "list[sqlite3.Row]":
    return conn.execute("SELECT * FROM user_trade ORDER BY trade_date DESC, id DESC").fetchall()


def _latest_price(conn: sqlite3.Connection, symbol: str) -> "float | None":
    row = conn.execute("SELECT close FROM ohlcv WHERE symbol = ? ORDER BY date DESC LIMIT 1", (symbol,)).fetchone()
    return row["close"] if row else None


def live_pnl_pct(conn: sqlite3.Connection, position: sqlite3.Row) -> "float | None":
    price = _latest_price(conn, position["symbol"])
    if price is None:
        return None
    return (price / position["fill_price"] - 1) * 100


def get_cash_balance(conn: sqlite3.Connection) -> float:
    bought = conn.execute("SELECT COALESCE(SUM(size_usd), 0) v FROM user_trade WHERE action = 'buy'").fetchone()["v"]
    realized = conn.execute(
        "SELECT COALESCE(SUM(size_usd * (1 + pnl_pct / 100.0)), 0) v FROM user_trade WHERE action = 'close'"
    ).fetchone()["v"]
    return STARTING_CASH - bought + realized


def compute_nav(conn: sqlite3.Connection) -> float:
    cash = get_cash_balance(conn)
    open_value = 0.0
    for pos in get_open_positions(conn):
        price = _latest_price(conn, pos["symbol"])
        if price is not None:
            open_value += pos["shares"] * price
    return cash + open_value


def snapshot_nav(conn: sqlite3.Connection) -> float:
    nav = compute_nav(conn)
    today = date.today().isoformat()
    conn.execute(
        "INSERT INTO user_nav (date, nav) VALUES (?, ?) ON CONFLICT(date) DO UPDATE SET nav = excluded.nav",
        (today, nav),
    )
    conn.commit()
    return nav


def get_nav_history(conn: sqlite3.Connection) -> "list[sqlite3.Row]":
    return conn.execute("SELECT date, nav FROM user_nav ORDER BY date").fetchall()


def get_return_pct(conn: sqlite3.Connection) -> "float | None":
    history = get_nav_history(conn)
    if not history:
        return None
    return (history[-1]["nav"] / STARTING_CASH - 1) * 100


def buy(conn: sqlite3.Connection, symbol: str, size_usd: float) -> None:
    if size_usd <= 0:
        raise ValueError("Enter a dollar amount greater than $0.")
    price = _latest_price(conn, symbol)
    if price is None:
        raise ValueError(f"No price data for {symbol} yet.")
    cash = get_cash_balance(conn)
    if size_usd > cash:
        raise ValueError(f"Only ${cash:,.2f} in simulated cash available.")

    shares = size_usd / price
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    today = date.today().isoformat()
    conn.execute(
        """
        INSERT INTO user_trade (symbol, action, trade_date, size_usd, fill_price, shares, status, pnl_pct, created_at)
        VALUES (?, 'buy', ?, ?, ?, ?, 'open', NULL, ?)
        """,
        (symbol, today, size_usd, price, shares, now),
    )
    conn.commit()
    snapshot_nav(conn)


def close_position(conn: sqlite3.Connection, position_id: int) -> None:
    pos = conn.execute(
        "SELECT * FROM user_trade WHERE id = ? AND action = 'buy' AND status = 'open'", (position_id,)
    ).fetchone()
    if pos is None:
        raise ValueError("That position is already closed or doesn't exist.")

    price = _latest_price(conn, pos["symbol"])
    if price is None:
        raise ValueError(f"No current price for {pos['symbol']}.")

    pnl_pct = (price / pos["fill_price"] - 1) * 100
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    today = date.today().isoformat()
    conn.execute("UPDATE user_trade SET status = 'closed' WHERE id = ?", (pos["id"],))
    conn.execute(
        """
        INSERT INTO user_trade (symbol, action, trade_date, size_usd, fill_price, shares, status, pnl_pct, created_at)
        VALUES (?, 'close', ?, ?, ?, ?, 'closed', ?, ?)
        """,
        (pos["symbol"], today, pos["size_usd"], price, pos["shares"], pnl_pct, now),
    )
    conn.commit()
    snapshot_nav(conn)
