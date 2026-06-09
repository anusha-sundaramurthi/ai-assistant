(function () {
  "use strict";

  // ── Read config from script tag ───────────────────────
  const script    = document.currentScript || (function () {
    const scripts = document.getElementsByTagName("script");
    return scripts[scripts.length - 1];
  })();

  const WIDGET_ID   = script.getAttribute("data-widget-id") || "";
  const API_URL     = (script.getAttribute("data-api") || "").replace(/\/$/, "");
  const TITLE       = script.getAttribute("data-title")       || "AI Assistant";
  const COLOR       = script.getAttribute("data-color")       || "#4a9eff";
  const WELCOME     = script.getAttribute("data-welcome")     || "Hi! How can I help you today?";
  const LANGUAGE    = script.getAttribute("data-language")    || "English";
  const PLACEHOLDER = script.getAttribute("data-placeholder") || "Ask me anything...";
  const POSITION    = script.getAttribute("data-position")    || "right"; // left or right

  if (!WIDGET_ID || !API_URL) {
    console.error("[AI Widget] Missing data-widget-id or data-api attribute.");
    return;
  }

  // ── Session ID ────────────────────────────────────────
  const SESSION_ID = "aiw_" + Math.random().toString(36).substr(2, 9);

  // ── State ─────────────────────────────────────────────
  let isOpen              = false;
  let isTyping            = false;
  let pendingGeneralQuery = null;
  let messages            = [];

  // ── Helpers ───────────────────────────────────────────
  function darkenColor(hex, amount) {
    const num = parseInt(hex.replace("#", ""), 16);
    const r   = Math.max(0, (num >> 16) - amount);
    const g   = Math.max(0, ((num >> 8) & 0xff) - amount);
    const b   = Math.max(0, (num & 0xff) - amount);
    return "#" + ((r << 16) | (g << 8) | b).toString(16).padStart(6, "0");
  }

  function hexToRgba(hex, alpha) {
    const num = parseInt(hex.replace("#", ""), 16);
    const r   = (num >> 16) & 255;
    const g   = (num >> 8) & 255;
    const b   = num & 255;
    return `rgba(${r},${g},${b},${alpha})`;
  }

  function escapeHtml(text) {
    const d = document.createElement("div");
    d.textContent = text;
    return d.innerHTML;
  }

  function formatMessage(text) {
    // Convert markdown-like formatting to HTML
    return escapeHtml(text)
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.*?)\*/g, "<em>$1</em>")
      .replace(/^### (.+)$/gm, '<p class="aiw-heading3">$1</p>')
      .replace(/^## (.+)$/gm, '<p class="aiw-heading2">$1</p>')
      .replace(/^# (.+)$/gm, '<p class="aiw-heading1">$1</p>')
      .replace(/^- (.+)$/gm, '<li>$1</li>')
      .replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>')
      .replace(/(<li>.*<\/li>\n?)+/g, function(match) {
        return '<ul class="aiw-list">' + match + '</ul>';
      })
      .replace(/\n\n/g, '</p><p class="aiw-para">')
      .replace(/\n/g, "<br>")
      .replace(/^(?!<)(.+)/, '<p class="aiw-para">$1</p>');
  }

  // ── Inject styles ─────────────────────────────────────
  const css = `
    #aiw-container * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }

    #aiw-bubble {
      position: fixed;
      ${POSITION === "left" ? "left: 24px;" : "right: 24px;"}
      bottom: 24px;
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: ${COLOR};
      box-shadow: 0 4px 20px ${hexToRgba(COLOR, 0.4)};
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 999999;
      transition: transform 0.2s ease, box-shadow 0.2s ease;
      border: none;
      outline: none;
    }
    #aiw-bubble:hover {
      transform: scale(1.08);
      box-shadow: 0 6px 28px ${hexToRgba(COLOR, 0.5)};
    }
    #aiw-bubble svg { width: 26px; height: 26px; fill: white; transition: opacity 0.2s; }

    #aiw-badge {
      position: absolute;
      top: -2px;
      right: -2px;
      width: 14px;
      height: 14px;
      background: #ff4757;
      border-radius: 50%;
      border: 2px solid white;
      display: none;
    }

    #aiw-panel {
      position: fixed;
      ${POSITION === "left" ? "left: 24px;" : "right: 24px;"}
      bottom: 92px;
      width: 370px;
      max-width: calc(100vw - 32px);
      height: 560px;
      max-height: calc(100vh - 120px);
      background: #ffffff;
      border-radius: 20px;
      box-shadow: 0 12px 48px rgba(0,0,0,0.15), 0 2px 8px rgba(0,0,0,0.08);
      display: flex;
      flex-direction: column;
      overflow: hidden;
      z-index: 999998;
      opacity: 0;
      transform: translateY(16px) scale(0.97);
      pointer-events: none;
      transition: opacity 0.25s ease, transform 0.25s ease;
    }
    #aiw-panel.aiw-open {
      opacity: 1;
      transform: translateY(0) scale(1);
      pointer-events: all;
    }

    #aiw-header {
      background: ${COLOR};
      padding: 16px 18px;
      display: flex;
      align-items: center;
      gap: 12px;
      flex-shrink: 0;
    }
    #aiw-header-avatar {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: rgba(255,255,255,0.25);
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }
    #aiw-header-avatar svg { width: 20px; height: 20px; fill: white; }
    #aiw-header-info { flex: 1; }
    #aiw-header-title { color: white; font-size: 15px; font-weight: 600; line-height: 1.2; }
    #aiw-header-status { color: rgba(255,255,255,0.8); font-size: 12px; margin-top: 2px; display: flex; align-items: center; gap: 4px; }
    #aiw-status-dot { width: 7px; height: 7px; border-radius: 50%; background: #4ade80; display: inline-block; }
    #aiw-close-btn {
      background: rgba(255,255,255,0.2);
      border: none;
      border-radius: 50%;
      width: 30px;
      height: 30px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-size: 16px;
      transition: background 0.15s;
      flex-shrink: 0;
    }
    #aiw-close-btn:hover { background: rgba(255,255,255,0.3); }

    #aiw-messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      scroll-behavior: smooth;
    }
    #aiw-messages::-webkit-scrollbar { width: 4px; }
    #aiw-messages::-webkit-scrollbar-track { background: transparent; }
    #aiw-messages::-webkit-scrollbar-thumb { background: #e0e0e0; border-radius: 4px; }

    .aiw-msg { display: flex; flex-direction: column; max-width: 85%; animation: aiw-fadein 0.2s ease; }
    .aiw-msg-bot { align-self: flex-start; }
    .aiw-msg-user { align-self: flex-end; }

    .aiw-bubble-text {
      padding: 10px 14px;
      border-radius: 16px;
      font-size: 14px;
      line-height: 1.55;
      color: #1a1a1a;
    }
    .aiw-msg-bot .aiw-bubble-text {
      background: #f4f4f5;
      border-bottom-left-radius: 4px;
    }
    .aiw-msg-user .aiw-bubble-text {
      background: ${COLOR};
      color: white;
      border-bottom-right-radius: 4px;
    }
    .aiw-msg-time {
      font-size: 11px;
      color: #aaa;
      margin-top: 4px;
      padding: 0 4px;
    }
    .aiw-msg-bot .aiw-msg-time { align-self: flex-start; }
    .aiw-msg-user .aiw-msg-time { align-self: flex-end; }

    .aiw-list { padding-left: 18px; margin: 6px 0; }
    .aiw-list li { margin-bottom: 4px; }
    .aiw-para { margin-bottom: 6px; }
    .aiw-heading1 { font-size: 15px; font-weight: 700; margin-bottom: 6px; }
    .aiw-heading2 { font-size: 14px; font-weight: 700; margin-bottom: 4px; }
    .aiw-heading3 { font-size: 13px; font-weight: 600; margin-bottom: 4px; }

    .aiw-typing {
      display: flex;
      align-items: center;
      gap: 5px;
      padding: 12px 14px;
      background: #f4f4f5;
      border-radius: 16px;
      border-bottom-left-radius: 4px;
      width: fit-content;
    }
    .aiw-dot {
      width: 7px; height: 7px;
      border-radius: 50%;
      background: #999;
      animation: aiw-bounce 1.2s infinite;
    }
    .aiw-dot:nth-child(2) { animation-delay: 0.2s; }
    .aiw-dot:nth-child(3) { animation-delay: 0.4s; }

    .aiw-confirm-btns { display: flex; gap: 8px; margin-top: 8px; }
    .aiw-confirm-btn {
      padding: 7px 16px;
      border-radius: 20px;
      border: none;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      transition: opacity 0.15s;
    }
    .aiw-confirm-btn:hover { opacity: 0.85; }
    .aiw-confirm-yes { background: ${COLOR}; color: white; }
    .aiw-confirm-no  { background: #f0f0f0; color: #555; }

    #aiw-footer { padding: 12px 14px; border-top: 1px solid #f0f0f0; flex-shrink: 0; }
    #aiw-input-row { display: flex; gap: 8px; align-items: flex-end; }
    #aiw-input {
      flex: 1;
      border: 1.5px solid #e8e8e8;
      border-radius: 22px;
      padding: 10px 16px;
      font-size: 14px;
      outline: none;
      resize: none;
      max-height: 100px;
      line-height: 1.4;
      color: #1a1a1a;
      background: #fafafa;
      transition: border-color 0.15s;
      font-family: inherit;
    }
    #aiw-input:focus { border-color: ${COLOR}; background: white; }
    #aiw-input::placeholder { color: #bbb; }
    #aiw-send {
      width: 40px; height: 40px;
      border-radius: 50%;
      background: ${COLOR};
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      transition: opacity 0.15s, transform 0.15s;
    }
    #aiw-send:hover { opacity: 0.88; transform: scale(1.05); }
    #aiw-send:disabled { opacity: 0.45; cursor: not-allowed; transform: none; }
    #aiw-send svg { width: 18px; height: 18px; fill: white; }

    #aiw-powered {
      text-align: center;
      font-size: 11px;
      color: #ccc;
      margin-top: 8px;
    }
    #aiw-powered a { color: ${COLOR}; text-decoration: none; }

    @keyframes aiw-bounce {
      0%, 60%, 100% { transform: translateY(0); }
      30% { transform: translateY(-5px); }
    }
    @keyframes aiw-fadein {
      from { opacity: 0; transform: translateY(6px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    @media (max-width: 420px) {
      #aiw-panel { width: calc(100vw - 32px); ${POSITION === "left" ? "left: 16px;" : "right: 16px;"} }
    }
  `;

  const styleEl = document.createElement("style");
  styleEl.textContent = css;
  document.head.appendChild(styleEl);

  // ── Build DOM ─────────────────────────────────────────
  const container = document.createElement("div");
  container.id    = "aiw-container";

  // Bubble
  container.innerHTML = `
    <button id="aiw-bubble" aria-label="Open chat">
      <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2C6.477 2 2 6.477 2 12c0 1.89.525 3.66 1.438 5.168L2.05 21.5l4.518-1.374A9.953 9.953 0 0012 22c5.523 0 10-4.477 10-10S17.523 2 12 2zm0 18a7.95 7.95 0 01-4.073-1.117l-.292-.174-3.024.92.938-2.94-.19-.302A7.96 7.96 0 014 12c0-4.411 3.589-8 8-8s8 3.589 8 8-3.589 8-8 8z"/>
        <path d="M8 11h8v1.5H8zm0-3h5v1.5H8zm0 6h6v1.5H8z" opacity=".6"/>
      </svg>
      <div id="aiw-badge"></div>
    </button>

    <div id="aiw-panel" role="dialog" aria-label="Chat assistant">
      <div id="aiw-header">
        <div id="aiw-header-avatar">
          <svg viewBox="0 0 24 24"><path d="M12 2C6.477 2 2 6.477 2 12c0 1.89.525 3.66 1.438 5.168L2.05 21.5l4.518-1.374A9.953 9.953 0 0012 22c5.523 0 10-4.477 10-10S17.523 2 12 2z"/></svg>
        </div>
        <div id="aiw-header-info">
          <div id="aiw-header-title">${escapeHtml(TITLE)}</div>
          <div id="aiw-header-status"><span id="aiw-status-dot"></span> Online</div>
        </div>
        <button id="aiw-close-btn" aria-label="Close chat">✕</button>
      </div>

      <div id="aiw-messages"></div>

      <div id="aiw-footer">
        <div id="aiw-input-row">
          <textarea id="aiw-input" rows="1" placeholder="${escapeHtml(PLACEHOLDER)}" aria-label="Message"></textarea>
          <button id="aiw-send" aria-label="Send">
            <svg viewBox="0 0 24 24"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/></svg>
          </button>
        </div>
        <div id="aiw-powered">Powered by <a href="#" target="_blank">AI Widget</a></div>
      </div>
    </div>
  `;

  document.body.appendChild(container);

  // ── Element refs ──────────────────────────────────────
  const bubble   = document.getElementById("aiw-bubble");
  const panel    = document.getElementById("aiw-panel");
  const closeBtn = document.getElementById("aiw-close-btn");
  const messagesEl = document.getElementById("aiw-messages");
  const input    = document.getElementById("aiw-input");
  const sendBtn  = document.getElementById("aiw-send");
  const badge    = document.getElementById("aiw-badge");

  // ── Toggle panel ──────────────────────────────────────
  function openPanel() {
    isOpen = true;
    panel.classList.add("aiw-open");
    badge.style.display = "none";
    input.focus();
    if (messages.length === 0) addBotMessage(WELCOME);
  }

  function closePanel() {
    isOpen = false;
    panel.classList.remove("aiw-open");
  }

  bubble.addEventListener("click", function () {
    isOpen ? closePanel() : openPanel();
  });
  closeBtn.addEventListener("click", closePanel);

  // ── Time helper ───────────────────────────────────────
  function getTime() {
    return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  // ── Add messages ──────────────────────────────────────
  function addBotMessage(text, withConfirm) {
    const msg = { role: "bot", text, time: getTime() };
    messages.push(msg);

    const el       = document.createElement("div");
    el.className   = "aiw-msg aiw-msg-bot";
    el.innerHTML   = `
      <div class="aiw-bubble-text">${formatMessage(text)}</div>
      ${withConfirm ? `
        <div class="aiw-confirm-btns">
          <button class="aiw-confirm-btn aiw-confirm-yes" data-ans="yes">Yes, please</button>
          <button class="aiw-confirm-btn aiw-confirm-no"  data-ans="no">No thanks</button>
        </div>` : ""}
      <div class="aiw-msg-time">${msg.time}</div>
    `;

    if (withConfirm) {
      el.querySelectorAll(".aiw-confirm-btn").forEach(function (btn) {
        btn.addEventListener("click", function () {
          const ans = btn.getAttribute("data-ans");
          el.querySelectorAll(".aiw-confirm-btn").forEach(function (b) { b.disabled = true; b.style.opacity = "0.5"; });
          handleConfirm(ans);
        });
      });
    }

    messagesEl.appendChild(el);
    scrollToBottom();

    if (!isOpen) {
      badge.style.display = "block";
    }
  }

  function addUserMessage(text) {
    const msg = { role: "user", text, time: getTime() };
    messages.push(msg);
    const el     = document.createElement("div");
    el.className = "aiw-msg aiw-msg-user";
    el.innerHTML = `
      <div class="aiw-bubble-text">${escapeHtml(text)}</div>
      <div class="aiw-msg-time">${msg.time}</div>
    `;
    messagesEl.appendChild(el);
    scrollToBottom();
  }

  function showTyping() {
    const el     = document.createElement("div");
    el.className = "aiw-msg aiw-msg-bot";
    el.id        = "aiw-typing";
    el.innerHTML = `<div class="aiw-typing"><div class="aiw-dot"></div><div class="aiw-dot"></div><div class="aiw-dot"></div></div>`;
    messagesEl.appendChild(el);
    scrollToBottom();
  }

  function hideTyping() {
    const el = document.getElementById("aiw-typing");
    if (el) el.remove();
  }

  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  // ── API call ──────────────────────────────────────────
  async function askQuestion(query, useGeneral) {
    try {
      const res = await fetch(API_URL + "/ask", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({
          query:       query,
          session_id:  SESSION_ID,
          widget_id:   WIDGET_ID,
          language:    LANGUAGE,
          use_general: useGeneral || false
        })
      });
      if (!res.ok) throw new Error("Server error " + res.status);
      return await res.json();
    } catch (e) {
      throw e;
    }
  }

  // ── Handle confirm (yes/no general knowledge) ─────────
  async function handleConfirm(answer) {
    if (!pendingGeneralQuery) return;
    const query = pendingGeneralQuery;
    pendingGeneralQuery = null;

    if (answer === "yes") {
      showTyping();
      setInputDisabled(true);
      try {
        const data = await askQuestion(query, true);
        hideTyping();
        if (data.response) {
          addBotMessage(data.response);
        } else {
          addBotMessage("I couldn't find an answer. Please try rephrasing your question.");
        }
      } catch (e) {
        hideTyping();
        addBotMessage("Something went wrong. Please try again.");
      } finally {
        setInputDisabled(false);
      }
    } else {
      addBotMessage("No problem! Feel free to ask me anything else.");
    }
  }

  // ── Send message ──────────────────────────────────────
  async function sendMessage() {
    const text = input.value.trim();
    if (!text || isTyping) return;

    addUserMessage(text);
    input.value = "";
    autoResize();

    isTyping = true;
    setInputDisabled(true);
    showTyping();

    try {
      const data = await askQuestion(text, false);
      hideTyping();

      if (data.response === null || data.response === undefined) {
        // No PDF context — ask if user wants general knowledge
        pendingGeneralQuery = text;
        addBotMessage(
          "I don't have specific information about that in my documents.\n\nWould you like me to answer from my general knowledge?",
          true
        );
      } else {
        addBotMessage(data.response);
      }
    } catch (e) {
      hideTyping();
      addBotMessage("⚠️ Something went wrong. Please try again in a moment.");
    } finally {
      isTyping = false;
      setInputDisabled(false);
      input.focus();
    }
  }

  // ── Input controls ────────────────────────────────────
  function setInputDisabled(disabled) {
    input.disabled  = disabled;
    sendBtn.disabled = disabled;
  }

  function autoResize() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 100) + "px";
  }

  input.addEventListener("input", autoResize);

  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  sendBtn.addEventListener("click", sendMessage);

  // ── Close on outside click ────────────────────────────
  document.addEventListener("click", function (e) {
    if (isOpen && !panel.contains(e.target) && !bubble.contains(e.target)) {
      closePanel();
    }
  });

  // ── Keyboard accessibility ────────────────────────────
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && isOpen) closePanel();
  });

})();