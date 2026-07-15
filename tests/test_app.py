from pathlib import Path

from app import create_app
from app import db


class TestConfig:
    TESTING = True
    SECRET_KEY = "test-only"
    DATABASE_PATH = ""
    ANTHROPIC_API_KEY = ""
    QUOTE_STALE_AFTER_HOURS = 24
    NEWS_STALE_AFTER_HOURS = 24


def test_app_bootstraps_schema_and_health_endpoint(tmp_path: Path):
    TestConfig.DATABASE_PATH = tmp_path / "test.sqlite3"
    app = create_app(TestConfig)
    response = app.test_client().get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"
    assert TestConfig.DATABASE_PATH.exists()

    conn = db.connect(TestConfig.DATABASE_PATH)
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    assert conn.execute("SELECT COUNT(*) FROM ticker").fetchone()[0] == 0
    conn.close()
