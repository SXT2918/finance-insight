from flask import Flask

from app.config import Config
from app import db
from app.services.tape import get_tape


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)
    app.config["DATABASE_PATH"] = str(app.config["DATABASE_PATH"])

    db.init_app(app)

    from app.blueprints.dashboard import bp as dashboard_bp
    from app.blueprints.watchlist import bp as watchlist_bp
    from app.blueprints.sectors import bp as sectors_bp
    from app.blueprints.analysis import bp as analysis_bp
    from app.blueprints.brief import bp as brief_bp
    from app.blueprints.media import bp as media_bp
    from app.blueprints.journal import bp as journal_bp
    from app.blueprints.portfolio import bp as portfolio_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(watchlist_bp)
    app.register_blueprint(sectors_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(brief_bp)
    app.register_blueprint(media_bp)
    app.register_blueprint(journal_bp)
    app.register_blueprint(portfolio_bp)

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "finance-insight"}

    @app.context_processor
    def inject_tape():
        items, stale = get_tape()
        return {"tape_items": items, "tape_stale": stale}

    return app
