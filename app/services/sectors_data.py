"""1-month sector performance relative to SPY, for the Sectors heatmap."""

import sqlite3

BENCHMARK = "SPY"
LOOKBACK_SESSIONS = 21  # ~1 trading month, matches watchlist_data's 1M window


def _pct_change_1m(conn: sqlite3.Connection, symbol: str):
    latest = conn.execute(
        "SELECT close FROM ohlcv WHERE symbol = ? ORDER BY date DESC LIMIT 1", (symbol,)
    ).fetchone()
    month_ago = conn.execute(
        "SELECT close FROM ohlcv WHERE symbol = ? ORDER BY date DESC LIMIT 1 OFFSET ?",
        (symbol, LOOKBACK_SESSIONS),
    ).fetchone()
    if not latest or not month_ago:
        return None
    return (latest["close"] / month_ago["close"] - 1) * 100


def get_sector_performance(conn: sqlite3.Connection) -> "list[dict]":
    spy_chg = _pct_change_1m(conn, BENCHMARK)

    etfs = conn.execute("SELECT etf_symbol, sector_name FROM sector_etf ORDER BY sector_name").fetchall()
    rows = []
    for etf in etfs:
        etf_chg = _pct_change_1m(conn, etf["etf_symbol"])
        if etf_chg is None or spy_chg is None:
            rows.append({"symbol": etf["etf_symbol"], "name": etf["sector_name"], "rel_pct": None})
            continue
        rows.append(
            {
                "symbol": etf["etf_symbol"],
                "name": etf["sector_name"],
                "rel_pct": etf_chg - spy_chg,
            }
        )

    rows.sort(key=lambda r: (r["rel_pct"] is None, -(r["rel_pct"] or 0)))
    return rows


def build_heat_note(rows: "list[dict]") -> str:
    scored = [r for r in rows if r["rel_pct"] is not None]
    if len(scored) < 2:
        return "Not enough data yet to summarize sector rotation."
    leader, laggard = scored[0], scored[-1]
    return (
        f"Leadership: {leader['name']} ({leader['rel_pct']:+.1f}% vs SPY) · "
        f"Laggard: {laggard['name']} ({laggard['rel_pct']:+.1f}% vs SPY) — 1-month relative move."
    )
