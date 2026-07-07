"""Daily post-close ingestion job.

Phase 1 scope: fetch OHLCV for every ticker (watchlist + sector ETFs + SPY
benchmark) and compute indicators. News/sentiment/brief generation are added
in later phases and will be called from here too.

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

    conn.close()
    print("Done.")


if __name__ == "__main__":
    run()
