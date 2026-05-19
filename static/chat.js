/* ═══════════════════════════════════════════════════
   S.H.I.E.L.D. TERMINAL — chat.js
   Preserves: /api/chat, #chat-container, #query-input,
              #btn-send, #typing-indicator,
              .message.bot/.user, .meta-info, .source-tag
   ═══════════════════════════════════════════════════ */

/* ── DOM refs ── */
const chatContainer = document.getElementById("chat-container");
const input         = document.getElementById("query-input");
const btn           = document.getElementById("btn-send");
const typing        = document.getElementById("typing-indicator");

/* ════════════════════════════════════════
   CANVAS BACKGROUND — Hexagonal grid + particles
   ════════════════════════════════════════ */
(function initCanvas() {
  const canvas = document.getElementById("bg-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  let W, H, nodes;

  const NODE_COUNT  = 60;
  const LINK_DIST   = 140;
  const NODE_SPEED  = 0.25;
  const NODE_RADIUS = 1.5;
  const COLOR       = "rgba(0, 212, 255, 1)";

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }

  function makeNode() {
    return {
      x:  Math.random() * W,
      y:  Math.random() * H,
      vx: (Math.random() - 0.5) * NODE_SPEED,
      vy: (Math.random() - 0.5) * NODE_SPEED,
    };
  }

  function init() {
    nodes = Array.from({ length: NODE_COUNT }, makeNode);
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);

    // Move nodes
    nodes.forEach(n => {
      n.x += n.vx;
      n.y += n.vy;
      if (n.x < 0 || n.x > W) n.vx *= -1;
      if (n.y < 0 || n.y > H) n.vy *= -1;
    });

    // Draw links
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx   = nodes[i].x - nodes[j].x;
        const dy   = nodes[i].y - nodes[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < LINK_DIST) {
          const alpha = (1 - dist / LINK_DIST) * 0.45;
          ctx.beginPath();
          ctx.moveTo(nodes[i].x, nodes[i].y);
          ctx.lineTo(nodes[j].x, nodes[j].y);
          ctx.strokeStyle = `rgba(0, 212, 255, ${alpha})`;
          ctx.lineWidth   = 0.6;
          ctx.stroke();
        }
      }
    }

    // Draw nodes
    nodes.forEach(n => {
      ctx.beginPath();
      ctx.arc(n.x, n.y, NODE_RADIUS, 0, Math.PI * 2);
      ctx.fillStyle = COLOR;
      ctx.shadowColor = "rgba(0, 212, 255, 0.8)";
      ctx.shadowBlur  = 6;
      ctx.fill();
      ctx.shadowBlur  = 0;
    });

    requestAnimationFrame(draw);
  }

  window.addEventListener("resize", () => { resize(); init(); });
  resize();
  init();
  draw();
})();

/* ════════════════════════════════════════
   UPTIME COUNTER
   ════════════════════════════════════════ */
(function initUptime() {
  const el = document.getElementById("uptime-counter");
  if (!el) return;
  let seconds = 0;
  setInterval(() => {
    seconds++;
    const h = String(Math.floor(seconds / 3600)).padStart(2, "0");
    const m = String(Math.floor((seconds % 3600) / 60)).padStart(2, "0");
    const s = String(seconds % 60).padStart(2, "0");
    el.textContent = `${h}:${m}:${s}`;
  }, 1000);
})();

/* ════════════════════════════════════════
   AUTO TIMESTAMPS
   ════════════════════════════════════════ */
function nowTimestamp() {
  return new Date().toLocaleTimeString("es-ES", { hour12: false });
}

/* Fill initial welcome timestamp */
document.querySelectorAll("[data-auto-time]").forEach(el => {
  el.textContent = nowTimestamp();
});

/* ════════════════════════════════════════
   CHAT LOGIC
   ════════════════════════════════════════ */
function addMessage(text, type, extra = null) {
  const wrapper = document.createElement("div");
  wrapper.className = `message ${type}`;

  // Header (agent tag + timestamp)
  const header = document.createElement("div");
  header.className = "msg-header";

  const agentTag = document.createElement("span");
  agentTag.className = "agent-tag";

  if (type === "bot") {
    agentTag.textContent = extra
      ? `◈ ${extra.agent}`
      : "◈ AGENTE IA";
  } else {
    agentTag.textContent = "◎ AGENTE OPERATIVO";
  }

  const ts = document.createElement("span");
  ts.className   = "msg-ts";
  ts.textContent = nowTimestamp();

  header.appendChild(agentTag);
  header.appendChild(ts);

  // Body
  const body = document.createElement("div");
  body.className   = "msg-body";
  body.innerHTML   = text.replace(/\n/g, "<br>");

  // Sources
  if (extra && extra.sources && extra.sources.length > 0) {
    const meta = document.createElement("div");
    meta.className = "meta-info";
    meta.innerHTML =
      extra.sources.map(s => `<span class="source-tag">📄 ${s}</span>`).join("");
    body.appendChild(meta);
  }

  wrapper.appendChild(header);
  wrapper.appendChild(body);
  chatContainer.appendChild(wrapper);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

async function send() {
  const msg = input.value.trim();
  if (!msg) return;

  addMessage(msg, "user");
  input.value = "";

  // Show typing indicator as flex
  typing.style.display = "flex";
  btn.disabled = true;

  try {
    const res = await fetch("/api/chat", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ message: msg })
    });
    const data = await res.json();

    addMessage(data.reply, "bot", {
      agent:   data.agent ? data.agent.toUpperCase() : "AGENTE IA",
      sources: data.sources || []
    });
  } catch (e) {
    addMessage("⚠ Error de comunicación con el servidor central.", "bot");
  } finally {
    typing.style.display = "none";
    btn.disabled = false;
    input.focus();
  }
}

function quick(text) {
  input.value = text;
  send();
}

function clearChat() {
  chatContainer.innerHTML = `
    <div class="message bot">
      <div class="msg-header">
        <span class="agent-tag">◈ AGENTE IA</span>
        <span class="msg-ts">${nowTimestamp()}</span>
      </div>
      <div class="msg-body">
        Historial purgado. Terminal S.H.I.E.L.D. lista para nuevas consultas.
      </div>
    </div>
  `;
}

btn.addEventListener("click", send);
input.addEventListener("keypress", e => { if (e.key === "Enter") send(); });
