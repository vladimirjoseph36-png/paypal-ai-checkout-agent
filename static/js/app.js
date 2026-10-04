/* ==========================================================================
   PayPal AI Checkout Agent — Logique du chat + i18n + fond anime
   --------------------------------------------------------------------------
   Author  : Anio Joseph
   Project : PayPal AI Hackathon 2026
   --------------------------------------------------------------------------
   Organisation du fichier :
     1. Traductions (i18n)
     2. Fond anime : mosaique de logos PayPal + particules
     3. Chat : envoi, rendu, gestion d'erreurs
   ========================================================================== */


/* ==========================================================================
   1. TRADUCTIONS (i18n)
   ========================================================================== */

const TRANSLATIONS = {
  en: {
    app_title: "PayPal AI Checkout Agent",
    status_online: "Agent online · Sandbox",
    welcome_message:
      "Hello 👋 I'm your personal shopping assistant. " +
      "Tell me what you want to buy and at what price, " +
      "I'll create the PayPal order for you in seconds.",
    suggestion_1: "I want to buy a bluetooth headset for $49.99",
    suggestion_2: "Buy a gaming mouse for $29.99",
    suggestion_3: "A mechanical keyboard for $89",
    input_placeholder: "Describe your purchase…",
    send_button: "Send",
    typing_error: "❌ Error: ",
    typing_network: "❌ Network error: "
  },
  fr: {
    app_title: "PayPal AI Checkout Agent",
    status_online: "Agent en ligne · Sandbox",
    welcome_message:
      "Bonjour 👋 Je suis votre assistant d'achat personnel. " +
      "Dites-moi ce que vous voulez acheter et à quel prix, " +
      "je crée la commande PayPal pour vous en quelques secondes.",
    suggestion_1: "Je veux acheter un casque bluetooth à 49.99$",
    suggestion_2: "Acheter une souris gaming à 29.99$",
    suggestion_3: "Un clavier mécanique à 89$",
    input_placeholder: "Décrivez votre achat…",
    send_button: "Envoyer",
    typing_error: "❌ Erreur : ",
    typing_network: "❌ Erreur réseau : "
  },
  es: {
    app_title: "PayPal AI Checkout Agent",
    status_online: "Agente en línea · Sandbox",
    welcome_message:
      "Hola 👋 Soy tu asistente personal de compras. " +
      "Dime qué quieres comprar y a qué precio, " +
      "crearé el pedido de PayPal para ti en segundos.",
    suggestion_1: "Quiero comprar unos auriculares bluetooth por $49.99",
    suggestion_2: "Comprar un ratón gaming por $29.99",
    suggestion_3: "Un teclado mecánico por $89",
    input_placeholder: "Describe tu compra…",
    send_button: "Enviar",
    typing_error: "❌ Error: ",
    typing_network: "❌ Error de red: "
  }
};

const DEFAULT_LANG = "en";
const SUPPORTED_LANGS = ["en", "fr", "es"];

/**
 * Recupere la langue courante depuis localStorage (fallback : anglais).
 * @returns {string} Code de langue ("en", "fr", "es")
 */
function getCurrentLang() {
  const stored = localStorage.getItem("app_lang");
  return SUPPORTED_LANGS.includes(stored) ? stored : DEFAULT_LANG;
}

/**
 * Applique les traductions sur tous les elements marques
 * avec data-i18n ou data-i18n-placeholder.
 * @param {string} lang - Code de langue
 */
function applyTranslations(lang) {
  const t = TRANSLATIONS[lang] || TRANSLATIONS[DEFAULT_LANG];
  document.documentElement.lang = lang;

  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.dataset.i18n;
    if (t[key]) el.textContent = t[key];
  });

  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    const key = el.dataset.i18nPlaceholder;
    if (t[key]) el.placeholder = t[key];
  });
}


/* ==========================================================================
   2. FOND ANIME — Mosaique de logos PayPal + particules
   ========================================================================== */

(function initBackground() {
  const layer = document.querySelector(".background-layer");
  if (!layer) return;

  const svgNS = "http://www.w3.org/2000/svg";

  /**
   * Genere un petit logo PayPal (double P + texte "PayPal").
   * @param {string} uid - Identifiant unique pour eviter les collisions
   *                      d'ID entre les gradients SVG.
   * @returns {SVGElement}
   */
  function createPayPalLogo(uid) {
    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("viewBox", "0 0 320 120");
    svg.classList.add("paypal-watermark");

    svg.innerHTML = `
      <defs>
        <linearGradient id="ppG1-${uid}" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#0070ba"/>
          <stop offset="100%" stop-color="#00a8e8"/>
        </linearGradient>
        <linearGradient id="ppG2-${uid}" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#00a8e8"/>
          <stop offset="100%" stop-color="#4fc3f7"/>
        </linearGradient>
      </defs>

      <!-- Double P stylise -->
      <g transform="translate(20, 5)">
        <path fill="url(#ppG1-${uid})" d="
          M 15 15 L 55 15
          C 78 15, 88 30, 83 52
          C 78 74, 60 85, 38 85
          L 22 85 L 15 120 L -8 120 Z"/>
        <path fill="url(#ppG2-${uid})" opacity="0.9" d="
          M 40 32 L 80 32
          C 103 32, 113 47, 108 69
          C 103 91, 85 102, 63 102
          L 47 102 L 40 137 L 17 137 Z"/>
      </g>

      <!-- Texte "PayPal" -->
      <text x="120" y="85"
            font-family="Inter, sans-serif"
            font-size="56"
            font-weight="800"
            fill="url(#ppG1-${uid})"
            letter-spacing="-2">PayPal</text>
    `;
    return svg;
  }

  /**
   * Remplit le fond avec une mosaique de petits logos PayPal.
   * Chaque logo a une position, taille, rotation et opacite aleatoires
   * pour un rendu naturel et non-repetitif.
   */
  function createLogoMosaic() {
    const container = document.createElement("div");
    container.className = "logo-mosaic";

    const COLS = 6;   // colonnes de la grille
    const ROWS = 4;   // lignes de la grille
    const TOTAL = COLS * ROWS;

    for (let i = 0; i < TOTAL; i++) {
      const logo = createPayPalLogo(`m${i}`);

      const col = i % COLS;
      const row = Math.floor(i / COLS);

      // Position avec un leger jitter pour casser la regularite
      const xPercent = (col / COLS) * 100 + (Math.random() * 8 - 4);
      const yPercent = (row / ROWS) * 100 + (Math.random() * 8 - 4);

      // Taille : entre 110 et 170 px
      const width = (110 + Math.random() * 60).toFixed(0);

      // Opacite de base : entre 0.05 et 0.11
      const baseOpacity = (0.05 + Math.random() * 0.06).toFixed(2);

      // Rotation aleatoire entre -20 et +20 degres
      const rot = (Math.random() * 40 - 20).toFixed(1);

      logo.style.position = "absolute";
      logo.style.left = xPercent + "%";
      logo.style.top = yPercent + "%";
      logo.style.width = width + "px";
      logo.style.height = "auto";
      logo.style.setProperty("--base-opacity", baseOpacity);
      logo.style.setProperty("--rot", rot + "deg");
      logo.style.transform = `rotate(${rot}deg) translate(-50%, -50%)`;
      logo.style.animationDelay = (Math.random() * 8).toFixed(2) + "s";
      logo.style.animationDuration = (6 + Math.random() * 6).toFixed(2) + "s";

      container.appendChild(logo);
    }

    layer.appendChild(container);
  }

  createLogoMosaic();

  /* --- Particules flottantes --- */
  const particles = document.createElement("div");
  particles.className = "particles";
  layer.appendChild(particles);

  const PARTICLE_COUNT = 25;
  for (let i = 0; i < PARTICLE_COUNT; i++) {
    const p = document.createElement("div");
    p.className = "particle";
    p.style.left = Math.random() * 100 + "%";
    p.style.top = 100 + Math.random() * 20 + "%";
    p.style.animationDuration = 12 + Math.random() * 18 + "s";
    p.style.animationDelay = Math.random() * 15 + "s";

    const size = 2 + Math.random() * 4;
    p.style.width = size + "px";
    p.style.height = size + "px";
    p.style.background = Math.random() > 0.5 ? "#00a8e8" : "#4fc3f7";

    particles.appendChild(p);
  }
})();


/* ==========================================================================
   3. CHAT — Interface conversationnelle
   ========================================================================== */

const chat = document.getElementById("chat");
const input = document.getElementById("input");
const sendBtn = document.getElementById("send");
const suggestions = document.getElementById("suggestions");
const langSelect = document.getElementById("lang-select");

let currentLang = getCurrentLang();

/* --- Initialisation de la langue --- */
langSelect.value = currentLang;
applyTranslations(currentLang);

langSelect.addEventListener("change", () => {
  currentLang = langSelect.value;
  localStorage.setItem("app_lang", currentLang);
  applyTranslations(currentLang);
  input.focus();
});

/* --- Envoi avec la touche Entree --- */
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

/* --- Boutons de suggestion --- */
document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    input.value = chip.textContent.trim();
    sendMessage();
  });
});

sendBtn.addEventListener("click", sendMessage);

/**
 * Ajoute un message dans la zone de chat.
 * @param {string} text - Contenu textuel
 * @param {"user"|"agent"} role - Qui parle
 */
function addMessage(text, role) {
  const msg = document.createElement("div");
  msg.className = "message " + role;

  const avatarLabel = role === "user" ? "Me" : "AI";
  msg.innerHTML = `
    <div class="avatar">${avatarLabel}</div>
    <div class="bubble">${formatText(text)}</div>
  `;

  chat.appendChild(msg);
  chat.scrollTop = chat.scrollHeight;
}

/**
 * Echappe le HTML puis transforme les liens Markdown
 * [texte](url) en balises <a> cliquables.
 * @param {string} text - Texte brut
 * @returns {string} HTML sur
 */
function formatText(text) {
  const esc = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  return esc.replace(
    /\[([^\]]+)\]\((https?:[^)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener">$1</a>'
  );
}

/**
 * Affiche l'indicateur de frappe (3 points animes).
 */
function showTyping() {
  const t = document.createElement("div");
  t.className = "message agent";
  t.id = "typing";
  t.innerHTML = `
    <div class="avatar">AI</div>
    <div class="bubble typing"><span></span><span></span><span></span></div>
  `;
  chat.appendChild(t);
  chat.scrollTop = chat.scrollHeight;
}

/**
 * Retire l'indicateur de frappe s'il est present.
 */
function hideTyping() {
  const t = document.getElementById("typing");
  if (t) t.remove();
}

/**
 * Envoie le message courant au backend Flask
 * et affiche la reponse de l'agent.
 */
async function sendMessage() {
  const message = input.value.trim();
  if (!message) return;

  const t = TRANSLATIONS[currentLang] || TRANSLATIONS[DEFAULT_LANG];

  suggestions.style.display = "none";
  addMessage(message, "user");
  input.value = "";
  input.disabled = true;
  sendBtn.disabled = true;
  showTyping();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, lang: currentLang }),
    });

    const data = await res.json();
    hideTyping();

    if (data.error) {
      addMessage(t.typing_error + data.error, "agent");
    } else {
      addMessage(data.reply, "agent");
    }
  } catch (err) {
    hideTyping();
    addMessage(t.typing_network + err.message, "agent");
  } finally {
    input.disabled = false;
    sendBtn.disabled = false;
    input.focus();
  }
}

/* --- Focus initial sur la zone de saisie --- */
input.focus();