"""Create the SQLite database, apply schema.sql, and seed starter tickers.

Usage: python scripts/init_db.py
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import db
from app.config import Config

STARTER_WATCHLIST = [
    ("NVDA", "NVIDIA", "Technology"),
    ("AAPL", "Apple", "Technology"),
    ("MSFT", "Microsoft", "Technology"),
    ("TSLA", "Tesla", "Consumer Discretionary"),
    ("JPM", "JPMorgan Chase", "Financials"),
    ("XLE", "Energy Select Sector SPDR", "Energy"),
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
        "INSERT OR IGNORE INTO ticker (symbol, name, sector, is_watchlist, added_at) VALUES (?, ?, ?, 1, ?)",
        [(sym, name, sector, now) for sym, name, sector in STARTER_WATCHLIST],
    )
    conn.executemany(
        "INSERT OR IGNORE INTO sector_etf (etf_symbol, sector_name) VALUES (?, ?)",
        SECTOR_ETFS,
    )
    conn.commit()

    n_tickers = conn.execute("SELECT COUNT(*) FROM ticker").fetchone()[0]
    n_sectors = conn.execute("SELECT COUNT(*) FROM sector_etf").fetchone()[0]
    print(f"Initialized {db_path}")
    print(f"  tickers: {n_tickers}, sector ETFs: {n_sectors}")
    conn.close()


if __name__ == "__main__":
    main()
