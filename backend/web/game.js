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
    el.addEventListener("click", () => doPresent(e.id, el));
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
  document.querySelectorAll(".actions button").forEach((btn) => {
    btn.addEventListener("click", () => {
      const act = btn.dataset.act;
      if (act === "pressure") doPressure();
      else if (act === "observe") doObserve();
      else if (act === "accuse-open") $("#accuse-modal").classList.remove("hidden");
    });
  });
  $("#accuse-submit").addEventListener("click", submitAccuse);
  $("#accuse-cancel").addEventListener("click", () => $("#accuse-modal").classList.add("hidden"));
  $("#brief-start").addEventListener("click", () => $("#brief-modal").classList.add("hidden"));
  $("#result-restart").addEventListener("click", () => location.reload());
}

window.addEventListener("DOMContentLoaded", () => {
  bindEvents();
  startSession();
});

async function doPressure() {
  if (!state.sessionId) return;
  addLine("detective", "（猛地一拍桌子，厉声施压）");
  const r = await fetch("/api/pressure", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: state.sessionId }),
  });
  const d = await r.json();
  if (typeof d.composure === "number") setComposure(d.composure);
  if (d.lawyer_up) {
    const target = addLine("suspect", "");
    typeInto(target, d.message || "我要请律师，无可奉告。");
    setTimeout(() => showResult(false, "嫌疑人要求律师，审讯终止，你失败了。"), 1200);
  } else {
    addLine("suspect", "（嫌疑人被你的气势震了一下，没敢吭声）");
  }
  state.turn += 1;
  $("#turn-num").textContent = state.turn;
}

async function doObserve() {
  if (!state.sessionId) return;
  addLine("detective", "（仔细观察 ta 的微表情）");
  const r = await fetch("/api/observe", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: state.sessionId }),
  });
  const d = await r.json();
  const t = addLine("suspect", "");
  typeInto(t, "（旁白）" + (d.description || ""));
}

function typeInto(el, text) {
  let i = 0;
  const timer = setInterval(() => {
    el.textContent += text[i] || "";
    i++;
    if (i >= text.length) clearInterval(timer);
  }, 24);
}

async function doPresent(evidenceId, el) {
  if (!state.sessionId) return;
  const label = el ? el.textContent : evidenceId;
  addLine("detective", `（出示证据：${label}）`);
  const r = await fetch("/api/present", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: state.sessionId, lie_id: null, evidence_id: evidenceId }),
  });
  const d = await r.json();
  if (typeof d.composure === "number") setComposure(d.composure);
  if (d.hit) {
    if (el) el.classList.add("used");
    addLine("detective", "【矛盾！】" + (d.message || ""), true);
  } else {
    addLine("suspect", "（轻描淡写地）" + (d.message || "这能说明什么？"));
  }
  state.turn += 1;
  $("#turn-num").textContent = state.turn;
}

function showResult(win, text) {
  $("#result-title").textContent = win ? "破案！" : "审讯失败";
  $("#result-text").textContent = text;
  $("#result-modal").classList.remove("hidden");
}

async function submitAccuse() {
  const culprit = $("#accuse-culprit").value.trim();
  const method = $("#accuse-method").value.trim();
  const motive = $("#accuse-motive").value.trim();
  if (!culprit || !method || !motive) {
    alert("请填写完整");
    return;
  }
  const r = await fetch("/api/accuse", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: state.sessionId, culprit, method, motive }),
  });
  const d = await r.json();
  const truth = d.truth || {};
  showResult(d.win, `${d.reason}（真相：${truth.culprit} · ${truth.method} · ${truth.motive}）`);
}