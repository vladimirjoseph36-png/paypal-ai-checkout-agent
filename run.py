"""
Application entry point.

This module starts the Flask development server that exposes the
chat interface. It also prints a short banner summarising the
current mode (real or mock) so the user immediately knows whether
PayPal and Gemini will actually be contacted.

Usage:
    ::

        python run.py

Author:
    Anio Joseph

Project:
    PayPal AI Hackathon 2026
"""

from __future__ import annotations

from config import settings
from web import create_app

# ----------------------------------------------------------------------
# Application instance
# ----------------------------------------------------------------------

app = create_app()
"""The Flask application, created via the factory in :mod:`web.app`."""


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _print_banner() -> None:
    """
    Print a startup banner describing the current configuration.

    The banner includes:

    * The author and project name.
    * The current mode (``LIVE`` or ``MOCK``).
    * The local URL where the app is served.
    * A short notice when mock mode is active.
    """
    mode = "MOCK (no credentials required)" if settings.is_mock_mode else "LIVE (PayPal Sandbox)"

    print("=" * 62)
    print("  PayPal AI Checkout Agent")
    print("  Author  : Anio Joseph")
    print("  Project : PayPal AI Hackathon 2026")
    print("-" * 62)
    print(f"  Mode    : {mode}")
    print(f"  URL     : http://localhost:{settings.FLASK_PORT}")
    print("=" * 62)

    if settings.is_mock_mode:
        print("  >> Mock mode is ON:")
        print("     no real PayPal or Gemini calls will be made.")
        print("=" * 62)


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

if __name__ == "__main__":
    settings.validate()
    _print_banner()

    app.run(
        host=settings.FLASK_HOST,
        port=settings.FLASK_PORT,
        debug=True,
    )