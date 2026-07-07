"""Image proxy/cache for news thumbnails.

Only ever fetches URLs we already stored in news_item.image_url (sourced
from yfinance, not user input) — never an arbitrary caller-supplied URL —
so this can't be used as an open SSRF proxy. Caches to disk so a slow
source only costs one fetch.
"""

import hashlib
from pathlib import Path

import requests
from flask import Blueprint, current_app, redirect, send_file, url_for

from app import db

bp = Blueprint("media", __name__)

FETCH_TIMEOUT = 5


def _cache_dir() -> Path:
    d = Path(current_app.config["DATABASE_PATH"]).parent / "img_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


@bp.route("/media/news/<int:news_id>/thumb")
def news_thumb(news_id):
    conn = db.get_db()
    row = conn.execute("SELECT image_url FROM news_item WHERE id = ?", (news_id,)).fetchone()
    if not row or not row["image_url"]:
        return redirect(url_for("static", filename="img/thumb-placeholder.svg"))

    url = row["image_url"]
    key = hashlib.sha256(url.encode()).hexdigest()
    cache_dir = _cache_dir()
    data_path = cache_dir / f"{key}.bin"
    ctype_path = cache_dir / f"{key}.ctype"

    if data_path.exists() and ctype_path.exists():
        return send_file(data_path, mimetype=ctype_path.read_text().strip())

    try:
        resp = requests.get(url, timeout=FETCH_TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        ctype = resp.headers.get("Content-Type", "image/jpeg").split(";")[0]
        data_path.write_bytes(resp.content)
        ctype_path.write_text(ctype)
        return send_file(data_path, mimetype=ctype)
    except Exception:
        return redirect(url_for("static", filename="img/thumb-placeholder.svg"))
