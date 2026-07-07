import sqlite3

from flask import current_app, g


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE_PATH"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def connect(database_path) -> sqlite3.Connection:
    """Standalone connection for scripts/jobs that run outside a Flask app context."""
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection, schema_path) -> None:
    with open(schema_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    migrate(conn)


def migrate(conn: sqlite3.Connection) -> None:
    """Small additive migrations for DBs created before a column existed."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(journal_entry)").fetchall()}
    if cols and "direction" not in cols:
        conn.execute("ALTER TABLE journal_entry ADD COLUMN direction TEXT NOT NULL DEFAULT 'up'")
        conn.commit()


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
    with app.app_context():
        conn = connect(app.config["DATABASE_PATH"])
        migrate(conn)
        conn.close()
