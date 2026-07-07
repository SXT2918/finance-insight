from datetime import date

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from app import db
from app.services import agent, journal_data

bp = Blueprint("journal", __name__)


def _trade_rows(conn):
    rows = []
    for t in agent.get_all_trades(conn):
        pnl = t["pnl_pct"] if t["status"] == "closed" else agent.live_pnl_pct(conn, t)
        rows.append(dict(t) | {"pnl_pct": pnl})
    return rows


@bp.route("/journal")
def index():
    conn = db.get_db()
    entries = journal_data.get_entries(conn)
    stats = journal_data.get_accuracy_stats(conn)
    benchmarks = journal_data.get_benchmark_choices(conn)
    trades = _trade_rows(conn)

    agent.snapshot_nav(conn)  # cheap (price lookups only) - keeps the equity curve current
    agent_return = agent.get_agent_return_pct(conn)
    spy_return = agent.get_spy_return_since_inception(conn)
    your_return = journal_data.get_your_avg_return(conn)

    return render_template(
        "journal.html",
        entries=entries,
        stats=stats,
        benchmarks=benchmarks,
        trades=trades,
        agent_return=agent_return,
        spy_return=spy_return,
        your_return=your_return,
        today=date.today().isoformat(),
    )


@bp.route("/journal/add", methods=["POST"])
def add():
    conn = db.get_db()
    thesis = request.form.get("thesis", "").strip()
    logged_date = request.form.get("logged_date") or date.today().isoformat()
    benchmark = request.form.get("benchmark", "")
    direction = request.form.get("direction", "up")
    try:
        horizon_days = int(request.form.get("horizon_days", 30))
    except ValueError:
        horizon_days = 30

    if thesis and benchmark:
        journal_data.add_entry(conn, thesis, logged_date, benchmark, horizon_days, direction)
    else:
        flash("A thesis and benchmark are required to log a call.", "error")
    return redirect(url_for("journal.index"))


@bp.route("/journal/agent/run", methods=["POST"])
def agent_run():
    conn = db.get_db()
    try:
        result = agent.run_agent(conn, current_app.config["ANTHROPIC_API_KEY"])
        if result is None and not agent.already_traded_today(conn):
            flash("Agent had nothing safe to execute today.", "error")
    except Exception as exc:
        flash(f"Agent run failed: {exc}", "error")
    return redirect(url_for("journal.index"))
