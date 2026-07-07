from flask import Blueprint, flash, redirect, render_template, request, url_for

from app import db
from app.services import user_portfolio

bp = Blueprint("portfolio", __name__)


def _tradeable_symbols(conn) -> "list[str]":
    return [r["symbol"] for r in conn.execute("SELECT symbol FROM ticker WHERE is_watchlist = 1 ORDER BY symbol")]


def _position_rows(conn):
    rows = []
    for p in user_portfolio.get_open_positions(conn):
        rows.append(dict(p) | {"pnl_pct": user_portfolio.live_pnl_pct(conn, p)})
    return rows


def _trade_rows(conn):
    rows = []
    for t in user_portfolio.get_all_trades(conn):
        pnl = t["pnl_pct"] if t["status"] == "closed" else user_portfolio.live_pnl_pct(conn, t)
        rows.append(dict(t) | {"pnl_pct": pnl})
    return rows


@bp.route("/portfolio")
def index():
    conn = db.get_db()
    user_portfolio.snapshot_nav(conn)  # cheap (price lookups only) - keeps the equity curve current

    return render_template(
        "portfolio.html",
        symbols=_tradeable_symbols(conn),
        cash=user_portfolio.get_cash_balance(conn),
        nav=user_portfolio.compute_nav(conn),
        return_pct=user_portfolio.get_return_pct(conn),
        positions=_position_rows(conn),
        trades=_trade_rows(conn),
        starting_cash=user_portfolio.STARTING_CASH,
    )


@bp.route("/portfolio/buy", methods=["POST"])
def buy():
    conn = db.get_db()
    symbol = request.form.get("symbol", "").upper()
    try:
        size_usd = float(request.form.get("size_usd", 0))
    except ValueError:
        size_usd = 0
    try:
        user_portfolio.buy(conn, symbol, size_usd)
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("portfolio.index"))


@bp.route("/portfolio/close/<int:position_id>", methods=["POST"])
def close(position_id):
    conn = db.get_db()
    try:
        user_portfolio.close_position(conn, position_id)
    except ValueError as exc:
        flash(str(exc), "error")
    return redirect(url_for("portfolio.index"))
