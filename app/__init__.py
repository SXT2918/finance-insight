from flask import Flask, render_template

from app.config import Config
from app import db


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)
    app.config["DATABASE_PATH"] = str(app.config["DATABASE_PATH"])

    db.init_app(app)

    @app.route("/")
    def index():
        conn = db.get_db()
        tickers = conn.execute(
            "SELECT symbol, name FROM ticker WHERE is_watchlist = 1 ORDER BY symbol"
        ).fetchall()
        fetch_log = conn.execute(
            "SELECT source, fetched_at, status FROM fetch_log ORDER BY fetched_at DESC LIMIT 20"
        ).fetchall()
        return render_template("index.html", tickers=tickers, fetch_log=fetch_log)

    return app
