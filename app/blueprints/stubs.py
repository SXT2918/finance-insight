"""Placeholder routes for pages not yet built, so nav links resolve.
Each of these is replaced by a real blueprint in its own phase."""

from flask import Blueprint, render_template

sectors_bp = Blueprint("sectors", __name__)
analysis_bp = Blueprint("analysis", __name__)
brief_bp = Blueprint("brief", __name__)
journal_bp = Blueprint("journal", __name__)


@sectors_bp.route("/sectors")
def index():
    return render_template("coming_soon.html", page_title="Sectors")


@analysis_bp.route("/analysis")
def index():
    return render_template("coming_soon.html", page_title="Analysis")


@brief_bp.route("/brief")
def index():
    return render_template("coming_soon.html", page_title="Daily brief")


@journal_bp.route("/journal")
def index():
    return render_template("coming_soon.html", page_title="Journal")
