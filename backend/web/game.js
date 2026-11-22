const state = {
  sessionId: null,
  composure: 100,
  turn: 0,
  mood: "从容",
};

const $ = (sel) => document.querySelector(sel);

function moodOf(c) {
  if (c >= 80) return "从容";
  if (c >= 50) return "不耐烦";
  if (c >= 20) return "慌乱";
  if (c > 0) return "濒临崩溃";
  return "崩溃";
}

function setComposure(c) {
  state.composure = c;
  $("#composure-num").textContent = c;
  $("#composure-bar").style.width = c + "%";
  state.mood = moodOf(c);
  $("#mood").textContent = state.mood;
}

function addLine(role, text, warn = false) {
  const div = document.createElement("div");
  div.className = "line " + role + (warn ? " warn" : "");
  const who = role === "detective" ? "你" : "嫌疑人";
  div.innerHTML = `<div class="who">${who}</div><div class="text"></div>`;
  div.querySelector(".text").textContent = text;
  const dlg = $("#dialog");
  dlg.appendChild(div);
  dlg.scrollTop = dlg.scrollHeight;
  return div.querySelector(".text");
}

async function startSession() {
  const r = await fetch("/api/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ case_id: "case_001" }),
  });
  const data = await r.json();
  state.sessionId = data.session_id;
  state.turn = 0;
  $("#turn-num").textContent = "0";
  $("#case-title").textContent = data.title;
  setComposure(data.composure);
  $("#brief-text").textContent = data.brief;
  $("#suspect").textContent = data.suspect_name;
  renderEvidence(data.evidence);
  $("#brief-evidence").innerHTML = data.evidence
    .map((e) => `<div><b>${e.name}</b>：${e.detail}</div>`)
    .join("");
}

function renderEvidence(list) {
  const box = $("#evidence-list");
  box.innerHTML = "";
  list.forEach((e) => {
    const el = document.createElement("div");
    el.className = "ev";
    el.textContent = e.name;
    el.dataset.id = e.id;
    box.appendChild(el);
  });
}

async function sendAsk(text) {
  if (!state.sessionId) return;
  addLine("detective", text);
  const target = addLine("suspect", "");
  const resp = await fetch("/api/interrogate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: state.sessionId, text }),
  });
  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    target.textContent += decoder.decode(value, { stream: true });
    const dlg = $("#dialog");
    dlg.scrollTop = dlg.scrollHeight;
  }
  state.turn += 1;
  $("#turn-num").textContent = state.turn;
}

function bindEvents() {
  $("#input-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const inp = $("#ask-input");
    const v = inp.value.trim();
    if (!v) return;
    inp.value = "";
    sendAsk(v);
  });
}

window.addEventListener("DOMContentLoaded", () => {
  bindEvents();
  startSession();
});