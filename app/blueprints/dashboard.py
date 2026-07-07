from flask import Blueprint, jsonify, render_template, request

from app import db
from app.services import chart_data

bp = Blueprint("dashboard", __name__)

INDEX_SYMBOL = "SPY"


@bp.route("/")
def index():
    conn = db.get_db()
    points, stale = chart_data.get_series(conn, INDEX_SYMBOL, "1D")
    return render_template(
        "dashboard.html",
        symbol=INDEX_SYMBOL,
        initial_points=points,
        initial_stale=stale,
    )


@bp.route("/api/chart/<symbol>")
def api_chart(symbol):
    tf = request.args.get("tf", "1D")
    conn = db.get_db()
    points, stale = chart_data.get_series(conn, symbol.upper(), tf)
    return jsonify({"points": points, "stale": stale})
