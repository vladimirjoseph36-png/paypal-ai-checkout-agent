"""
Conversational AI agent with multi-provider LLM support.

This module defines :class:`CheckoutAgent`, the component responsible
for understanding natural-language purchase intents and calling the
appropriate PayPal tools.

The agent supports **two LLM providers**:

* **Groq** (default) — free, no credit card required, 30 req/min.
* **Google Gemini** — used as a fallback.

For the Groq provider, the purchase intent is detected
**deterministically** (regex on the amount). This guarantees that a
PayPal order is created whenever the user message contains a price,
regardless of the LLM's tool-calling behaviour.

A third **mock mode** is available for judges / offline demos: it
uses simple regex rules and never calls any external API.

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
from groq import Groq

from agent.tools import create_order_tool
from config import settings


# ======================================================================
# System prompts (real mode)
# ======================================================================

SYSTEM_PROMPTS: Dict[str, str] = {
    "en": """You are a professional, warm and concise shopping assistant.

If the user message does NOT contain an amount or a purchase intent,
reply politely in ENGLISH (1-2 sentences) and ask them what they
would like to buy and for how much.

Keep it short. Do NOT invent prices. Do NOT confirm any order.""",

    "fr": """Tu es un assistant d'achat professionnel, concis et chaleureux.

Si le message de l'utilisateur ne contient PAS de montant ni
d'intention d'achat, réponds poliment en FRANÇAIS (1 à 2 phrases) et
demande-lui ce qu'il souhaite acheter et à quel prix.

Reste bref. N'invente PAS de prix. Ne confirme AUCUNE commande.""",

    "es": """Eres un asistente de compras profesional, cercano y conciso.

Si el mensaje del usuario NO contiene un monto ni una intención de
compra, responde con educación en ESPAÑOL (1-2 frases) y pregúntale
qué quiere comprar y a qué precio.

Sé breve. NO inventes precios. NO confirmes ningún pedido.""",
}


# ======================================================================
# Template replies (used when an amount is detected)
# ======================================================================

ORDER_CONFIRMATION_TEMPLATES: Dict[str, str] = {
    "en": (
        "✅ I've created your order for **{description}** "
        "for **${amount:.2f}**.\n\n"
        "👉 [Pay now]({url})"
    ),
    "fr": (
        "✅ J'ai créé votre commande pour **{description}** "
        "d'un montant de **{amount:.2f} $**.\n\n"
        "👉 [Payer maintenant]({url})"
    ),
    "es": (
        "✅ He creado tu pedido para **{description}** "
        "por **${amount:.2f}**.\n\n"
        "👉 [Pagar ahora]({url})"
    ),
}

MOCK_DISCLAIMERS: Dict[str, str] = {
    "en": "\n\n_(Mock mode: no real PayPal call was made.)_",
    "fr": "\n\n_(Mode démo : aucun appel PayPal réel n'a été effectué.)_",
    "es": "\n\n_(Modo demo: no se realizó ninguna llamada real a PayPal.)_",
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
# Helpers
# ======================================================================

def _normalise_lang(lang: Optional[str]) -> str:
    """Return a supported language code, defaulting to English."""
    if lang in SUPPORTED_LANGS:
        return lang
    return DEFAULT_LANG


def _parse_amount(message: str) -> Optional[float]:
    """
    Extract the first monetary amount found in a message.

    Supports: ``49.99``, ``49,99``, ``$49.99``, ``49.99$``, ``50 USD``, etc.
    """
    normalized = message.replace(",", ".")
    match = re.search(r"(\d+(?:\.\d{1,2})?)", normalized)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


# List of keywords to strip from the message when extracting a
# product description. Kept as a plain Python list for clarity and
# easy maintenance.
_DESCRIPTION_STOPWORDS = [
    "i want to buy",
    "i would like to buy",
    "i want",
    "i would like",
    "please",
    "buy",
    "purchase",
    "je veux acheter",
    "je voudrais acheter",
    "je veux",
    "je voudrais",
    "svp",
    "acheter",
    "quiero comprar",
    "quisiera comprar",
    "quiero",
    "comprar",
    "por favor",
    "for",
    "pour",
    "por",
    "usd",
    "dollar",
    "dollars",
    "euro",
    "euros",
    "a",
    "an",
    "the",
    "un",
    "une",
    "le",
    "la",
    "les",
    "my",
    "mon",
    "ma",
    "mes",
    "me",
    "moi",
]


def _extract_description(message: str, lang: str) -> str:
    """
    Extract a product description from a user message.

    Removes amounts, currency symbols and common purchase-related
    keywords. Falls back to a generic label if nothing remains.
    """
    # 1. Remove numbers
    cleaned = re.sub(r"\d+(?:[.,]\d{1,2})?", "", message)

    # 2. Remove currency symbols
    cleaned = re.sub(r"[\$€£]", "", cleaned)

    # 3. Remove stopwords (case-insensitive, whole word)
    for word in _DESCRIPTION_STOPWORDS:
        cleaned = re.sub(
            r"\b" + re.escape(word) + r"\b",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

    # 4. Collapse whitespace and strip punctuation
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

    Attributes:
        is_mock: Whether the agent runs in mock mode.
        provider: The selected LLM provider ("groq" or "gemini").
    """

    def __init__(self) -> None:
        self.is_mock: bool = settings.is_mock_mode
        self.provider: str = getattr(settings, "LLM_PROVIDER", "groq").lower()
        self._models: Dict[str, Any] = {}

        # Initialise Groq client (only if not in mock mode)
        self._groq_client: Optional[Groq] = None
        if not self.is_mock and self.provider == "groq":
            self._groq_client = Groq(api_key=settings.GROQ_API_KEY)

        # Initialise Gemini (fallback) if needed
        if not self.is_mock and self.provider == "gemini":
            genai.configure(api_key=settings.GEMINI_API_KEY)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def new_session(self, lang: str = DEFAULT_LANG) -> Any:
        """Start a new chat session in the given language."""
        if self.is_mock:
            return {"lang": _normalise_lang(lang), "messages": []}

        if self.provider == "groq":
            return {
                "lang": _normalise_lang(lang),
                "messages": [
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPTS[_normalise_lang(lang)],
                    },
                ],
            }

        model = self._get_gemini_model(lang)
        return model.start_chat(enable_automatic_function_calling=True)

    def ask(
        self,
        message: str,
        chat_session: Optional[Any] = None,
        lang: str = DEFAULT_LANG,
    ) -> Tuple[str, Any]:
        """Send a message to the agent and return its response."""
        if self.is_mock:
            reply = self._ask_mock(message, lang)
            return reply, {"lang": _normalise_lang(lang), "messages": []}

        if self.provider == "groq":
            return self._ask_groq(message, chat_session, lang)

        return self._ask_gemini(message, chat_session, lang)

    # ------------------------------------------------------------------
    # Groq (primary)
    # ------------------------------------------------------------------

    def _ask_groq(
        self,
        message: str,
        session: Optional[Dict[str, Any]],
        lang: str,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Send a message to Groq.

        If a price is detected, the PayPal order is created directly
        and the reply is templated (deterministic).
        Otherwise, Groq is asked to reply naturally.
        """
        lang = _normalise_lang(lang)

        if session is None:
            session = self.new_session(lang)

        session["messages"].append({"role": "user", "content": message})

        # --- 1. Detect a purchase intent ---
        amount = _parse_amount(message)
        if amount is not None and amount > 0:
            description = _extract_description(message, lang) or "item"
            result = create_order_tool(
                amount_usd=amount,
                description=description,
            )

            reply = ORDER_CONFIRMATION_TEMPLATES[lang].format(
                description=description.capitalize(),
                amount=amount,
                url=result["approve_url"],
            )
            session["messages"].append({"role": "assistant", "content": reply})
            return reply, session

        # --- 2. No amount: let Groq reply naturally ---
        try:
            response = self._groq_client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=session["messages"],
                temperature=0.4,
                max_tokens=200,
            )
            reply = response.choices[0].message.content or MOCK_FALLBACK[lang]
        except Exception:
            reply = MOCK_FALLBACK[lang]

        session["messages"].append({"role": "assistant", "content": reply})
        return reply, session

    # ------------------------------------------------------------------
    # Gemini (fallback)
    # ------------------------------------------------------------------

    def _get_gemini_model(self, lang: str) -> Any:
        """Return (and cache) the Gemini model for the given language."""
        lang = _normalise_lang(lang)
        if lang not in self._models:
            self._models[lang] = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                system_instruction=SYSTEM_PROMPTS[lang],
                tools=[create_order_tool],
            )
        return self._models[lang]

    def _ask_gemini(
        self,
        message: str,
        session: Optional[Any],
        lang: str,
    ) -> Tuple[str, Any]:
        """Send a message to Gemini (fallback, keeps function calling)."""
        if session is None:
            session = self._get_gemini_model(lang).start_chat(
                enable_automatic_function_calling=True
            )
        response = session.send_message(message)
        return response.text, session

    # ------------------------------------------------------------------
    # Mock mode
    # ------------------------------------------------------------------

    def _ask_mock(self, message: str, lang: str) -> str:
        """Simulate an agent response without calling any external API."""
        lang = _normalise_lang(lang)

        amount = _parse_amount(message)
        if amount is None or amount <= 0:
            return MOCK_FALLBACK[lang]

        description = _extract_description(message, lang)
        result = create_order_tool(amount, description)

        reply = ORDER_CONFIRMATION_TEMPLATES[lang].format(
            description=description.capitalize(),
            amount=amount,
            url=result["approve_url"],
        )
        return reply + MOCK_DISCLAIMERS[lang]


__all__ = ["CheckoutAgent", "SYSTEM_PROMPTS", "ORDER_CONFIRMATION_TEMPLATES"]