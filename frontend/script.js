// =============================================================
// ML Interview Prep — Frontend Logic (Streaming version)
// =============================================================

const API_BASE = "http://localhost:5000";

// Configure marked.js — Markdown parser
marked.setOptions({ breaks: true, gfm: true });

// ── DOM REFERENCES ───────────────────────────────────────────
const messagesDiv = document.getElementById("messages");
const userInput   = document.getElementById("userInput");
const sendBtn     = document.getElementById("sendBtn");
const clearBtn    = document.getElementById("clearBtn");
const statusDot   = document.getElementById("statusDot");
const statusText  = document.getElementById("statusText");


// ── STATUS CHECK & LOAD SAVED CHATS ─────────────────────────
async function initApp() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (res.ok) {
      statusDot.className    = "status-dot online";
      statusText.textContent = "Gemini connected";
      // Once backend is confirmed online, restore saved chats
      await loadPastHistory();
    } else {
      throw new Error();
    }
  } catch {
    statusDot.className    = "status-dot offline";
    statusText.textContent = "Backend offline — run python app.py";
  }
}

async function loadPastHistory() {
  try {
    const res = await fetch(`${API_BASE}/history`);
    if (!res.ok) return;
    const data = await res.json();
    if (data.history && data.history.length > 0) {
      // Clear initial welcome message placeholder
      messagesDiv.innerHTML = "";
      for (const msg of data.history) {
        const role = msg.role === "assistant" ? "bot" : "user";
        renderMessage(role, msg.content, false);
      }
      messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
  } catch (err) {
    console.warn("Could not load past chat history:", err);
  }
}

initApp();


// ── RENDER A MESSAGE ─────────────────────────────────────────
function renderMessage(role, text = "", isThinking = false) {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${role === "user" ? "user-message" : "bot-message"}`;
  if (isThinking) wrapper.classList.add("thinking");

  const content = document.createElement("div");
  content.className = "message-content";

  if (isThinking) {
    content.innerHTML = `
      <div class="thinking-indicator">
        <span>✨ AI is preparing your answer</span>
        <span class="thinking-dots">
          <span></span><span></span><span></span>
        </span>
      </div>
    `;
  } else if (role === "user") {
    content.textContent = text;
  } else {
    content.innerHTML = marked.parse(text);
  }

  wrapper.appendChild(content);
  messagesDiv.appendChild(wrapper);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
  return wrapper;
}


// ── SEND MESSAGE (STREAMING) ──────────────────────────────────
async function sendMessage(messageText) {
  const text = messageText || userInput.value.trim();
  if (!text) return;

  userInput.value = "";
  autoResize(userInput);
  sendBtn.disabled = true;

  // 1. Show user message
  renderMessage("user", text);

  // 2. Show animated bot thinking bubble ("AI is preparing your answer...")
  const botWrapper = renderMessage("bot", "", true);
  const botContent = botWrapper.querySelector(".message-content");

  let accumulated = "";
  let streamDone   = false;

  try {
    const res = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text })
    });

    const reader  = res.body.getReader();
    const decoder = new TextDecoder();
    let   buffer  = "";

    while (!streamDone) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop();

      for (const event of events) {
        const line = event.trim();
        if (!line.startsWith("data: ")) continue;

        const payload = line.slice(6).trim();

        if (payload === "[DONE]") {
          streamDone = true;
          break;
        }

        try {
          const parsed = JSON.parse(payload);

          if (parsed.error) {
            botWrapper.classList.remove("thinking");
            botContent.textContent = `❌ ${parsed.error}`;
            streamDone = true;
            break;
          }

          if (parsed.chunk) {
            // As soon as the first token arrives, remove thinking animation
            if (!accumulated) {
              botWrapper.classList.remove("thinking");
            }
            accumulated += parsed.chunk;
            botContent.innerHTML = marked.parse(accumulated);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
          }
        } catch {
          // Malformed chunk ignored
        }
      }
    }

    // Safety net
    if (!accumulated && !botContent.textContent.startsWith("❌")) {
      botWrapper.classList.remove("thinking");
      botContent.textContent = "⚠️ No response received from model. Try asking again.";
    }

  } catch (err) {
    botWrapper.classList.remove("thinking");
    botContent.textContent = "❌ Could not reach the backend. Is python app.py running in your terminal?";
  }

  sendBtn.disabled = false;
  userInput.focus();
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}


// ── CLEAR HISTORY ────────────────────────────────────────────
async function clearHistory() {
  try {
    await fetch(`${API_BASE}/clear`, { method: "POST" });
  } catch {}
  messagesDiv.innerHTML = "";
  renderMessage("bot", "🔄 Chat cleared! Fresh session started.\n\nAsk me anything about ML interview prep.");
}


// ── AUTO-RESIZE TEXTAREA ──────────────────────────────────────
function autoResize(el) {
  el.style.height = "auto";
  el.style.height = el.scrollHeight + "px";
}


// ── EVENT LISTENERS ───────────────────────────────────────────
sendBtn.addEventListener("click", () => sendMessage());

userInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

userInput.addEventListener("input", () => autoResize(userInput));
clearBtn.addEventListener("click", clearHistory);

document.querySelector(".quick-prompts").addEventListener("click", (e) => {
  const btn = e.target.closest(".prompt-btn");
  if (btn?.dataset.prompt) sendMessage(btn.dataset.prompt);
});
