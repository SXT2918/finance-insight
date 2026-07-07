"""Daily post-close ingestion job: prices -> indicators -> news -> sentiment
-> earnings calendar. Daily brief generation is deliberately NOT triggered
here — it's generated on demand from the Brief page to keep control over
when the (paid) Anthropic call happens.

Usage: python jobs/daily_job.py
Schedule (cron, after US market close, ET):
    0 21 * * 1-5 cd /path/to/finance-insight && .venv/bin/python jobs/daily_job.py >> data/cron.log 2>&1
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db
from app.config import Config
from app.services import indicators, market_data
from app.services.fundamentals import refresh_fundamentals_for_watchlist
from app.services.macro_calendar import refresh_earnings_events
from app.services.news import ingest_general_market_news, ingest_news_for_watchlist
from app.services.sentiment import score_unscored_news

BENCHMARK = "SPY"


def symbols_to_refresh(conn) -> "list[str]":
    watchlist = [r[0] for r in conn.execute("SELECT symbol FROM ticker WHERE is_watchlist = 1")]
    sector_etfs = [r[0] for r in conn.execute("SELECT etf_symbol FROM sector_etf")]
    symbols = list(dict.fromkeys(watchlist + sector_etfs + [BENCHMARK]))
    return symbols


def run():
    conn = db.connect(Config.DATABASE_PATH)
    symbols = symbols_to_refresh(conn)
    print(f"Refreshing {len(symbols)} symbols: {', '.join(symbols)}")

    for sym in symbols:
        n = market_data.refresh_symbol(conn, sym)
        m = indicators.compute_for_symbol(conn, sym)
        print(f"  {sym}: {n} price rows, {m} indicator rows")
        time.sleep(0.3)  # be polite to the data source

    news_count = ingest_news_for_watchlist(conn)
    print(f"News: {news_count} ticker items ingested/refreshed")

    market_news_count = ingest_general_market_news(conn)
    print(f"News: {market_news_count} general market items ingested/refreshed")

    scored = score_unscored_news(conn)
    print(f"Sentiment: scored {scored} new headlines")

    events = refresh_earnings_events(conn)
    print(f"Macro calendar: {events} upcoming earnings events")

    fundamentals_count = refresh_fundamentals_for_watchlist(conn)
    print(f"Fundamentals: refreshed {fundamentals_count} tickers")

    conn.close()
    print("Done.")


if __name__ == "__main__":
    run()
