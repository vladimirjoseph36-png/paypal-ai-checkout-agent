# 💳 PayPal AI Checkout Agent

### by **Anio Joseph**

**Conversational AI that creates real PayPal orders from natural language.**

Tell it what you want to buy → it understands → it creates the PayPal order.

![PayPal](https://img.shields.io/badge/PayPal-Sandbox-0070ba?logo=paypal&logoColor=white)
![Gemini](https://img.shields.io/badge/Google-Gemini%203.8%20Flash-4285F4?logo=google&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?logo=flask&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)

*Built for the **PayPal AI Hackathon 2026** by **Anio Joseph***

---

## 📖 Description

**PayPal AI Checkout Agent** is a conversational shopping assistant that turns natural language into real PayPal orders — in seconds.

The user simply types something like:

> *"I want to buy a bluetooth headset for $49.99"*

And the agent:

1. **Understands** the purchase intent using Google Gemini
2. **Calls** the PayPal Orders v2 API via function calling
3. **Creates** a real PayPal Sandbox order
4. **Returns** a clickable approval link to the user

No forms. No checkout page. Just a conversation.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🗣️ Natural language checkout | Users describe what they want, the AI does the rest |
| 🤖 AI function calling | Gemini 3.8 Flash automatically invokes PayPal tools |
| 💳 Real PayPal integration | Creates actual orders in the PayPal Sandbox |
| 🌍 Multi-language | Full UI + AI responses in English / Français / Español |
| 🎨 Premium UI | Glassmorphism, animated PayPal watermark background |
| ⚡ Fast | Single-page chat, no build step, no framework overhead |
| 🔒 Secure | Credentials stored in .env, never committed |

---

## 🏗️ Architecture

### High-level overview

The project follows a **3-layer architecture** that cleanly separates
the presentation (web), the intelligence (agent), and the integration (PayPal).

```
+------------------------------------------------------------------+
|                       BROWSER (Chat UI)                          |
|  templates/index.html + static/css/style.css + static/js/app.js  |
|                                                                  |
|  - Multilingual interface (EN / FR / ES)                         |
|  - Animated background with PayPal watermark mosaic              |
|  - Sends POST /api/chat with { message, lang }                   |
+--------------------------+---------------------------------------+
                           | HTTP
                           v
+------------------------------------------------------------------+
|                    FLASK WEB LAYER (web/)                        |
|                                                                  |
|  web/app.py      -> creates the Flask app                        |
|  web/routes.py   -> handles / and /api/chat                      |
|                                                                  |
|  - Manages per-user chat sessions                                |
|  - Restarts the Gemini session when the language changes         |
+--------------------------+---------------------------------------+
                           | Python calls
                           v
+------------------------------------------------------------------+
|                    AI AGENT LAYER (agent/)                       |
|                                                                  |
|  agent/gemini_agent.py  -> Gemini model + multilingual prompts   |
|  agent/tools.py         -> functions exposed to the LLM          |
|                                                                  |
|  - Understands natural language purchase intent                  |
|  - Uses Gemini Function Calling to invoke PayPal tools           |
|  - Returns a friendly message with a Markdown payment link       |
+--------------------------+---------------------------------------+
                           | Function call
                           v
+------------------------------------------------------------------+
|                   PAYPAL INTEGRATION (agent/)                    |
|                                                                  |
|  agent/paypal_client.py -> PayPal Orders v2 REST wrapper         |
|                                                                  |
|  - OAuth2 token management (cached)                              |
|  - Creates orders with intent=CAPTURE                            |
|  - Returns the approval URL for the user                         |
+--------------------------+---------------------------------------+
                           | HTTPS
                           v
                +----------------------------+
                |    PayPal Sandbox API      |
                |  api-m.sandbox.paypal.com  |
                +----------------------------+
```

### Data flow — end to end

Here's exactly what happens when a user types a message:

| Step | What happens | Where |
|---|---|---|
| **1** | User types "I want to buy a bluetooth headset for $49.99" and hits Enter | Browser |
| **2** | JS sends `POST /api/chat` with `{ message, lang }` | `static/js/app.js` |
| **3** | Flask receives the request, retrieves the user's Gemini session | `web/routes.py` |
| **4** | The message is passed to the `CheckoutAgent` | `web/routes.py` |
| **5** | Gemini detects a purchase intent and requests a function call to `create_order_tool` | `agent/gemini_agent.py` |
| **6** | The tool calls `PayPalClient.create_order(amount_usd, description)` | `agent/tools.py` |
| **7** | PayPalClient gets an OAuth2 token (cached) then POSTs to `/v2/checkout/orders` | `agent/paypal_client.py` |
| **8** | PayPal returns an `order_id` and an `approve_url` | PayPal Sandbox |
| **9** | Gemini composes a natural-language reply with a Markdown payment link | `agent/gemini_agent.py` |
| **10** | Flask returns the reply as JSON | `web/routes.py` |
| **11** | JS renders the message with a clickable **Pay now** link | `static/js/app.js` |
| **12** | User clicks the link -> opens the official PayPal checkout page | PayPal Sandbox |

### Component responsibilities

| File | Role | Key class / function |
|---|---|---|
| `config/settings.py` | Loads `.env`, exposes `settings` object | `Settings` |
| `agent/paypal_client.py` | Encapsulates PayPal Orders v2 | `PayPalClient` |
| `agent/tools.py` | Exposes functions to the LLM | `create_order_tool()` |
| `agent/gemini_agent.py` | Gemini model + multilingual prompts | `CheckoutAgent` |
| `web/app.py` | Flask factory | `create_app()` |
| `web/routes.py` | HTTP endpoints | `index()`, `chat()` |
| `templates/index.html` | Chat UI | - |
| `static/css/style.css` | Premium design + animations | - |
| `static/js/app.js` | Chat logic, i18n, animated background | - |
| `run.py` | Application entry point | - |

### Design decisions

| Decision | Why |
|---|---|
| **Function calling instead of prompt engineering** | More reliable: Gemini returns structured tool calls, not free-form text |
| **Cached OAuth2 token** | Avoids requesting a new PayPal token on every message |
| **Separate `agent/` and `web/` packages** | Clean separation between AI logic and HTTP layer -> testable in isolation |
| **Per-language Gemini model cache** | Avoids recreating the model on every message when the user doesn't change language |
| **Vanilla JS frontend** | No build step, no framework overhead, judges can read the code directly |
| **Session restart on language change** | Guarantees the assistant always replies in the language the user selected |
| **Mock mode** | Lets judges test the full UX without needing PayPal or Gemini credentials |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- A PayPal Developer account -> https://developer.paypal.com/
- A Google Gemini API key -> https://aistudio.google.com/app/apikey

### 1. Clone the repository

```bash
git clone https://github.com/votre-username/paypal-ai-checkout-agent.git
cd paypal-ai-checkout-agent
```

### 2. Create a virtual environment

```bash
python -m venv venv
# Windows
.\venv\Scripts\Activate.ps1
# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Then edit `.env`:

```env
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_SECRET=your_paypal_secret
PAYPAL_ENV=sandbox

GEMINI_API_KEY=your_gemini_api_key

FLASK_SECRET_KEY=change_me_in_production
FLASK_PORT=5000
```

**How to get PayPal credentials:**
1. Go to https://developer.paypal.com/dashboard/applications/sandbox
2. Click "Create App"
3. Choose Merchant type
4. Copy the Client ID and Secret

**How to get a Gemini API key:**
1. Go to https://aistudio.google.com/app/apikey
2. Click "Create API key"
3. Copy the key

### 5. Run the app

```bash
python run.py
```

Open your browser at http://localhost:5000

---

## 🧪 Mock Mode (no credentials required)

For judges who don't have PayPal/Gemini credentials, a mock mode is available.

**Activate mock mode:**

```bash
# Windows
set MOCK_MODE=true && python run.py

# macOS / Linux
MOCK_MODE=true python run.py
```

Or add `MOCK_MODE=true` to your `.env` file.

In mock mode, the app returns a fake but realistic PayPal approval URL so you can see the full UX end-to-end.

---

## 📁 Project Structure

```
paypal-ai-checkout-agent/
|
|-- .env.example
|-- .gitignore
|-- LICENSE
|-- README.md
|-- requirements.txt
|-- run.py
|
|-- config/
|   |-- __init__.py
|   +-- settings.py
|
|-- agent/
|   |-- __init__.py
|   |-- paypal_client.py
|   |-- tools.py
|   +-- gemini_agent.py
|
|-- web/
|   |-- __init__.py
|   |-- app.py
|   +-- routes.py
|
|-- templates/
|   +-- index.html
|
+-- static/
    |-- css/
    |   +-- style.css
    +-- js/
        +-- app.js
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| LLM | Google Gemini 3.8 Flash (function calling) |
| Payments | PayPal Orders v2 API (REST) |
| Backend | Python 3.11+, Flask 3.0 |
| Frontend | Vanilla HTML / CSS / JavaScript |
| i18n | Custom translation system (EN/FR/ES) |
| Design | Glassmorphism, CSS animations, SVG watermarks |

---

## 🔒 Security Notes

- Never commit your `.env` file — it contains your PayPal and Gemini credentials.
- The `.gitignore` is preconfigured to exclude `.env`.
- All PayPal interactions use the Sandbox environment by default.
- To go live, change `PAYPAL_ENV=live` in your `.env` and use production credentials.

---

## 📜 License

This project is licensed under the **MIT License**.
See the [LICENSE](./LICENSE) file for details.

Copyright (c) 2026 **Anio Joseph**

---

## 👤 Author

### **Anio Joseph**

**Developer & Architect of this project**

Built with 💙 for the **PayPal AI Hackathon 2026**
using the **PayPal Developer Platform** and **Google Gemini**.

---

⭐ If you find this project useful, consider giving it a star!

*© 2026 Anio Joseph — All rights reserved under the MIT License.*