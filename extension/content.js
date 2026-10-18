// AskDSA content script: injects a floating launcher + panel (isolated in a Shadow DOM),
// extracts the current problem title, and asks the backend for progressive hints.

(function () {
  if (window.__askdsaLoaded) return;      // avoid double-injection on SPA navigations
  window.__askdsaLoaded = true;

  // ---------- problem title extraction ----------
  function extractTitle() {
    const h1 = document.querySelector("h1");
    if (h1 && h1.textContent.trim().length > 2) return h1.textContent.trim();
    return (document.title || "")
      .replace(/\s*[|\-–]\s*(LeetCode|GeeksforGeeks|CodeChef|HackerRank).*$/i, "")
      .trim();
  }

  // ---------- minimal, safe markdown -> HTML ----------
  function escapeHtml(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  function inlineMd(s) {
    return s
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/\*([^*\n]+)\*/g, "<em>$1</em>");
  }
  function renderMarkdown(md) {
    const blocks = [];
    md = md.replace(/```[a-zA-Z0-9]*\n?([\s\S]*?)```/g, (_m, code) => {
      blocks.push(code.replace(/\n+$/, ""));
      return `\u0000B${blocks.length - 1}\u0000`;
    });
    md = escapeHtml(md);
    const out = [];
    let list = null;
    const closeList = () => { if (list) { out.push(`</${list}>`); list = null; } };
    for (const line of md.split("\n")) {
      let m;
      if ((m = line.match(/^\u0000B(\d+)\u0000\s*$/))) {
        closeList(); out.push(`<pre><code>${escapeHtml(blocks[+m[1]])}</code></pre>`);
      } else if ((m = line.match(/^\s*#{1,6}\s+(.*)$/))) {
        closeList(); out.push(`<h4>${inlineMd(m[1])}</h4>`);
      } else if ((m = line.match(/^\s*[-*]\s+(.*)$/))) {
        if (list !== "ul") { closeList(); out.push("<ul>"); list = "ul"; }
        out.push(`<li>${inlineMd(m[1])}</li>`);
      } else if ((m = line.match(/^\s*\d+\.\s+(.*)$/))) {
        if (list !== "ol") { closeList(); out.push("<ol>"); list = "ol"; }
        out.push(`<li>${inlineMd(m[1])}</li>`);
      } else if (line.trim() === "") {
        closeList();
      } else {
        closeList(); out.push(`<p>${inlineMd(line)}</p>`);
      }
    }
    closeList();
    let html = out.join("");
    html = html.replace(/\u0000B(\d+)\u0000/g,
      (_m, i) => `<pre><code>${escapeHtml(blocks[+i])}</code></pre>`);
    return html;
  }

  // ---------- UI (inside a Shadow DOM so the host page's CSS can't touch it) ----------
  const host = document.createElement("div");
  host.id = "askdsa-host";
  host.style.cssText = "position:fixed;z-index:2147483647;bottom:20px;left:20px;";
  document.body.appendChild(host);
  const root = host.attachShadow({ mode: "open" });

  root.innerHTML = `
    <style>
      :host { all: initial; }
      * { box-sizing: border-box; font-family: system-ui, Arial, sans-serif; }
      #launcher {
        background:#0EA5E9; color:#fff; border:none; border-radius:24px;
        padding:10px 16px; font-size:14px; font-weight:600; cursor:pointer;
        box-shadow:0 4px 14px rgba(0,0,0,.3);
      }
      #panel {
        display:none; width:360px; max-height:72vh; overflow:hidden;
        background:#fff; color:#1b2436; border-radius:12px;
        box-shadow:0 8px 30px rgba(0,0,0,.35); flex-direction:column;
      }
      #panel.open { display:flex; }
      header { background:#16213E; color:#fff; padding:12px 14px; }
      header .t { font-weight:700; font-size:15px; }
      header .p { font-size:12px; color:#9bb0d4; margin-top:2px;
                  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
      .body { padding:12px 14px; overflow:auto; }
      .levels { display:flex; gap:6px; margin-bottom:10px; }
      .levels button {
        flex:1; padding:6px 4px; font-size:11px; border:1px solid #cbd5e1;
        background:#f1f5f9; border-radius:6px; cursor:pointer;
      }
      .levels button.sel { background:#0EA5E9; color:#fff; border-color:#16213E; }
      textarea {
        width:100%; min-height:54px; padding:8px; font-size:13px;
        border:1px solid #cbd5e1; border-radius:6px; resize:vertical;
      }
      #ask {
        margin-top:8px; width:100%; padding:9px; background:#FF9900; color:#16213E;
        border:none; border-radius:6px; font-weight:700; cursor:pointer;
      }
      #ask:disabled { opacity:.6; cursor:default; }
            #answer { margin-top:12px; font-size:13px; line-height:1.5; word-wrap:break-word; }
      #answer p { margin:0 0 8px; }
      #answer h4 { margin:10px 0 4px; font-size:13px; }
      #answer ul, #answer ol { margin:4px 0 8px 18px; padding:0; }
      #answer li { margin:2px 0; }
      #answer code { background:#eef2f7; padding:1px 4px; border-radius:4px;
                     font-family:ui-monospace,Consolas,monospace; font-size:12px; }
      #answer pre { background:#0f1729; color:#e6edf3; padding:10px; border-radius:6px;
                    overflow:auto; }
      #answer pre code { background:transparent; color:inherit; padding:0; }
      .muted { color:#64748b; }
      .close { float:right; cursor:pointer; color:#9bb0d4; font-weight:700; }
    </style>

    <button id="launcher">🎓 AskDSA</button>

    <div id="panel">
      <header>
        <span class="close" id="close">✕</span>
        <div class="t">AskDSA Tutor</div>
        <div class="p" id="prob">—</div>
      </header>
      <div class="body">
        <div class="levels">
          <button data-level="1" class="sel">1 · Nudge</button>
          <button data-level="2">2 · Strategy</button>
          <button data-level="3">3 · Steps</button>
          <button data-level="4">4 · Solution</button>
        </div>
        <textarea id="q" placeholder="Ask something, or just click Ask for a hint…"></textarea>
                <button id="ask">Ask</button>
        <div id="answer" class="muted"></div>
      </div>
    </div>
  `;

  const $ = (sel) => root.querySelector(sel);
  const panel = $("#panel");
  const answerEl = $("#answer");
  const askBtn = $("#ask");
  let level = 1;
  const answers = {};          // level -> rendered HTML, cached so switching levels restores it

  $("#prob").textContent = extractTitle() || "(problem not detected)";

  function togglePanel() { panel.classList.toggle("open"); }
  $("#launcher").addEventListener("click", togglePanel);
  $("#close").addEventListener("click", () => panel.classList.remove("open"));

  function showLevel(l) {
    if (answers[l]) {
      answerEl.classList.remove("muted");
      answerEl.innerHTML = answers[l];
    } else {
      answerEl.classList.add("muted");
      answerEl.textContent =
        "No answer yet for this level — type a question (or leave it blank) and press Enter.";
    }
  }

  root.querySelectorAll(".levels button").forEach((b) => {
    b.addEventListener("click", () => {
      level = parseInt(b.dataset.level, 10);
      root.querySelectorAll(".levels button").forEach((x) => x.classList.remove("sel"));
      b.classList.add("sel");
      showLevel(level);          // restore this level's cached answer (if any)
    });
  });

  function ask() {
    const title = extractTitle();
    $("#prob").textContent = title || "(problem not detected)";
    const question = $("#q").value.trim();
    const query =
      `Problem: ${title || "(unknown)"}\n\n` +
      `Student's question: ${question || "Give me a hint for this problem."}`;

    const reqLevel = level;      // remember which level this request is for
    answerEl.classList.remove("muted");
    answerEl.textContent = "Thinking…";
    askBtn.disabled = true;

    chrome.runtime.sendMessage(
      { type: "tutor", payload: { query, level: reqLevel } },
      (resp) => {
        askBtn.disabled = false;
        if (chrome.runtime.lastError || !resp || !resp.ok) {
          answerEl.textContent = "Sorry the backend failed, please retry😭";
          return;
        }
        answers[reqLevel] = renderMarkdown(resp.answer);   // cache per level
        if (level === reqLevel) {                          // only paint if still viewing it
          answerEl.classList.remove("muted");
          answerEl.innerHTML = answers[reqLevel];
        }
      }
    );
  }

  $("#ask").addEventListener("click", ask);

  // Enter sends; Shift+Enter makes a new line.
  $("#q").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      ask();
    }
  });

  chrome.runtime.onMessage.addListener((msg) => {
    if (msg.type === "toggle") togglePanel();
  });
})();