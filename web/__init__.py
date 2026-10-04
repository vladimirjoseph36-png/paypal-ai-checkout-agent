"""
Web package for the PayPal AI Checkout Agent.

This package contains the Flask application factory and all HTTP
routes. It is intentionally thin: all business logic lives in the
:mod:`agent` package.

Exports:
    :func:`web.app.create_app` — the Flask application factory.

Author:
    Anio Joseph

Project:
    PayPal AI Hackathon 2026
"""

from web.app import create_app

__all__ = ["create_app"]