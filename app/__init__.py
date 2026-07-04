import os
from flask import Flask, flash

from app.extensions import limiter
from app.db.database import init_schema


REQUIRED_ENV = ["JWT_SECRET"]


def create_app():
    missing = [key for key in REQUIRED_ENV if not os.environ.get(key)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    if not os.environ.get("OWNER_USERNAME") or not os.environ.get("OWNER_PASSWORD"):
        print(
            "WARNING: OWNER_USERNAME / OWNER_PASSWORD are not set - the personal "
            "owner login will be disabled until they are."
        )

    app = Flask(__name__)
    app.secret_key = os.environ["JWT_SECRET"]  # reused for flash() session signing

    init_schema()
    limiter.init_app(app)

    from app.routes import auth, board, marketing, titles, owner

    app.register_blueprint(marketing.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(board.bp)
    app.register_blueprint(titles.bp)
    app.register_blueprint(owner.bp)

    @app.context_processor
    def inject_current_user():
        from app.utils.current_user import get_current_user
        return {"current_user": get_current_user()}

    @app.template_filter("dateonly")
    def dateonly(value):
        if not value:
            return ""
        if hasattr(value, "strftime"):
            return value.strftime("%Y-%m-%d")
        return str(value)[:10]

    @app.template_filter("relative_time")
    def relative_time(value):
        if not value:
            return "Never"
        import datetime as _dt
        dt = value if hasattr(value, "strftime") else None
        if dt is None:
            try:
                dt = _dt.datetime.fromisoformat(str(value)[:26].replace(" ", "T"))
            except ValueError:
                return str(value)
        if hasattr(dt, "tzinfo") and dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        seconds = (_dt.datetime.utcnow() - dt).total_seconds()
        if seconds < 60:
            return "Just now"
        if seconds < 3600:
            minutes = int(seconds // 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        if seconds < 86400:
            hours = int(seconds // 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        days = int(seconds // 86400)
        if days < 30:
            return f"{days} day{'s' if days != 1 else ''} ago"
        return dt.strftime("%Y-%m-%d")

    @app.route("/healthz")
    def health():
        from app.db.database import get_backend_name
        return {"ok": True, "app": "WatchBoard", "author": "Girish D. Sakpal", "db": get_backend_name()}

    @app.errorhandler(404)
    def handle_404(e):
        from flask import render_template
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def handle_500(e):
        from flask import render_template
        app.logger.exception("Unhandled error")
        return render_template("500.html"), 500

    return app
