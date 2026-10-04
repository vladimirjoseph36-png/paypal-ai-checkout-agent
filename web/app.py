"""
Flask application factory.

This module creates and configures the Flask application instance
used by the web layer. It wires together:

* The shared :mod:`config` settings.
* The main blueprint defined in :mod:`web.routes`.
* The Jinja templates (``templates/``) and static assets (``static/``).

Using a factory (instead of a module-level ``app`` object) keeps the
application testable and avoids import side effects.

Author:
    Anio Joseph

Project:
    PayPal AI Hackathon 2026
"""

from __future__ import annotations

from flask import Flask

from config import settings


def create_app() -> Flask:
    """
    Create and configure the Flask application.

    Returns:
        A fully configured :class:`flask.Flask` instance with the
        ``main`` blueprint registered.

    Example:
        >>> from web.app import create_app
        >>> app = create_app()
        >>> app.run()
    """
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.secret_key = settings.FLASK_SECRET_KEY

    # Register HTTP routes
    from web.routes import main_bp
    app.register_blueprint(main_bp)

    return app


__all__ = ["create_app"]