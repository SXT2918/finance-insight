"""WSGI entrypoint for production servers (gunicorn, etc.).

Local development still uses `flask run` / `flask --app app run`, which calls
create_app() itself. This file exists only for `gunicorn wsgi:app`.
"""

from app import create_app

app = create_app()
