"""
PayPal Orders v2 REST client.

This module wraps the PayPal Orders v2 REST API and exposes a small,
reusable :class:`PayPalClient` class. It handles:

* OAuth2 authentication (with token caching).
* Creating orders with ``intent=CAPTURE``.
* Capturing approved orders.

When the application runs in **mock mode** (see
:attr:`config.settings.Settings.is_mock_mode`), the client does not
make any network call: it returns a realistic fake order instead.
This allows the app to be tested without PayPal credentials.

Example:
    Basic usage::

        from agent.paypal_client import PayPalClient

        client = PayPalClient()
        order = client.create_order(49.99, "Bluetooth headset")
        print(order["approve_url"])

Author:
    Anio Joseph

Project:
    PayPal AI Hackathon 2026
"""

from __future__ import annotations

import uuid
from typing import Any, Dict

import requests

from config import settings


class PayPalClient:
    """
    Minimal client for the PayPal Orders v2 REST API.

    Attributes:
        base_url: PayPal REST API base URL (sandbox or live).
        client_id: PayPal OAuth2 client ID.
        secret: PayPal OAuth2 secret.
        is_mock: Whether the client runs in mock mode.
    """

    # Timeout (in seconds) applied to every HTTP request.
    HTTP_TIMEOUT: int = 15

    def __init__(self) -> None:
        """
        Initialise the client from the shared :mod:`config` settings.

        No network call is performed here; the OAuth2 token is fetched
        lazily on the first real request.
        """
        self.base_url: str = settings.paypal_base_url
        self.client_id: str = settings.PAYPAL_CLIENT_ID
        self.secret: str = settings.PAYPAL_SECRET
        self.is_mock: bool = settings.is_mock_mode
        self._access_token: str | None = None

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def get_access_token(self, force_refresh: bool = False) -> str:
        """
        Retrieve (and cache) a PayPal OAuth2 access token.

        Args:
            force_refresh: If ``True``, ignore the cached token and
                request a new one from PayPal.

        Returns:
            A valid OAuth2 access token (or ``"MOCK_TOKEN"`` in mock mode).

        Raises:
            requests.HTTPError: If PayPal rejects the credentials.
        """
        if self.is_mock:
            return "MOCK_TOKEN"

        if self._access_token and not force_refresh:
            return self._access_token

        response = requests.post(
            f"{self.base_url}/v1/oauth2/token",
            auth=(self.client_id, self.secret),
            data={"grant_type": "client_credentials"},
            timeout=self.HTTP_TIMEOUT,
        )
        response.raise_for_status()
        self._access_token = response.json()["access_token"]
        return self._access_token

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def create_order(
        self,
        amount_usd: float,
        description: str = "Purchase",
    ) -> Dict[str, Any]:
        """
        Create a PayPal order with ``intent=CAPTURE``.

        Args:
            amount_usd: Amount in US dollars (e.g. ``49.99``).
            description: Short description shown to the customer.

        Returns:
            A dictionary with the following keys:

            * ``order_id`` — PayPal order identifier.
            * ``approve_url`` — URL the user must open to approve payment.
            * ``amount`` — Amount in USD (echoed back).
            * ``description`` — Product description (echoed back).
            * ``status`` — PayPal order status (e.g. ``CREATED``).
            * ``mock`` — ``True`` if the response is simulated.

        Raises:
            requests.HTTPError: If PayPal rejects the request.
        """
        # --- Mock mode: return a realistic fake order ---
        if self.is_mock:
            fake_id = "MOCK-" + uuid.uuid4().hex[:12].upper()
            return {
                "order_id": fake_id,
                "approve_url": (
                    "https://www.sandbox.paypal.com/checkoutnow"
                    f"?token={fake_id}"
                ),
                "amount": amount_usd,
                "description": description,
                "status": "CREATED",
                "mock": True,
            }

        # --- Real mode: call the PayPal API ---
        token = self.get_access_token()
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "description": description,
                    "amount": {
                        "currency_code": "USD",
                        "value": f"{amount_usd:.2f}",
                    },
                }
            ],
        }
        response = requests.post(
            f"{self.base_url}/v2/checkout/orders",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            json=payload,
            timeout=self.HTTP_TIMEOUT,
        )
        response.raise_for_status()
        order = response.json()

        approve_url = next(
            link["href"] for link in order["links"] if link["rel"] == "approve"
        )

        return {
            "order_id": order["id"],
            "approve_url": approve_url,
            "amount": amount_usd,
            "description": description,
            "status": order.get("status", "CREATED"),
            "mock": False,
        }

    def capture_order(self, order_id: str) -> Dict[str, Any]:
        """
        Capture an order previously approved by the user.

        Args:
            order_id: PayPal order identifier.

        Returns:
            The raw PayPal capture response, or a mock completion
            dictionary in mock mode.

        Raises:
            requests.HTTPError: If PayPal rejects the request.
        """
        if self.is_mock:
            return {
                "id": order_id,
                "status": "COMPLETED",
                "mock": True,
            }

        token = self.get_access_token()
        response = requests.post(
            f"{self.base_url}/v2/checkout/orders/{order_id}/capture",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            timeout=self.HTTP_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()