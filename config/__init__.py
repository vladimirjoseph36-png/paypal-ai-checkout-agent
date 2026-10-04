"""
Configuration package for the PayPal AI Checkout Agent.

This package centralises all environment-based configuration
(PayPal credentials, Gemini API key, Flask settings, mock mode)
and exposes a single shared ``settings`` instance to the rest
of the application.

Typical usage::

    from config import settings

    if settings.is_mock_mode:
        ...

Author:
    Anio Joseph

Project:
    PayPal AI Hackathon 2026
"""

from config.settings import Settings, settings

__all__ = ["Settings", "settings"]