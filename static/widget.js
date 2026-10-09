/* Embeddable help chat.
 *
 * Add to any site:
 *   <script src="https://YOUR-BOT-HOST/widget.js" data-title="Help" data-color="#2f5d50" defer></script>
 *
 * Optional attributes: data-api (defaults to the script's own origin), data-title,
 * data-color, data-greeting, data-suggestions ("q1|q2|q3").
 */
(function () {
  if (window.__docsBotLoaded) return;
  window.__docsBotLoaded = true;

  var script = document.currentScript;
  var cfg = {
    api: (script && script.dataset.api) || (script ? new URL(script.src).origin : ""),
    title: (script && script.dataset.title) || "Help",
    color: (script && script.dataset.color) || "#2f5d50",
    greeting: (script && script.dataset.greeting) || "Hi! Ask me about shipping, returns, warranty or our bikes.",
    suggestions: ((script && script.dataset.suggestions) || "").split("|").filter(Boolean),
  };

  var css = `
  .dbw-btn{position:fixed;right:20px;bottom:20px;width:58px;height:58px;border-radius:50%;border:0;cursor:pointer;
    background:var(--dbw);color:#fff;box-shadow:0 6px 20px rgba(0,0,0,.18);z-index:2147483000;display:grid;place-items:center}
  .dbw-btn:focus-visible{outline:3px solid #fff;outline-offset:2px}
  .dbw-panel{position:fixed;right:20px;bottom:90px;width:min(380px,calc(100vw - 32px));height:min(560px,calc(100vh - 120px));
    background:#fff;border-radius:16px;box-shadow:0 12px 40px rgba(0,0,0,.2);display:none;flex-direction:column;overflow:hidden;
    z-index:2147483000;font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif;color:#1d2321}
  .dbw-panel.open{display:flex}
  .dbw-head{background:var(--dbw);color:#fff;padding:14px 16px;display:flex;justify-content:space-between;align-items:center}
  .dbw-head b{font-size:15px}.dbw-head small{display:block;opacity:.8;font-size:12px}
  .dbw-x{background:none;border:0;color:#fff;font-size:22px;cursor:pointer;line-height:1}
  .dbw-log{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:10px;background:#f6f7f6}
  .dbw-msg{max-width:85%;padding:9px 12px;border-radius:14px;white-space:pre-wrap;word-wrap:break-word}
  .dbw-bot{background:#fff;border:1px solid #e3e6e4;align-self:flex-start;border-bottom-left-radius:4px}
  .dbw-user{background:var(--dbw);color:#fff;align-self:flex-end;border-bottom-right-radius:4px}
  .dbw-src{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
  .dbw-chip{font-size:11.5px;border:1px solid #cfd6d2;background:#f3f6f4;border-radius:999px;padding:3px 9px;cursor:pointer;color:#2b3631}
  .dbw-snip{display:none;white-space:pre-wrap;margin-top:6px;font-size:12px;color:#4a5550;border-left:3px solid var(--dbw);padding:4px 8px;background:#f3f6f4}
  .dbw-snip.show{display:block}
  .dbw-sugg{display:flex;flex-wrap:wrap;gap:6px}
  .dbw-sugg button{font:inherit;font-size:12.5px;border:1px solid var(--dbw);color:var(--dbw);background:#fff;border-radius:999px;padding:5px 10px;cursor:pointer}
  .dbw-typing{color:#7a8580;font-style:italic}
  .dbw-form{display:flex;gap:8px;padding:10px;border-top:1px solid #e3e6e4;background:#fff}
  .dbw-form input{flex:1;border:1px solid #cfd6d2;border-radius:10px;padding:10px 12px;font:inherit}
  .dbw-form input:focus{outline:2px solid var(--dbw);border-color:transparent}
  .dbw-form button{border:0;border-radius:10px;padding:0 14px;background:var(--dbw);color:#fff;font:inherit;font-weight:600;cursor:pointer}
  .dbw-form button:disabled{opacity:.5;cursor:default}`;

  var style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);
  document.documentElement.style.setProperty("--dbw", cfg.color);

  var btn = el("button", "dbw-btn");
  btn.setAttribute("aria-label", "Open help chat");
  btn.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/></svg>';

  var panel = el("div", "dbw-panel");
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-label", cfg.title);
  var head = el("div", "dbw-head");
  head.innerHTML = "<div><b></b><small>Answers come from our help docs</small></div>";
  head.querySelector("b").textContent = cfg.title;
  var close = el("button", "dbw-x");
  close.setAttribute("aria-label", "Close chat");
  close.textContent = "×";
  head.appendChild(close);
  var log = el("div", "dbw-log");
  log.setAttribute("aria-live", "polite");
  var form = el("form", "dbw-form");
  var input = el("input");
  input.placeholder = "Type your question…";
  input.setAttribute("aria-label", "Your question");
  input.maxLength = 1000;
  var send = el("button");
  send.type = "submit";
  send.textContent = "Send";
  form.append(input, send);
  panel.append(head, log, form);
  document.body.append(panel, btn);

  var history = [];
  addBot(cfg.greeting, []);
  if (cfg.suggestions.length) {
    var sugg = el("div", "dbw-sugg");
    cfg.suggestions.forEach(function (q) {
      var b = el("button");
      b.type = "button";
      b.textContent = q;
      b.onclick = function () { sugg.remove(); ask(q); };
      sugg.appendChild(b);
    });
    log.appendChild(sugg);
  }

  btn.onclick = function () { panel.classList.toggle("open"); if (panel.classList.contains("open")) input.focus(); };
  close.onclick = function () { panel.classList.remove("open"); btn.focus(); };
  form.onsubmit = function (e) { e.preventDefault(); var q = input.value.trim(); if (q) ask(q); };

  function el(tag, cls) { var n = document.createElement(tag); if (cls) n.className = cls; return n; }

  function addUser(text) {
    var m = el("div", "dbw-msg dbw-user");
    m.textContent = text;
    log.appendChild(m);
    log.scrollTop = log.scrollHeight;
  }

  function addBot(text, sources) {
    var m = el("div", "dbw-msg dbw-bot");
    var p = el("div");
    p.textContent = text;
    m.appendChild(p);
    if (sources && sources.length) {
      var row = el("div", "dbw-src");
      sources.forEach(function (s) {
        var chip = el("button", "dbw-chip");
        chip.type = "button";
        chip.textContent = "📄 " + s.title.split(" > ").pop();
        chip.title = s.title;
        var snip = el("div", "dbw-snip");
        snip.textContent = s.snippet + (s.snippet.length >= 280 ? "…" : "");
        chip.onclick = function () { snip.classList.toggle("show"); };
        row.appendChild(chip);
        m.appendChild(snip);
      });
      m.insertBefore(row, m.querySelector(".dbw-snip"));
    }
    log.appendChild(m);
    log.scrollTop = log.scrollHeight;
  }

  function ask(q) {
    input.value = "";
    send.disabled = true;
    addUser(q);
    var typing = el("div", "dbw-msg dbw-bot dbw-typing");
    typing.textContent = "Checking the docs…";
    log.appendChild(typing);
    log.scrollTop = log.scrollHeight;
    fetch(cfg.api + "/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: q, history: history.slice(-10) }),
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        typing.remove();
        if (!res.ok) { addBot(res.j.detail || "Something went wrong, please try again.", []); return; }
        addBot(res.j.answer, res.j.sources);
        history.push({ role: "user", content: q }, { role: "assistant", content: res.j.answer });
      })
      .catch(function () { typing.remove(); addBot("Couldn't reach the help bot. Check your connection and try again.", []); })
      .finally(function () { send.disabled = false; input.focus(); });
  }
})();
