/* ── markdown.js ───────────────────────────────────────
   Supported syntax:
     # H1   ## H2   ### H3
     **bold**   *italic*   ***bold italic***
     [text](url)
     - bullet item  (also * and +)
   ─────────────────────────────────────────────────── */

function parseMarkdown(raw) {
  const lines = raw.split("\n");
  const out = [];
  let inList = false;

  for (let i = 0; i < lines.length; i++) {
    let line = lines[i];

    /* ── headings ──────────────────────────────────── */
    const h3 = line.match(/^###\s+(.*)/);
    const h2 = line.match(/^##\s+(.*)/);
    const h1 = line.match(/^#\s+(.*)/);

    if (h1) {
      if (inList) { out.push("</ul>"); inList = false; }
      out.push(`<h1 class="md-h1">${inlineFormat(h1[1])}</h1>`);
      continue;
    }
    if (h2) {
      if (inList) { out.push("</ul>"); inList = false; }
      out.push(`<h2 class="md-h2">${inlineFormat(h2[1])}</h2>`);
      continue;
    }
    if (h3) {
      if (inList) { out.push("</ul>"); inList = false; }
      out.push(`<h3 class="md-h3">${inlineFormat(h3[1])}</h3>`);
      continue;
    }

    /* ── bullet list ───────────────────────────────── */
    const bullet = line.match(/^[-*+]\s+(.*)/);
    if (bullet) {
      if (!inList) { out.push('<ul class="md-list">'); inList = true; }
      out.push(`<li>${inlineFormat(bullet[1])}</li>`);
      continue;
    }

    /* ── close list on blank or non-bullet line ────── */
    if (inList) { out.push("</ul>"); inList = false; }

    /* ── blank line ────────────────────────────────── */
    if (line.trim() === "") {
      out.push('<div class="md-spacer"></div>');
      continue;
    }

    /* ── paragraph ─────────────────────────────────── */
    out.push(`<p class="md-p">${inlineFormat(line)}</p>`);
  }

  if (inList) out.push("</ul>");
  return out.join("\n");
}

/* ── inline formatting ─────────────────────────────── */
function inlineFormat(text) {
  /* escape HTML first to avoid injection */
  text = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  /* order matters: bold italic before bold before italic */
  text = text.replace(/\*\*\*(.*?)\*\*\*/g, '<span class="md-bolditalic">$1</span>');
  text = text.replace(/\*\*(.*?)\*\*/g,     '<span class="md-bold">$1</span>');
  text = text.replace(/\*(.*?)\*/g,         '<span class="md-italic">$1</span>');

  /* links */
  text = text.replace(
    /\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g,
    '<a class="md-link" href="$2" target="_blank" rel="noopener">$1</a>'
  );

  return text;
}

/* ── render into element ───────────────────────────── */
function renderMarkdown(raw, el) {
  el.innerHTML = parseMarkdown(raw);
}