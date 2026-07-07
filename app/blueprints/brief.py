from flask import Blueprint, current_app, flash, redirect, render_template, url_for

from app import db
from app.services import ai_brief
from app.services.macro_calendar import get_upcoming_events
from app.services.sentiment import score_title

bp = Blueprint("brief", __name__)


def _news_list(conn, limit=30):
    rows = conn.execute(
        """
        SELECT n.id, n.title, n.source, n.published_at, s.label
        FROM news_item n
        JOIN news_tag t ON t.news_id = n.id
        LEFT JOIN news_sentiment s ON s.news_id = n.id
        WHERE t.tag_type IN ('ticker', 'sector')
        GROUP BY n.id
        ORDER BY n.published_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    out = []
    for r in rows:
        label = r["label"] or score_title(r["title"])[1]
        out.append({"id": r["id"], "title": r["title"], "source": r["source"], "label": label})
    return out


@bp.route("/brief")
def index():
    conn = db.get_db()
    brief = ai_brief.get_cached_brief(conn)
    news = _news_list(conn)
    events = get_upcoming_events(conn)
    return render_template("brief.html", brief=brief, news=news, events=events)


@bp.route("/brief/generate", methods=["POST"])
def generate():
    conn = db.get_db()
    api_key = current_app.config["ANTHROPIC_API_KEY"]
    try:
        ai_brief.generate_and_store_brief(conn, api_key)
    except Exception as exc:
        flash(f"Couldn't generate today's brief: {exc}", "error")
    return redirect(url_for("brief.index"))
