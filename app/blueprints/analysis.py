from flask import Blueprint, abort, redirect, render_template, url_for

from app import db
from app.services.analysis_data import get_analysis

bp = Blueprint("analysis", __name__)


@bp.route("/analysis")
def index():
    conn = db.get_db()
    first = conn.execute(
        "SELECT symbol FROM ticker WHERE is_watchlist = 1 ORDER BY symbol LIMIT 1"
    ).fetchone()
    if not first:
        abort(404)
    return redirect(url_for("analysis.ticker", symbol=first["symbol"]))


@bp.route("/analysis/<symbol>")
def ticker(symbol):
    symbol = symbol.upper()
    conn = db.get_db()
    tickers = [
        r["symbol"] for r in conn.execute("SELECT symbol FROM ticker WHERE is_watchlist = 1 ORDER BY symbol")
    ]
    if symbol not in tickers:
        abort(404)

    data = get_analysis(conn, symbol)
    if data is None:
        abort(404)

    return render_template("analysis.html", tickers=tickers, active_symbol=symbol, data=data)
