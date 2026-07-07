"""Assembles the verified data block fed to every AI prompt (research desk
roles, PM synthesis, scorecard suggestion). Every prompt in this app is
built from this same function so the model only ever sees numbers that
actually came from our database.
"""

import sqlite3

from app.services import indicators as indicators_service
from app.services.price_stats import get_price_and_changes


def get_ticker_context(conn: sqlite3.Connection, symbol: str) -> dict:
    stats = get_price_and_changes(conn, symbol)
    ind = indicators_service.latest(conn, symbol)
    news_rows = conn.execute(
        """
        SELECT n.title, n.source, s.label
        FROM news_item n
        JOIN news_tag t ON t.news_id = n.id
        LEFT JOIN news_sentiment s ON s.news_id = n.id
        WHERE t.tag = ? AND t.tag_type = 'ticker'
        ORDER BY n.published_at DESC LIMIT 6
        """,
        (symbol,),
    ).fetchall()

    return {
        "symbol": symbol,
        "price": stats["price"] if stats else None,
        "d1": stats["d1"] if stats else None,
        "m1": stats["m1"] if stats else None,
        "rsi14": ind["rsi14"] if ind else None,
        "macd": ind["macd"] if ind else None,
        "macd_signal": ind["macd_signal"] if ind else None,
        "sma50": ind["sma50"] if ind else None,
        "sma200": ind["sma200"] if ind else None,
        "news": [{"title": r["title"], "source": r["source"], "sentiment": r["label"] or "unscored"} for r in news_rows],
    }


def format_context_block(ctx: dict) -> str:
    def fmt(v, spec="{:.2f}"):
        return spec.format(v) if v is not None else "n/a"

    lines = [
        f"Ticker: {ctx['symbol']}",
        f"Price: ${fmt(ctx['price'])}",
        f"1-day change: {fmt(ctx['d1'])}%",
        f"1-month change: {fmt(ctx['m1'])}%",
        f"RSI(14): {fmt(ctx['rsi14'], '{:.0f}')}",
        f"MACD: {fmt(ctx['macd'])} (signal: {fmt(ctx['macd_signal'])})",
        f"50-day SMA: ${fmt(ctx['sma50'])}",
        f"200-day SMA: ${fmt(ctx['sma200'])}",
    ]
    if ctx["news"]:
        lines.append("Recent tagged headlines:")
        lines += [f"- [{n['sentiment']}] {n['title']} ({n['source']})" for n in ctx["news"]]
    else:
        lines.append("Recent tagged headlines: none available.")
    return "\n".join(lines)
