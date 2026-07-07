from flask import Blueprint, render_template

from app import db
from app.services.sectors_data import build_heat_note, get_sector_performance

bp = Blueprint("sectors", __name__)


@bp.route("/sectors")
def index():
    conn = db.get_db()
    rows = get_sector_performance(conn)
    return render_template("sectors.html", rows=rows, heat_note=build_heat_note(rows))
