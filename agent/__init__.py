"""
Agent package for the PayPal AI Checkout Agent.

This package contains the AI + payment core of the application:

* :class:`agent.paypal_client.PayPalClient` — PayPal Orders v2 REST wrapper.
* :func:`agent.tools.create_order_tool` — function exposed to the LLM.
* :class:`agent.gemini_agent.CheckoutAgent` — conversational AI agent
  that understands natural language and creates PayPal orders.

The package is intentionally decoupled from the web layer, so the
agent logic can be tested in isolation.

Author:
    Anio Joseph

Project:
    PayPal AI Hackathon 2026
"""

from agent.gemini_agent import CheckoutAgent
from agent.paypal_client import PayPalClient
from agent.tools import create_order_tool

__all__ = ["CheckoutAgent", "PayPalClient", "create_order_tool"]