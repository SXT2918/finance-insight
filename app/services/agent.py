"""AI paper-trading agent: fake cash, real prices. Proposes at most one
trade per day (buy a new watchlist name or close an existing position),
reasoning stored alongside the trade. NAV is snapshotted on every Journal
page view (cheap - just price lookups, no API call) so the equity curve
builds up over time even on days the agent itself isn't run.
"""

import json
import re
import sqlite3
from datetime import date, datetime, timezone

import anthropic

from app.services.ticker_context import format_context_block, get_ticker_context

MODEL = "claude-haiku-4-5-20251001"
STARTING_CASH = 1000.0
TRADE_SIZE_USD = 50.0


def get_open_positions(conn: sqlite3.Connection) -> "list[sqlite3.Row]":
    return conn.execute(
        "SELECT * FROM agent_trade WHERE action = 'buy' AND status = 'open' ORDER BY trade_date"
    ).fetchall()


def get_all_trades(conn: sqlite3.Connection) -> "list[sqlite3.Row]":
    return conn.execute("SELECT * FROM agent_trade ORDER BY trade_date DESC, id DESC").fetchall()


def _latest_price(conn: sqlite3.Connection, symbol: str) -> "float | None":
    row = conn.execute("SELECT close FROM ohlcv WHERE symbol = ? ORDER BY date DESC LIMIT 1", (symbol,)).fetchone()
    return row["close"] if row else None


def live_pnl_pct(conn: sqlite3.Connection, position: sqlite3.Row) -> "float | None":
    price = _latest_price(conn, position["symbol"])
    if price is None:
        return None
    return (price / position["fill_price"] - 1) * 100


def get_cash_balance(conn: sqlite3.Connection) -> float:
    bought = conn.execute("SELECT COALESCE(SUM(size_usd), 0) v FROM agent_trade WHERE action = 'buy'").fetchone()["v"]
    realized = conn.execute(
        "SELECT COALESCE(SUM(size_usd * (1 + pnl_pct / 100.0)), 0) v FROM agent_trade WHERE action = 'close'"
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
        "INSERT INTO agent_nav (date, nav) VALUES (?, ?) ON CONFLICT(date) DO UPDATE SET nav = excluded.nav",
        (today, nav),
    )
    conn.commit()
    return nav


def get_nav_history(conn: sqlite3.Connection) -> "list[sqlite3.Row]":
    return conn.execute("SELECT date, nav FROM agent_nav ORDER BY date").fetchall()


def get_agent_return_pct(conn: sqlite3.Connection) -> "float | None":
    history = get_nav_history(conn)
    if not history:
        return None
    return (history[-1]["nav"] / STARTING_CASH - 1) * 100


def get_spy_return_since_inception(conn: sqlite3.Connection) -> "float | None":
    history = get_nav_history(conn)
    if not history:
        return None
    inception = history[0]["date"]
    start = conn.execute(
        "SELECT close FROM ohlcv WHERE symbol = 'SPY' AND date >= ? ORDER BY date LIMIT 1", (inception,)
    ).fetchone()
    latest = _latest_price(conn, "SPY")
    if not start or latest is None:
        return None
    return (latest / start["close"] - 1) * 100


def already_traded_today(conn: sqlite3.Connection) -> bool:
    today = date.today().isoformat()
    return conn.execute("SELECT 1 FROM agent_trade WHERE trade_date = ? LIMIT 1", (today,)).fetchone() is not None


def _build_prompt(conn: sqlite3.Connection, cash: float, open_positions: "list[sqlite3.Row]") -> "tuple[str, list[str]]":
    watchlist = [r["symbol"] for r in conn.execute("SELECT symbol FROM ticker WHERE is_watchlist = 1")]
    open_symbols = {p["symbol"] for p in open_positions}
    candidates = [s for s in watchlist if s not in open_symbols]

    lines = [f"Simulated cash available: ${cash:.2f}", f"Fixed trade size: ${TRADE_SIZE_USD:.2f}", "", "Watchlist candidates (not currently held):"]
    for sym in candidates:
        lines.append(f"--- {sym} ---")
        lines.append(format_context_block(get_ticker_context(conn, sym)))

    lines.append("\nOpen agent positions:")
    if open_positions:
        for p in open_positions:
            pnl = live_pnl_pct(conn, p)
            pnl_str = f"{pnl:+.1f}%" if pnl is not None else "n/a"
            lines.append(f"- {p['symbol']}: opened {p['trade_date']} at ${p['fill_price']:.2f}, now {pnl_str} (reasoning then: {p['reasoning']})")
    else:
        lines.append("- none")

    prompt = f"""You are the trading agent for Finance Insight's paper portfolio - fake cash, real prices,
purely educational. This is not investment advice. Choose exactly ONE action for today:
- "buy" one candidate symbol not already held, at the fixed trade size, OR
- "close" one existing open position.
Only choose "close" if there is at least one open position listed. Use ONLY the data below -
never invent a price or event. Respond with STRICT JSON only, no markdown fences:
{{"action": "buy" | "close", "symbol": "TICKER", "reasoning": "2-3 sentences"}}

{chr(10).join(lines)}
"""
    return prompt, candidates


def run_agent(conn: sqlite3.Connection, api_key: str) -> "dict | None":
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured")
    if already_traded_today(conn):
        return None

    cash = get_cash_balance(conn)
    open_positions = get_open_positions(conn)
    prompt, candidates = _build_prompt(conn, cash, open_positions)

    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(model=MODEL, max_tokens=250, messages=[{"role": "user", "content": prompt}])
    raw = "".join(b.text for b in resp.content if b.type == "text").strip()
    raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.MULTILINE).strip()
    decision = json.loads(raw)

    action = decision.get("action")
    symbol = (decision.get("symbol") or "").upper()
    reasoning = decision.get("reasoning", "")
    today = date.today().isoformat()

    if action == "buy" and symbol in candidates and cash >= TRADE_SIZE_USD:
        price = _latest_price(conn, symbol)
        if price is None:
            return None
        shares = TRADE_SIZE_USD / price
        conn.execute(
            """
            INSERT INTO agent_trade (symbol, action, trade_date, size_usd, fill_price, shares, reasoning, status, pnl_pct)
            VALUES (?, 'buy', ?, ?, ?, ?, ?, 'open', NULL)
            """,
            (symbol, today, TRADE_SIZE_USD, price, shares, reasoning),
        )
        conn.commit()
    elif action == "close" and symbol in {p["symbol"] for p in open_positions}:
        pos = next(p for p in open_positions if p["symbol"] == symbol)
        price = _latest_price(conn, symbol)
        if price is None:
            return None
        pnl_pct = (price / pos["fill_price"] - 1) * 100
        conn.execute("UPDATE agent_trade SET status = 'closed' WHERE id = ?", (pos["id"],))
        conn.execute(
            """
            INSERT INTO agent_trade (symbol, action, trade_date, size_usd, fill_price, shares, reasoning, status, pnl_pct)
            VALUES (?, 'close', ?, ?, ?, ?, ?, 'closed', ?)
            """,
            (symbol, today, pos["size_usd"], price, pos["shares"], reasoning, pnl_pct),
        )
        conn.commit()
    else:
        return None  # model proposed something we can't safely execute; skip silently

    snapshot_nav(conn)
    return {"action": action, "symbol": symbol, "reasoning": reasoning}
