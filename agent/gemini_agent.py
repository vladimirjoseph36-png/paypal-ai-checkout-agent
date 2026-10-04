"""
Conversational AI agent powered by Google Gemini.

This module defines :class:`CheckoutAgent`, the component responsible
for understanding natural-language purchase intents and calling the
appropriate PayPal tools via **Gemini function calling**.

Key responsibilities:

* Configure the Gemini model with a multilingual system prompt.
* Maintain one chat session per user and per language.
* Automatically invoke :func:`agent.tools.create_order_tool` when a
  purchase intent is detected.
* Provide a **mock mode** that simulates the AI's behaviour without
  calling Gemini or PayPal (useful for judges / offline demos).

Supported languages:
    * ``en`` — English (default)
    * ``fr`` — French
    * ``es`` — Spanish

Author:
    Anio Joseph

Project:
    PayPal AI Hackathon 2026
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

import google.generativeai as genai

from agent.tools import create_order_tool
from config import settings


# ======================================================================
# System prompts (real mode)
# ======================================================================
# Each prompt instructs the model to:
#   1. Detect a purchase intent with an amount.
#   2. Call `create_order_tool` immediately.
#   3. Reply in the user's language with a Markdown payment link.

SYSTEM_PROMPTS: Dict[str, str] = {
    "en": """You are a professional, warm and concise shopping assistant.

When the user expresses a purchase intent with an amount
(e.g. "I want to buy a bluetooth headset for $50"), you IMMEDIATELY call
the create_order_tool function with:
    - amount_usd: the amount in US dollars
    - description: a short description of the product

NEVER ask for confirmation: create the order directly.
Then reply in ENGLISH, in 2-3 sentences max, and end with a clickable
PayPal link in Markdown format:
    [Pay now](URL)

Be professional and reassuring.""",

    "fr": """Tu es un assistant d'achat professionnel, concis et chaleureux.

Quand l'utilisateur exprime une intention d'achat avec un montant
(ex: "je veux acheter un casque a 50$"), tu appelles IMMEDIATEMENT
la fonction create_order_tool avec :
    - amount_usd : le montant en dollars US
    - description : une description courte du produit

Ne demande JAMAIS de confirmation : cree la commande directement.
Reponds ensuite en FRANCAIS, en 2 a 3 phrases maximum, et termine
par un lien PayPal cliquable au format Markdown :
    [Payer maintenant](URL)

Sois professionnel et rassurant.""",

    "es": """Eres un asistente de compras profesional, cercano y conciso.

Cuando el usuario exprese una intencion de compra con un monto
(ej: "quiero comprar unos auriculares por $50"), llamas INMEDIATAMENTE
a la funcion create_order_tool con:
    - amount_usd: el monto en dolares US
    - description: una descripcion corta del producto

NUNCA pidas confirmacion: crea la orden directamente.
Luego responde en ESPANOL, en 2-3 frases maximo, y termina con un
enlace PayPal clicable en formato Markdown:
    [Pagar ahora](URL)

Se profesional y tranquilizador.""",
}


# ======================================================================
# Mock mode responses
# ======================================================================
# Used when `settings.is_mock_mode` is True. The text is templated with
# {description}, {amount}, and {url}.

MOCK_REPLIES: Dict[str, str] = {
    "en": (
        "✅ I've created your order for **{description}** "
        "for **${amount:.2f}**.\n\n"
        "👉 [Pay now]({url})\n\n"
        "_(Mock mode: no real PayPal call was made.)_"
    ),
    "fr": (
        "✅ J'ai créé votre commande pour **{description}** "
        "d'un montant de **{amount:.2f} $**.\n\n"
        "👉 [Payer maintenant]({url})\n\n"
        "_(Mode démo : aucun appel PayPal réel n'a été effectué.)_"
    ),
    "es": (
        "✅ He creado tu pedido para **{description}** "
        "por **${amount:.2f}**.\n\n"
        "👉 [Pagar ahora]({url})\n\n"
        "_(Modo demo: no se realizó ninguna llamada real a PayPal.)_"
    ),
}

MOCK_FALLBACK: Dict[str, str] = {
    "en": (
        "Please tell me what you want to buy and at what price "
        '(e.g. "a bluetooth headset for $49.99").'
    ),
    "fr": (
        "Dites-moi ce que vous voulez acheter et à quel prix "
        '(ex : « un casque bluetooth à 49,99 $ »).'
    ),
    "es": (
        "Dime qué quieres comprar y a qué precio "
        '(ej: "unos auriculares por $49.99").'
    ),
}

DEFAULT_LANG: str = "en"
SUPPORTED_LANGS: tuple[str, ...] = ("en", "fr", "es")


# ======================================================================
# Helpers (mock mode only)
# ======================================================================

def _normalise_lang(lang: Optional[str]) -> str:
    """
    Return a supported language code, defaulting to English.

    Args:
        lang: The language code to normalise.

    Returns:
        A code present in :data:`SUPPORTED_LANGS`.
    """
    if lang in SUPPORTED_LANGS:
        return lang
    return DEFAULT_LANG


def _parse_amount(message: str) -> Optional[float]:
    """
    Extract the first monetary amount found in a message.

    Supports: ``49.99``, ``49,99``, ``$49.99``, ``49.99$``, ``50 USD``, etc.

    Args:
        message: The raw user message.

    Returns:
        The amount as a float, or ``None`` if no amount was found.
    """
    normalized = message.replace(",", ".")
    match = re.search(r"(\d+(?:\.\d{1,2})?)", normalized)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _extract_description(message: str, lang: str) -> str:
    """
    Extract a product description from a user message (mock mode only).

    Removes amounts and common purchase-related keywords, then
    falls back to a generic label if nothing remains.

    Args:
        message: The raw user message.
        lang: The target language code.

    Returns:
        A cleaned-up product description.
    """
    # 1. Remove numeric amounts
    cleaned = re.sub(r"\d+(?:[.,]\d{1,2})?", "", message)

    # 2. Remove common purchase keywords and currency symbols
    keywords_pattern = (
        r"\b("
        r"i want to buy|buy|purchase|"
        r"je veux acheter|acheter|"
        r"quiero comprar|comprar|"
        r"for|pour|por|"
        r"usd"
        r")\b"
    )
    cleaned = re.sub(keywords_pattern, "", cleaned, flags=re.IGNORECASE)

    # 3. Remove currency symbols (not word-bound, so done separately)
    cleaned = re.sub(r"[\$€]", "", cleaned)

    # 4. Clean up whitespace and punctuation
    cleaned = " ".join(cleaned.split()).strip(" .,!?-")

    if cleaned:
        return cleaned

    return {
        "en": "your item",
        "fr": "votre article",
        "es": "tu artículo",
    }.get(lang, "your item")


# ======================================================================
# CheckoutAgent
# ======================================================================

class CheckoutAgent:
    """
    Multilingual conversational agent that creates PayPal orders.

    The agent supports two modes:

    * **Real mode** — uses Google Gemini with function calling.
    * **Mock mode** — uses regex-based intent detection and a fake
      PayPal response, so the app can be demonstrated without
      credentials.

    Attributes:
        is_mock: Whether the agent runs in mock mode.
        model_name: The Gemini model identifier.
    """

    def __init__(self) -> None:
        """Initialise the agent and (in real mode) configure Gemini."""
        self.is_mock: bool = settings.is_mock_mode
        self.model_name: str = settings.GEMINI_MODEL
        self._models: Dict[str, Any] = {}

        if not self.is_mock:
            genai.configure(api_key=settings.GEMINI_API_KEY)

    # ------------------------------------------------------------------
    # Real mode
    # ------------------------------------------------------------------

    def _get_model(self, lang: str) -> Any:
        """
        Return (and cache) the Gemini model for the given language.

        Creating a new model is expensive, so we cache one instance
        per supported language.

        Args:
            lang: A language code from :data:`SUPPORTED_LANGS`.

        Returns:
            A configured :class:`google.generativeai.GenerativeModel`.
        """
        lang = _normalise_lang(lang)

        if lang not in self._models:
            self._models[lang] = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=SYSTEM_PROMPTS[lang],
                tools=[create_order_tool],
            )
        return self._models[lang]

    def new_session(self, lang: str = DEFAULT_LANG) -> Any:
        """
        Start a new chat session in the given language.

        Args:
            lang: A language code from :data:`SUPPORTED_LANGS`.

        Returns:
            A new ``ChatSession`` (real mode) or a lightweight dict
            (mock mode).
        """
        if self.is_mock:
            return {"lang": _normalise_lang(lang)}

        model = self._get_model(lang)
        return model.start_chat(enable_automatic_function_calling=True)

    def ask(
        self,
        message: str,
        chat_session: Optional[Any] = None,
        lang: str = DEFAULT_LANG,
    ) -> Tuple[str, Any]:
        """
        Send a message to the agent and return its response.

        Args:
            message: The user's message.
            chat_session: An existing session, or ``None`` to create one.
            lang: The language code for the reply.

        Returns:
            A tuple ``(reply_text, updated_session)``.
        """
        if self.is_mock:
            reply = self._ask_mock(message, lang)
            return reply, {"lang": _normalise_lang(lang)}

        if chat_session is None:
            chat_session = self.new_session(lang)

        response = chat_session.send_message(message)
        return response.text, chat_session

    # ------------------------------------------------------------------
    # Mock mode
    # ------------------------------------------------------------------

    def _ask_mock(self, message: str, lang: str) -> str:
        """
        Simulate an agent response without calling Gemini or PayPal.

        Args:
            message: The user's message.
            lang: The target language code.

        Returns:
            A templated reply string.
        """
        lang = _normalise_lang(lang)

        amount = _parse_amount(message)
        if amount is None or amount <= 0:
            return MOCK_FALLBACK[lang]

        description = _extract_description(message, lang)

        # `create_order_tool` automatically returns a mock order
        # because the PayPalClient checks `settings.is_mock_mode`.
        result = create_order_tool(amount, description)

        return MOCK_REPLIES[lang].format(
            description=description.capitalize(),
            amount=amount,
            url=result["approve_url"],
        )


__all__ = ["CheckoutAgent", "SYSTEM_PROMPTS", "MOCK_REPLIES"]