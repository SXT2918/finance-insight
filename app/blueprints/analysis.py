from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for

from app import db
from app.services import ai_desk, scorecard_data
from app.services.analysis_data import get_analysis

bp = Blueprint("analysis", __name__)


def _watchlist_tickers(conn) -> "list[str]":
    return [r["symbol"] for r in conn.execute("SELECT symbol FROM ticker WHERE is_watchlist = 1 ORDER BY symbol")]


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
    tickers = _watchlist_tickers(conn)
    if symbol not in tickers:
        abort(404)

    data = get_analysis(conn, symbol)
    if data is None:
        abort(404)

    desk = ai_desk.get_cached_desk_report(conn, symbol)
    scorecard = scorecard_data.get_scorecard(conn, symbol)

    return render_template(
        "analysis.html", tickers=tickers, active_symbol=symbol, data=data, desk=desk, scorecard=scorecard
    )


@bp.route("/analysis/<symbol>/desk/generate", methods=["POST"])
def desk_generate(symbol):
    symbol = symbol.upper()
    conn = db.get_db()
    try:
        ai_desk.generate_desk_report(conn, symbol, current_app.config["ANTHROPIC_API_KEY"])
    except Exception as exc:
        flash(f"Couldn't generate the desk report: {exc}", "error")
    return redirect(url_for("analysis.ticker", symbol=symbol))


@bp.route("/analysis/<symbol>/scorecard/save", methods=["POST"])
def scorecard_save(symbol):
    symbol = symbol.upper()
    conn = db.get_db()
    scores = {}
    for key, _, _ in scorecard_data.DIMENSIONS:
        raw = request.form.get(key)
        if raw is not None and raw != "":
            scores[key] = int(raw)
    scorecard_data.save_user_scores(conn, symbol, scores)
    return redirect(url_for("analysis.ticker", symbol=symbol))


@bp.route("/analysis/<symbol>/scorecard/ai-suggest", methods=["POST"])
def scorecard_ai_suggest(symbol):
    symbol = symbol.upper()
    conn = db.get_db()
    try:
        scorecard_data.generate_ai_scores(conn, symbol, current_app.config["ANTHROPIC_API_KEY"])
    except Exception as exc:
        flash(f"Couldn't get an AI suggestion: {exc}", "error")
    return redirect(url_for("analysis.ticker", symbol=symbol))
