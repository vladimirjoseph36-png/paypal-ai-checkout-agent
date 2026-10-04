"""
HTTP routes for the PayPal AI Checkout Agent.

This module defines the two endpoints served by the application:

* ``GET /`` — renders the chat UI.
* ``POST /api/chat`` — receives a user message and returns the
  agent's reply as JSON.

Each browser session is assigned a unique ``user_id`` and its own
Gemini chat session, so multiple users can interact simultaneously
without interfering with each other. When the user switches language,
the Gemini session is restarted with the corresponding system prompt.

Author:
    Anio Joseph

Project:
    PayPal AI Hackathon 2026
"""

from __future__ import annotations

import uuid
from typing import Any, Dict

from flask import Blueprint, jsonify, render_template, request, session

from agent import CheckoutAgent

# ----------------------------------------------------------------------
# Blueprint
# ----------------------------------------------------------------------

main_bp = Blueprint("main", __name__)


# ----------------------------------------------------------------------
# Shared state
# ----------------------------------------------------------------------

_agent = CheckoutAgent()
"""Single shared :class:`CheckoutAgent` used by all requests."""

_chat_sessions: Dict[str, Dict[str, Any]] = {}
"""Per-user chat state: ``{user_id: {"session": ..., "lang": ...}}``."""

SUPPORTED_LANGS = {"en", "fr", "es"}
DEFAULT_LANG = "en"


# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------

@main_bp.route("/")
def index():
    """
    Render the main chat interface.

    A unique ``user_id`` is created on the first visit and stored in
    the Flask session (an encrypted cookie).

    Returns:
        The rendered ``index.html`` template.
    """
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())
    return render_template("index.html")


@main_bp.route("/api/chat", methods=["POST"])
def chat():
    """
    Process a chat message and return the agent's reply.

    Request body (JSON):
        {
            "message": "I want to buy a bluetooth headset for $49.99",
            "lang": "en"
        }

    Returns (JSON):
        On success: ``{"reply": "..."}``
        On error:   ``{"error": "..."}`` with an HTTP 4xx/5xx status.

    The Gemini chat session is restarted automatically when the
    requested language differs from the current session's language.
    """
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    lang = (data.get("lang") or DEFAULT_LANG).lower()

    if lang not in SUPPORTED_LANGS:
        lang = DEFAULT_LANG

    if not message:
        return jsonify({"error": "Empty message"}), 400

    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Invalid session"}), 400

    entry = _chat_sessions.get(user_id)

    # Restart the Gemini session if the language changed
    if entry is None or entry.get("lang") != lang:
        chat_session = _agent.new_session(lang)
        _chat_sessions[user_id] = {"session": chat_session, "lang": lang}
        entry = _chat_sessions[user_id]

    try:
        reply, updated_session = _agent.ask(
            message, entry["session"], lang
        )
        entry["session"] = updated_session
        return jsonify({"reply": reply})
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": str(exc)}), 500


__all__ = ["main_bp"]