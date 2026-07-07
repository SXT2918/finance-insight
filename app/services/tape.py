"""Market tape: a handful of live macro quotes, cached briefly so we don't
hammer the data source on every page load."""

import yfinance as yf

from app.services.cache import cache

TAPE_SYMBOLS = [
    ("S&P 500", "^GSPC", 2, False),
    ("NASDAQ", "^IXIC", 2, False),
    ("DOW", "^DJI", 2, False),
    ("RUSSELL 2K", "^RUT", 2, False),
    ("VIX", "^VIX", 2, False),
    ("US 10Y", "^TNX", 3, True),   # yield, shown as %
    ("WTI CRUDE", "CL=F", 2, False),
    ("GOLD", "GC=F", 2, False),
    ("EUR/USD", "EURUSD=X", 4, False),
    ("BTC", "BTC-USD", 0, False),
]

TTL_SECONDS = 600


def _fetch_one(symbol: str):
    df = yf.Ticker(symbol).history(period="5d", interval="1d", auto_adjust=False)
    if len(df) < 2:
        return None
    last = float(df["Close"].iloc[-1])
    prev = float(df["Close"].iloc[-2])
    chg_pct = (last / prev - 1) * 100 if prev else 0.0
    return {"last": last, "chg_pct": chg_pct}


def _fetch_tape():
    items = []
    for label, symbol, decimals, is_yield in TAPE_SYMBOLS:
        quote = _fetch_one(symbol)
        if quote is None:
            items.append({"label": label, "price": "—", "chg_pct": None})
            continue
        price = quote["last"] / 10 if is_yield else quote["last"]  # ^TNX is 10x the yield
        items.append(
            {
                "label": label,
                "price": f"{price:,.{decimals}f}" + ("%" if is_yield else ""),
                "chg_pct": quote["chg_pct"],
            }
        )
    return items


def get_tape():
    """Returns (items, is_stale)."""
    return cache.get_or_fetch("tape", TTL_SECONDS, _fetch_tape)
