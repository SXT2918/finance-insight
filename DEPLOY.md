# Deploying finance-insight to Render

This is a real Flask app with a persistent SQLite database and a daily background job —
none of that runs on Cloudflare Workers, which is why the earlier attempt there failed.
Render gives it an actual Python process, a persistent disk, and a shell to run one-off
commands against that same disk.

## 1. First deploy

1. https://dashboard.render.com → **New +** → **Blueprint**.
2. Connect the `SXT2918/finance-insight` GitHub repo. Render reads `render.yaml` at the
   repo root automatically.
3. When prompted for `ANTHROPIC_API_KEY` (marked `sync: false` in the blueprint, so Render
   asks rather than storing a default), paste your key from https://console.anthropic.com/.
   `FLASK_SECRET_KEY` is auto-generated; you don't need to fill it in.
4. **Apply**. This provisions the web service and a 1GB persistent disk mounted at
   `/var/data`, and starts `gunicorn --workers 1 --threads 4 wsgi:app`.

## 2. Optional one-time step: seed the starter watchlist

The application creates an empty schema automatically on first start. Run the following
step once if you want to seed the starter watchlist and sector ETFs.

Once the first deploy is live, open the service in the Render dashboard → **Shell** tab
(or **Jobs** → run a one-off command, both share the service's disk and environment) and run:

```
python scripts/init_db.py
```

This creates the schema and seeds the 29-stock starter watchlist plus the 11 sector ETFs.
It's idempotent — safe to re-run later after editing `STARTER_WATCHLIST`.

## 3. Running the daily ingestion job

`jobs/daily_job.py` refreshes prices, indicators, news, sentiment, and the earnings
calendar. It is **not scheduled automatically yet** — Render's Cron Job service type
can't mount the same persistent disk as a Web Service, so it can't safely share the
SQLite file with the running app. Until that's decided, run it manually the same way:

```
python jobs/daily_job.py
```

via the same Shell/Jobs feature, whenever you want fresh data (e.g., once after market
close).

**When you're ready to automate it**, the two realistic options are:
- An in-process scheduler (e.g., APScheduler) started inside `create_app()`, gated to a
  single gunicorn worker so the job can't run twice concurrently.
- A tiny authenticated HTTP endpoint on this same service (e.g., `POST /internal/run-daily-job`
  behind a shared-secret header) triggered by an external, disk-less cron caller —
  Render Cron Job, GitHub Actions on a schedule, or a free service like cron-job.org.

Either is a small, deliberate change — worth deciding rather than defaulting into, since it
changes how failures show up (a stuck request vs. a silent background thread).

## 4. Notes

- `plan: starter` in `render.yaml` is Render's smallest paid tier (needed for the
  persistent disk — free web services don't support disks). Check current pricing before
  deploying.
- `--workers 1` in the start command is deliberate: `app/db.py` opens a plain `sqlite3`
  connection with no WAL mode, so more than one process writing at once risks
  "database is locked" errors. `--threads 4` still gives real concurrency for reads.
- `data/*.db`, `data/img_cache/`, and `.venv/` stay out of git (see `.gitignore`) — they're
  either generated or, for the database, meant to live only on the persistent disk, not in
  source control.
