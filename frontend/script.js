const API_BASE = ""; // same-origin, served by FastAPI

/* ---------------- auth state ---------------- */
let authToken = localStorage.getItem("edugenie_token") || null;
let authUsername = localStorage.getItem("edugenie_username") || null;

function authHeaders() {
  return authToken ? { Authorization: `Bearer ${authToken}` } : {};
}

function renderAuthArea() {
  const area = document.getElementById("authArea");
  if (authToken) {
    area.innerHTML = `
      <span class="auth-username">${authUsername}</span>
      <button class="auth-btn" id="logoutBtn">Log out</button>`;
    document.getElementById("logoutBtn").addEventListener("click", logout);
  } else {
    area.innerHTML = `<button class="auth-btn" id="loginBtn">Log in</button>`;
    document.getElementById("loginBtn").addEventListener("click", () => openAuthModal("login"));
  }
}

let authMode = "login";

function openAuthModal(mode) {
  authMode = mode;
  document.getElementById("authModalTitle").textContent = mode === "login" ? "Log in" : "Register";
  document.getElementById("authSubmitBtn").textContent = mode === "login" ? "Log in" : "Register";
  document.getElementById("authSwitchBtn").textContent =
    mode === "login" ? "Need an account? Register" : "Already have an account? Log in";
  document.getElementById("authError").textContent = "";
  document.getElementById("auth-username").value = "";
  document.getElementById("auth-password").value = "";
  document.getElementById("authModal").style.display = "flex";
}

function closeAuthModal() {
  document.getElementById("authModal").style.display = "none";
}

document.getElementById("authCloseBtn").addEventListener("click", closeAuthModal);
document.getElementById("authSwitchBtn").addEventListener("click", () => {
  openAuthModal(authMode === "login" ? "register" : "login");
});

document.getElementById("authSubmitBtn").addEventListener("click", async () => {
  const username = document.getElementById("auth-username").value.trim();
  const password = document.getElementById("auth-password").value;
  const errorEl = document.getElementById("authError");
  errorEl.textContent = "";

  if (!username || !password) {
    errorEl.textContent = "Please fill in both fields.";
    return;
  }

  const endpoint = authMode === "login" ? "/api/login" : "/api/register";
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Something went wrong.");

    authToken = data.token;
    authUsername = data.username;
    localStorage.setItem("edugenie_token", authToken);
    localStorage.setItem("edugenie_username", authUsername);
    renderAuthArea();
    closeAuthModal();
  } catch (err) {
    errorEl.textContent = err.message;
  }
});

async function logout() {
  await fetch(`${API_BASE}/api/logout`, { method: "POST", headers: authHeaders() });
  authToken = null;
  authUsername = null;
  localStorage.removeItem("edugenie_token");
  localStorage.removeItem("edugenie_username");
  renderAuthArea();
}

renderAuthArea();

/* ---------------- history ---------------- */
async function loadHistory() {
  const container = document.getElementById("result-history");
  const loggedOutMsg = document.getElementById("historyLoggedOut");

  if (!authToken) {
    loggedOutMsg.style.display = "block";
    container.innerHTML = "";
    return;
  }
  loggedOutMsg.style.display = "none";
  showLoading(container, "Pulling up your history…");

  try {
    const res = await fetch(`${API_BASE}/api/history`, { headers: authHeaders() });
    if (!res.ok) throw new Error("Could not load history.");
    const items = await res.json();
    if (items.length === 0) {
      container.innerHTML = `<div class="card"><p>No history yet — try Ask, Quiz, Summarize, or Learning path first.</p></div>`;
      return;
    }
    container.innerHTML = items
      .map(
        (item) => `
      <div class="history-item">
        <div class="history-feature">${item.feature}</div>
        <div class="history-summary">${item.request_summary || ""}</div>
        <div class="history-date">${item.created_at}</div>
      </div>`
      )
      .join("");
  } catch (err) {
    showError(container, err);
  }
}

/* ---------------- tab switching ---------------- */
const tabBtns = document.querySelectorAll(".tab-btn");
const panels = document.querySelectorAll(".panel");

tabBtns.forEach((btn) => {
  btn.addEventListener("click", () => {
    tabBtns.forEach((b) => { b.classList.remove("is-active"); b.setAttribute("aria-selected", "false"); });
    panels.forEach((p) => p.classList.remove("is-active"));
    btn.classList.add("is-active");
    btn.setAttribute("aria-selected", "true");
    document.getElementById(`panel-${btn.dataset.tab}`).classList.add("is-active");
    if (btn.dataset.tab === "history") loadHistory();
  });
});

/* ---------------- chalk dust burst ---------------- */
function dustBurst(x, y) {
  const layer = document.getElementById("dustLayer");
  for (let i = 0; i < 14; i++) {
    const mote = document.createElement("div");
    mote.className = "dust-mote";
    const angle = Math.random() * Math.PI * 2;
    const dist = 30 + Math.random() * 50;
    mote.style.left = `${x}px`;
    mote.style.top = `${y}px`;
    mote.style.setProperty("--dx", `${Math.cos(angle) * dist}px`);
    mote.style.setProperty("--dy", `${Math.sin(angle) * dist}px`);
    mote.style.animationDelay = `${Math.random() * 120}ms`;
    layer.appendChild(mote);
    setTimeout(() => mote.remove(), 1200);
  }
}

function burstNear(el) {
  const rect = el.getBoundingClientRect();
  dustBurst(rect.left + rect.width / 2, rect.top);
}

/* ---------------- status pill ---------------- */
async function checkHealth() {
  const pill = document.getElementById("statusPill");
  const notice = document.getElementById("demoNotice");
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    const data = await res.json();
    if (data.demo_mode) {
      pill.textContent = "demo mode — no API key set";
      pill.classList.add("demo");
      notice.textContent = "Running in demo mode. Add a GEMINI_API_KEY in backend/.env for live AI responses.";
    } else {
      pill.textContent = "connected — Gemini live";
      pill.classList.add("live");
    }
  } catch (err) {
    pill.textContent = "backend unreachable";
  }
}
checkHealth();

/* ---------------- helpers ---------------- */
async function postJSON(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return res.json();
}

function showLoading(container, msg) {
  container.innerHTML = `<div class="loading">${msg}</div>`;
}

function showError(container, err) {
  container.innerHTML = `<div class="card error-card"><h3>Something went wrong</h3><p>${err.message}</p></div>`;
}

/* ---------------- ASK ---------------- */
document.getElementById("form-ask").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = e.target.querySelector("button");
  const container = document.getElementById("result-ask");
  const question = document.getElementById("ask-question").value.trim();
  const subject = document.getElementById("ask-subject").value.trim();

  btn.disabled = true;
  showLoading(container, "Summoning an answer…");
  try {
    const data = await postJSON("/api/ask", { question, subject: subject || null });
    container.innerHTML = `
      <div class="card">
        <h3>Answer</h3>
        <p>${data.answer}</p>
        <p style="color:var(--chalk-dim)">${data.context}</p>
        <div class="chip-row">${data.related_topics.map((t) => `<span class="chip">${t}</span>`).join("")}</div>
      </div>`;
    burstNear(btn);
  } catch (err) {
    showError(container, err);
  } finally {
    btn.disabled = false;
  }
});

/* ---------------- QUIZ ---------------- */
document.getElementById("form-quiz").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = e.target.querySelector("button");
  const container = document.getElementById("result-quiz");
  const topic = document.getElementById("quiz-topic").value.trim();
  const difficulty = document.getElementById("quiz-difficulty").value;
  const num_questions = parseInt(document.getElementById("quiz-count").value, 10) || 5;

  btn.disabled = true;
  showLoading(container, "Drawing up questions…");
  try {
    const data = await postJSON("/api/quiz", { topic, difficulty, num_questions });
    container.innerHTML = `<div class="card"><h3>${data.topic} — ${data.difficulty} quiz</h3>
      <div id="quizQuestions"></div></div>`;
    const qWrap = document.getElementById("quizQuestions");
    data.questions.forEach((q, qi) => {
      const qEl = document.createElement("div");
      qEl.className = "quiz-q";
      qEl.innerHTML = `
        <div class="quiz-q-title">${qi + 1}. ${q.question}</div>
        <div class="quiz-options"></div>
        <div class="quiz-explain">${q.explanation}</div>`;
      const optWrap = qEl.querySelector(".quiz-options");
      q.options.forEach((opt) => {
        const optEl = document.createElement("div");
        optEl.className = "quiz-option";
        optEl.textContent = opt;
        optEl.addEventListener("click", () => {
          if (optWrap.dataset.answered) return;
          optWrap.dataset.answered = "1";
          const isCorrect = opt.trim() === q.correct_answer.trim();
          optEl.classList.add(isCorrect ? "correct" : "incorrect");
          if (!isCorrect) {
            [...optWrap.children].forEach((c) => {
              if (c.textContent.trim() === q.correct_answer.trim()) c.classList.add("correct");
            });
          }
          qEl.querySelector(".quiz-explain").classList.add("show");
        });
        optWrap.appendChild(optEl);
      });
      qWrap.appendChild(qEl);
    });
    burstNear(btn);
  } catch (err) {
    showError(container, err);
  } finally {
    btn.disabled = false;
  }
});

/* ---------------- SUMMARIZE ---------------- */
document.getElementById("form-summarize").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = e.target.querySelector("button");
  const container = document.getElementById("result-summarize");
  const text = document.getElementById("sum-text").value.trim();
  const length = document.getElementById("sum-length").value;

  btn.disabled = true;
  showLoading(container, "Condensing the chapter…");
  try {
    const data = await postJSON("/api/summarize", { text, length });
    container.innerHTML = `
      <div class="card">
        <h3>Summary</h3>
        <p>${data.summary}</p>
        <ul class="stage-list">${data.key_points.map((k) => `<li>${k}</li>`).join("")}</ul>
        <p style="color:var(--chalk-dim); font-size:0.8rem">${data.word_count_original} words → ${data.word_count_summary} words</p>
      </div>`;
    burstNear(btn);
  } catch (err) {
    showError(container, err);
  } finally {
    btn.disabled = false;
  }
});

/* ---------------- LEARNING PATH ---------------- */
document.getElementById("form-path").addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = e.target.querySelector("button");
  const container = document.getElementById("result-path");
  const topic = document.getElementById("path-topic").value.trim();
  const current_level = document.getElementById("path-level").value;
  const goal = document.getElementById("path-goal").value.trim();

  btn.disabled = true;
  showLoading(container, "Mapping the road ahead…");
  try {
    const data = await postJSON("/api/learning-path", { topic, current_level, goal: goal || null });
    container.innerHTML = `<div class="card"><h3>${data.topic} — learning path</h3>
      <div class="stage-track" id="stageTrack"></div></div>`;
    const track = document.getElementById("stageTrack");
    data.stages.forEach((s) => {
      const el = document.createElement("div");
      el.className = "stage";
      el.innerHTML = `
        <div>
          <div class="stage-tag">${s.stage}</div>
          <div class="stage-duration">${s.duration_estimate}</div>
        </div>
        <div>
          <div class="stage-title">${s.title}</div>
          <ul class="stage-list">${s.topics.map((t) => `<li>${t}</li>`).join("")}</ul>
          <div class="stage-resources">${s.resources.map((r) => `<span class="chip">${r}</span>`).join("")}</div>
        </div>`;
      track.appendChild(el);
    });
    burstNear(btn);
  } catch (err) {
    showError(container, err);
  } finally {
    btn.disabled = false;
  }
});
