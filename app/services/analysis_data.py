"""Auto-assembles indicator chips and a bull/bear case from stored, real
indicator values. Never invents numbers — every claim traces back to a
column in `indicator`/`ohlcv`. News-driven points join once ingestion for
that exists (Phase 5+).
"""

import sqlite3

from app.services import indicators as indicators_service
from app.services.price_stats import get_price_and_changes

RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30


def get_analysis(conn: sqlite3.Connection, symbol: str):
    stats = get_price_and_changes(conn, symbol)
    ind = indicators_service.latest(conn, symbol)
    if stats is None or ind is None:
        return None

    price, m1 = stats["price"], stats["m1"]
    rsi, macd, macd_signal = ind["rsi14"], ind["macd"], ind["macd_signal"]
    sma50, sma200 = ind["sma50"], ind["sma200"]
    macd_hist = macd - macd_signal if macd is not None and macd_signal is not None else None

    chips = []
    bull = []
    bear = []

    if rsi is not None:
        if rsi >= RSI_OVERBOUGHT:
            chips.append((f"RSI {rsi:.0f}", "warn"))
            bear.append(f"RSI at {rsi:.0f} is in overbought territory — stretched readings have often preceded pullbacks.")
        elif rsi <= RSI_OVERSOLD:
            chips.append((f"RSI {rsi:.0f}", "warn"))
            bull.append(f"RSI at {rsi:.0f} is oversold, which raises the odds of a mean-reversion bounce.")
            bear.append(f"RSI at {rsi:.0f} confirms real selling pressure is still behind the move.")
        else:
            chips.append((f"RSI {rsi:.0f}", ""))
    else:
        chips.append(("RSI n/a", ""))

    if macd_hist is not None:
        if macd_hist > 0:
            chips.append(("MACD +", "good"))
            bull.append("MACD sits above its signal line, in line with upward momentum.")
        elif macd_hist < 0:
            chips.append(("MACD −", "bad"))
            bear.append("MACD sits below its signal line, reflecting fading momentum.")
        else:
            chips.append(("MACD flat", ""))
    else:
        chips.append(("MACD n/a", ""))

    if sma50 is not None:
        if price > sma50:
            chips.append(("Above 50D", "good"))
            bull.append(f"Price (${price:.2f}) is trading above its 50-day average (${sma50:.2f}).")
        else:
            chips.append(("Below 50D", "bad"))
            bear.append(f"Price (${price:.2f}) is trading below its 50-day average (${sma50:.2f}) — sellers control the trend.")
    else:
        chips.append(("50D n/a", ""))

    if sma50 is not None and sma200 is not None:
        if sma50 > sma200:
            chips.append(("50D > 200D", "good"))
            bull.append("The 50-day average sits above the 200-day — a longer-term uptrend structure.")
        else:
            chips.append(("50D < 200D", "bad"))
            bear.append("The 50-day average sits below the 200-day — a longer-term downtrend structure.")

    if m1 is not None:
        if m1 > 0:
            bull.append(f"Up {m1:.1f}% over the past month.")
        else:
            bear.append(f"Down {abs(m1):.1f}% over the past month.")

    if not bull:
        bull.append("No bullish technical signal from current indicators — the case will strengthen once tagged news is in.")
    if not bear:
        bear.append("No bearish technical signal from current indicators — the case will strengthen once tagged news is in.")

    return {
        "symbol": symbol,
        "price": price,
        "chips": chips,
        "bull": bull,
        "bear": bear,
    }
