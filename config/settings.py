"""
Centralised configuration for the PayPal AI Checkout Agent.

This module loads environment variables from the ``.env`` file located
at the project root and exposes a single shared ``settings`` instance
that the rest of the application imports.

It also detects whether the application should run in **mock mode**,
which allows the app to be tested without PayPal or Gemini credentials
(e.g. by hackathon judges).

Environment variables used:

    - ``PAYPAL_CLIENT_ID``  : PayPal Sandbox client ID
    - ``PAYPAL_SECRET``     : PayPal Sandbox secret
    - ``PAYPAL_ENV``        : ``sandbox`` (default) or ``live``
    - ``GEMINI_API_KEY``    : Google Gemini API key
    - ``FLASK_SECRET_KEY``  : Flask session secret
    - ``FLASK_PORT``        : HTTP port (default: 5000)
    - ``MOCK_MODE``         : force mock mode (``true`` / ``false``)

Author:
    Anio Joseph

Project:
    PayPal AI Hackathon 2026
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ----------------------------------------------------------------------
# Environment loading
# ----------------------------------------------------------------------

BASE_DIR: Path = Path(__file__).resolve().parent.parent
"""Absolute path to the project root directory."""

load_dotenv(BASE_DIR / ".env")
"""Load variables from the ``.env`` file at the project root."""


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _str_to_bool(value: str | None) -> bool:
    """
    Convert a string to a boolean.

    Accepts ``true``, ``1``, ``yes``, and ``on`` (case-insensitive)
    as truthy values. Everything else is considered falsy.

    Args:
        value: The string to convert.

    Returns:
        ``True`` if the value is truthy, ``False`` otherwise.
    """
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "on"}


# ----------------------------------------------------------------------
# Settings container
# ----------------------------------------------------------------------

class Settings:
    """
    Container for all application settings.

    This class reads environment variables once at import time and
    exposes them as class attributes. A single instance is created
    at the bottom of this module and shared across the whole app.

    Attributes:
        PAYPAL_CLIENT_ID: PayPal Sandbox client ID.
        PAYPAL_SECRET: PayPal Sandbox secret.
        PAYPAL_ENV: PayPal environment (``sandbox`` or ``live``).
        GEMINI_API_KEY: Google Gemini API key.
        GEMINI_MODEL: Gemini model name to use.
        FLASK_SECRET_KEY: Secret key for Flask sessions.
        FLASK_PORT: HTTP port for the Flask server.
        FLASK_HOST: Host interface for the Flask server.
        MOCK_MODE_FORCED: Whether mock mode is forced via ``.env``.
    """

    # --- PayPal ---
    PAYPAL_CLIENT_ID: str = os.getenv("PAYPAL_CLIENT_ID", "")
    PAYPAL_SECRET: str = os.getenv("PAYPAL_SECRET", "")
    PAYPAL_ENV: str = os.getenv("PAYPAL_ENV", "sandbox")

    # --- Google Gemini ---
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = gemini-flash-lite-latest"

    # --- Flask ---
    FLASK_SECRET_KEY: str = os.getenv("FLASK_SECRET_KEY", "dev-secret")
    FLASK_PORT: int = int(os.getenv("FLASK_PORT", "5000"))
    FLASK_HOST: str = "0.0.0.0"

    # --- Mock mode ---
    MOCK_MODE_FORCED: bool = _str_to_bool(os.getenv("MOCK_MODE", "false"))

    # ------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------

    @property
    def paypal_base_url(self) -> str:
        """
        Return the base URL of the PayPal REST API.

        Returns:
            The production URL when ``PAYPAL_ENV`` is ``live``,
            otherwise the Sandbox URL.
        """
        if self.PAYPAL_ENV == "live":
            return "https://api-m.paypal.com"
        return "https://api-m.sandbox.paypal.com"

    @property
    def is_mock_mode(self) -> bool:
        """
        Determine whether the application must run in mock mode.

        Mock mode is enabled when:

        * ``MOCK_MODE=true`` is set in the ``.env`` file, **or**
        * Any of the critical credentials is missing
          (``PAYPAL_CLIENT_ID``, ``PAYPAL_SECRET``, ``GEMINI_API_KEY``).

        This allows judges and reviewers to launch the app without
        configuring any credentials.

        Returns:
            ``True`` if mock mode should be used, ``False`` otherwise.
        """
        if self.MOCK_MODE_FORCED:
            return True

        return not (
            self.PAYPAL_CLIENT_ID
            and self.PAYPAL_SECRET
            and self.GEMINI_API_KEY
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> None:
        """
        Validate that required credentials are present.

        In mock mode, this method does nothing (no credentials required).
        Otherwise, it raises an ``EnvironmentError`` listing every
        missing variable.

        Raises:
            EnvironmentError: If one or more required credentials are missing.
        """
        if self.is_mock_mode:
            return

        missing: list[str] = []

        if not self.PAYPAL_CLIENT_ID:
            missing.append("PAYPAL_CLIENT_ID")
        if not self.PAYPAL_SECRET:
            missing.append("PAYPAL_SECRET")
        if not self.GEMINI_API_KEY:
            missing.append("GEMINI_API_KEY")

        if missing:
            raise EnvironmentError(
                "Missing environment variables: " + ", ".join(missing)
            )


# ----------------------------------------------------------------------
# Shared singleton
# ----------------------------------------------------------------------

settings = Settings()
"""Single shared instance of :class:`Settings` used across the app."""