/* ── nav active state ──────────────────────────────── */
function setActive(section) {
  document.querySelectorAll(".nav-item").forEach(el => {
    const isActive = el.getAttribute("onclick")?.includes(section);
    el.classList.toggle("active", isActive);
    el.querySelector(".nav-arrow").textContent = isActive ? "▸" : "›";
  });
}

/* ── panel control ─────────────────────────────────── */
function openPanel(section) {
  setActive(section);

  const content = document.getElementById("content");
  content.innerHTML = "";

  const prompt = document.createElement("div");
  prompt.className = "prompt-line";
  prompt.textContent = `~/user $ cat ${section}.md`;
  content.appendChild(prompt);

  const title = document.createElement("div");
  title.className = "section-title";
  title.textContent = `═══ ${section.toUpperCase()} ${"═".repeat(Math.max(0, 46 - section.length))}`;
  content.appendChild(title);

  const body = document.createElement("div");
  body.id = "cv-body";
  content.appendChild(body);

  fetch(`content/${section}.md`)
    .then(r => r.text())
    .then(md => typeMarkdown(md, body))
    .catch(() => { body.textContent = "could not load content."; });
}

//* ── chat ──────────────────────────────────────────── */
let history = [];

async function submitChat() {
  const textarea = document.getElementById("chatInput");
  const raw = textarea.value.trim();
  if (!raw) return;

  textarea.value = "";
  textarea.disabled = true;

  const block = appendAIResponse(raw);

  try {
    const response = await fetch("http://localhost:8000/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: raw, history })
    });
    if (response.status === 429) {
        block.textContent = "too many requests, please slow down.";
        textarea.disabled = false;
        textarea.focus();
        return;
    }
    const data = await response.json();
    history = data.history;

    const main = document.querySelector(".main");

    typeMarkdown(data.answer, block, () => { main.scrollTop = main.scrollHeight; });

  } catch (err) {
    block.textContent = "error: could not reach the server.";
  } finally {
    textarea.disabled = false;
    textarea.focus();
  }
}

function handleChat(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    submitChat();
  }
}

function appendAIResponse(question) {
  const content = document.getElementById("content");
  const main = document.querySelector(".main");

  // user question block
  const userDivider = document.createElement("div");
  userDivider.className = "user-divider";
  userDivider.textContent = "── ? USER QUESTION " + "─".repeat(55);
  content.appendChild(userDivider);

  const userText = document.createElement("div");
  userText.className = "user-text";
  userText.textContent = question;
  content.appendChild(userText);

  main.scrollTop = main.scrollHeight;

  // ai response block
  const divider = document.createElement("div");
  divider.className = "ascii-divider";
  divider.textContent = "── ∷ AI RESPONSE " + "─".repeat(57);
  content.appendChild(divider);

  const block = document.createElement("div");
  block.className = "ai-block";
  block.textContent = "thinking...";
  content.appendChild(block);

  return block;
}

/* ── word-by-word markdown typewriter ──────────────── */
function typeMarkdown(md, el, onDone) {
  const words = md.split(" ");
  let i = 0;

  const interval = setInterval(() => {
    renderMarkdown(words.slice(0, i + 1).join(" "), el);
    i++;
    if (i >= words.length) {
      clearInterval(interval);
      if (onDone) onDone();
    }
  }, 20);
}

/* ── char-by-char plain text typewriter ────────────── */
function typeText(text, el, onDone) {
  el.textContent = "";
  let i = 0;

  const interval = setInterval(() => {
    el.textContent += text[i];
    i++;
    if (i >= text.length) {
      clearInterval(interval);
      if (onDone) onDone();
    }
  }, 1);
}

/* ── init ──────────────────────────────────────────── */
window.onload = () => {
  document.getElementById("chatInput").addEventListener("keydown", handleChat);
  openPanel("experience");
};