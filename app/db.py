import sqlite3
from pathlib import Path

from flask import current_app, g


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE_PATH"])
    return g.db


def close_db(_exc=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def connect(database_path) -> sqlite3.Connection:
    """Standalone connection for scripts/jobs that run outside a Flask app context."""
    conn = sqlite3.connect(database_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_schema(conn: sqlite3.Connection, schema_path) -> None:
    with open(schema_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    migrate(conn)


def migrate(conn: sqlite3.Connection) -> None:
    """Small additive migrations for DBs created before a column existed."""
    je_cols = {r["name"] for r in conn.execute("PRAGMA table_info(journal_entry)").fetchall()}
    if je_cols and "direction" not in je_cols:
        conn.execute("ALTER TABLE journal_entry ADD COLUMN direction TEXT NOT NULL DEFAULT 'up'")
        conn.commit()

    ticker_cols = {r["name"] for r in conn.execute("PRAGMA table_info(ticker)").fetchall()}
    fundamentals_columns = {
        "market_cap": "REAL", "trailing_pe": "REAL", "forward_pe": "REAL",
        "week52_low": "REAL", "week52_high": "REAL", "avg_volume": "INTEGER",
        "target_mean_price": "REAL", "recommendation_key": "TEXT", "dividend_yield": "REAL",
        "fundamentals_updated_at": "TEXT",
    }
    if ticker_cols:
        for col, col_type in fundamentals_columns.items():
            if col not in ticker_cols:
                conn.execute(f"ALTER TABLE ticker ADD COLUMN {col} {col_type}")
        conn.commit()

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS user_trade (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol      TEXT NOT NULL,
            action      TEXT NOT NULL CHECK (action IN ('buy', 'close')),
            trade_date  TEXT NOT NULL,
            size_usd    REAL NOT NULL,
            fill_price  REAL NOT NULL,
            shares      REAL NOT NULL,
            status      TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed')),
            pnl_pct     REAL,
            created_at  TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS user_nav (
            date  TEXT PRIMARY KEY,
            nav   REAL NOT NULL
        );
        """
    )
    conn.commit()


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
    with app.app_context():
        database_path = Path(app.config["DATABASE_PATH"])
        database_path.parent.mkdir(parents=True, exist_ok=True)
        conn = connect(database_path)
        has_schema = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ticker'"
        ).fetchone()
        if has_schema:
            migrate(conn)
        else:
            init_schema(conn, Path(__file__).with_name("schema.sql"))
        conn.close()
