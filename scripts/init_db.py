"""Create the SQLite database, apply schema.sql, and sync starter tickers.

Idempotent: re-running this after editing STARTER_WATCHLIST will add new
tickers, update names/sectors, and un-watchlist anything removed from the
list (their price history and other rows are left alone).

Usage: python scripts/init_db.py
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db
from app.config import Config

# ~29 stocks spanning sectors, so the Watchlist/Analysis/News pages have
# real breadth instead of just a handful of mega-cap tech names.
STARTER_WATCHLIST = [
    # Technology
    ("AAPL", "Apple", "Technology"),
    ("MSFT", "Microsoft", "Technology"),
    ("NVDA", "NVIDIA", "Technology"),
    ("GOOGL", "Alphabet", "Technology"),
    ("META", "Meta Platforms", "Technology"),
    ("AVGO", "Broadcom", "Technology"),
    # Consumer Discretionary
    ("AMZN", "Amazon", "Consumer Discretionary"),
    ("TSLA", "Tesla", "Consumer Discretionary"),
    ("HD", "Home Depot", "Consumer Discretionary"),
    ("MCD", "McDonald's", "Consumer Discretionary"),
    # Financials
    ("JPM", "JPMorgan Chase", "Financials"),
    ("BAC", "Bank of America", "Financials"),
    ("GS", "Goldman Sachs", "Financials"),
    ("V", "Visa", "Financials"),
    # Health Care
    ("UNH", "UnitedHealth Group", "Health Care"),
    ("JNJ", "Johnson & Johnson", "Health Care"),
    ("LLY", "Eli Lilly", "Health Care"),
    ("PFE", "Pfizer", "Health Care"),
    # Energy
    ("XOM", "Exxon Mobil", "Energy"),
    ("CVX", "Chevron", "Energy"),
    # Industrials
    ("BA", "Boeing", "Industrials"),
    ("CAT", "Caterpillar", "Industrials"),
    ("GE", "GE Aerospace", "Industrials"),
    # Consumer Staples
    ("PG", "Procter & Gamble", "Consumer Staples"),
    ("KO", "Coca-Cola", "Consumer Staples"),
    ("WMT", "Walmart", "Consumer Staples"),
    # Communication Services
    ("DIS", "Walt Disney", "Communication Services"),
    ("NFLX", "Netflix", "Communication Services"),
    # Utilities
    ("NEE", "NextEra Energy", "Utilities"),
]

# The 11 SPDR sector ETFs used for the Sectors heatmap (vs SPY).
SECTOR_ETFS = [
    ("XLK", "Technology"),
    ("XLE", "Energy"),
    ("XLF", "Financials"),
    ("XLV", "Health Care"),
    ("XLY", "Consumer Discretionary"),
    ("XLP", "Consumer Staples"),
    ("XLI", "Industrials"),
    ("XLB", "Materials"),
    ("XLRE", "Real Estate"),
    ("XLU", "Utilities"),
    ("XLC", "Communication Services"),
]


def main():
    db_path = Config.DATABASE_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = db.connect(db_path)
    schema_path = Path(__file__).resolve().parent.parent / "app" / "schema.sql"
    db.init_schema(conn, schema_path)

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.executemany(
        """
        INSERT INTO ticker (symbol, name, sector, is_watchlist, added_at) VALUES (?, ?, ?, 1, ?)
        ON CONFLICT(symbol) DO UPDATE SET name = excluded.name, sector = excluded.sector, is_watchlist = 1
        """,
        [(sym, name, sector, now) for sym, name, sector in STARTER_WATCHLIST],
    )
    current_symbols = [sym for sym, _, _ in STARTER_WATCHLIST]
    conn.execute(
        f"UPDATE ticker SET is_watchlist = 0 WHERE is_watchlist = 1 AND symbol NOT IN ({','.join('?' * len(current_symbols))})",
        current_symbols,
    )
    conn.executemany(
        "INSERT OR IGNORE INTO sector_etf (etf_symbol, sector_name) VALUES (?, ?)",
        SECTOR_ETFS,
    )
    conn.commit()

    n_tickers = conn.execute("SELECT COUNT(*) FROM ticker WHERE is_watchlist = 1").fetchone()[0]
    n_sectors = conn.execute("SELECT COUNT(*) FROM sector_etf").fetchone()[0]
    print(f"Initialized {db_path}")
    print(f"  watchlist tickers: {n_tickers}, sector ETFs: {n_sectors}")
    conn.close()


if __name__ == "__main__":
    main()
