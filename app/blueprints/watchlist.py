from flask import Blueprint, render_template

from app import db
from app.services.watchlist_data import build_watchlist_rows

bp = Blueprint("watchlist", __name__)


@bp.route("/watchlist")
def index():
    conn = db.get_db()
    rows = build_watchlist_rows(conn)
    return render_template("watchlist.html", rows=rows)
