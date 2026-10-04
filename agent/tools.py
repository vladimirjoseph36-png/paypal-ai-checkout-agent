"""
Tools exposed to the LLM (Gemini function calling).

This module defines the functions that the language model is allowed
to call during a conversation. Each function must have:

* A clear docstring (used by Gemini to understand the tool).
* Typed arguments.
* A JSON-serialisable return value.

Currently, only one tool is exposed:

* :func:`create_order_tool` — creates a PayPal order via
  :class:`agent.paypal_client.PayPalClient`.

Author:
    Anio Joseph

Project:
    PayPal AI Hackathon 2026
"""

from __future__ import annotations

from typing import Any, Dict

from agent.paypal_client import PayPalClient

# ----------------------------------------------------------------------
# Shared PayPal client
# ----------------------------------------------------------------------
# A single PayPalClient instance is reused across the whole process so
# the OAuth2 token can be cached between calls.

_paypal_client = PayPalClient()


def create_order_tool(
    amount_usd: float,
    description: str,
) -> Dict[str, Any]:
    """
    Create a PayPal order for a given amount and product.

    This function is called **automatically by Gemini** whenever the
    user expresses a purchase intent (e.g. *"I want to buy a bluetooth
    headset for $49.99"*). It should never be called directly by the
    user interface — the LLM decides when to invoke it.

    Args:
        amount_usd: The amount in US dollars (e.g. ``49.99``).
        description: A short description of the product being purchased.

    Returns:
        A dictionary with the following keys:

        * ``order_id`` — the PayPal order identifier.
        * ``approve_url`` — the URL the user must open to approve the
          payment.
        * ``amount`` — the amount in USD (echoed back).
        * ``description`` — the product description (echoed back).
        * ``status`` — the PayPal order status (e.g. ``CREATED``).
        * ``mock`` — ``True`` if the response was simulated (mock mode).

    Raises:
        requests.HTTPError: If the PayPal API rejects the request
            (only in real mode).

    Example:
        >>> from agent.tools import create_order_tool
        >>> order = create_order_tool(49.99, "Bluetooth headset")
        >>> order["approve_url"]
        'https://www.sandbox.paypal.com/checkoutnow?token=...'
    """
    return _paypal_client.create_order(amount_usd, description)


__all__ = ["create_order_tool"]