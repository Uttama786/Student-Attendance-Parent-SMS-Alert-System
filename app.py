"""
app.py — Flask application factory and entry point.

Usage:
  python app.py               (development server)
  flask run                   (via flask CLI)
"""
import os
import logging
from flask import Flask

from config import config_map
from extensions import db, login_manager, csrf


def create_app(config_name: str = "default") -> Flask:
    """
    Application factory.
    Creates and configures the Flask application, registers all blueprints,
    initialises extensions, creates database tables and seeds the admin user.
    """
    app = Flask(__name__)
    app.config.from_object(config_map[config_name])

    # ── Initialise extensions ─────────────────────────────────────────────────
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # ── Register blueprints ───────────────────────────────────────────────────
    from blueprints.auth.routes import auth_bp
    from blueprints.dashboard.routes import dashboard_bp
    from blueprints.students.routes import students_bp
    from blueprints.attendance.routes import attendance_bp
    from blueprints.reports.routes import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(students_bp, url_prefix="/students")
    app.register_blueprint(attendance_bp, url_prefix="/attendance")
    app.register_blueprint(reports_bp, url_prefix="/reports")

    # ── Create tables & seed ──────────────────────────────────────────────────
    with app.app_context():
        db.create_all()
        _seed_admin(app)
        _seed_subjects(app)

    # ── Logging ───────────────────────────────────────────────────────────────
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )

    return app


def _seed_admin(app: Flask) -> None:
    """
    Creates a default admin account on first run if no faculty records exist.
    Credentials are taken from environment variables / .env file.
    """
    from models import Faculty

    if Faculty.query.count() == 0:
        admin = Faculty(
            name="System Administrator",
            username=app.config["ADMIN_USERNAME"],
            role="admin",
        )
        admin.set_password(app.config["ADMIN_PASSWORD"])
        db.session.add(admin)
        db.session.commit()
        app.logger.info(
            "Default admin created → username: %s", app.config["ADMIN_USERNAME"]
        )


def _seed_subjects(app: Flask) -> None:
    """
    Creates default subjects (PYTHON for Sem 1, TOC for Sem 5)
    on first run if no subject records exist.
    """
    from models import Subject

    if Subject.query.count() == 0:
        db.session.add(Subject(name="PYTHON", semester=1))
        db.session.add(Subject(name="TOC", semester=5))
        db.session.commit()
        app.logger.info("Default subjects seeded (PYTHON -> Sem 1, TOC -> Sem 5)")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    env = os.environ.get("FLASK_ENV", "development")
    application = create_app(env)
    application.run(host="0.0.0.0", port=5000, debug=(env == "development"))
