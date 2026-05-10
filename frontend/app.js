const STORAGE_KEY = "kitchenpilot.sessions.v1";

const $ = (selector) => document.querySelector(selector);

const elements = {
  baseUrl: $("#baseUrl"),
  userId: $("#userId"),
  activeSessionId: $("#activeSessionId"),
  newSession: $("#newSession"),
  sessionList: $("#sessionList"),
  chatQuery: $("#chatQuery"),
  chatIngredients: $("#chatIngredients"),
  sendChat: $("#sendChat"),
  chatStatus: $("#chatStatus"),
  messages: $("#messages"),
  routerInfo: $("#routerInfo"),
  recommendations: $("#recommendations"),
  trace: $("#trace"),
  sources: $("#sources"),
  quality: $("#quality"),
  rawJson: $("#rawJson"),
};

let sessions = loadSessions();
let activeSessionId = sessions[0]?.id || null;
if (!activeSessionId) {
  activeSessionId = createSession().id;
}

function apiBase() {
  return elements.baseUrl.value.trim().replace(/\/+$/, "");
}

function loadSessions() {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveSessions() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
}

function makeSessionId() {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID();
  }
  return `session_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function createSession() {
  const now = new Date().toISOString();
  const session = {
    id: makeSessionId(),
    title: "新对话",
    messages: [],
    lastDebug: null,
    createdAt: now,
    updatedAt: now,
  };
  sessions = [session, ...sessions];
  activeSessionId = session.id;
  saveSessions();
  return session;
}

function currentSession() {
  let session = sessions.find((item) => item.id === activeSessionId);
  if (!session) {
    session = createSession();
  }
  return session;
}

function updateSession(patch) {
  sessions = sessions.map((session) =>
    session.id === activeSessionId ? { ...session, ...patch } : session
  );
  saveSessions();
}

function splitIngredients(value) {
  return value
    .split(/[,\s，、]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

async function requestJson(path, options = {}) {
  const response = await fetch(`${apiBase()}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const detail = payload?.detail || response.statusText || "请求失败";
    throw new Error(`${response.status} ${detail}`);
  }
  return payload;
}

function setStatus(message, isError = false) {
  elements.chatStatus.textContent = message;
  elements.chatStatus.classList.toggle("error", isError);
}

function escapeText(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function tag(label, isWarning = false) {
  return `<span class="tag${isWarning ? " warn" : ""}">${escapeText(label)}</span>`;
}

function appendMessage(role, content, persist = true) {
  elements.messages.classList.remove("empty");
  const article = document.createElement("article");
  article.className = `message ${role}`;
  article.innerHTML = `
    <div class="message-role">${role === "user" ? "User" : "KitchenPilot"}</div>
    <div class="message-body">${escapeText(content || "无内容")}</div>
  `;
  elements.messages.append(article);
  elements.messages.scrollTop = elements.messages.scrollHeight;

  if (persist) {
    const session = currentSession();
    updateSession({
      messages: [...session.messages, { role, content }],
      updatedAt: new Date().toISOString(),
      title: session.title === "新对话" && role === "user" ? titleFromQuery(content) : session.title,
    });
    renderSessions();
  }
}

function titleFromQuery(query) {
  const value = String(query || "").trim();
  return value.length > 16 ? `${value.slice(0, 16)}...` : value || "新对话";
}

function renderMessages() {
  elements.messages.innerHTML = "";
  const session = currentSession();
  if (!session.messages.length) {
    elements.messages.className = "messages empty";
    elements.messages.innerHTML =
      "<p>输入自然语言问题，KitchenPilot 会自动判断 intent、recommendation_type 和追问上下文。</p>";
    return;
  }
  elements.messages.className = "messages";
  session.messages.forEach((message) => appendMessage(message.role, message.content, false));
}

function renderSessions() {
  elements.activeSessionId.textContent = activeSessionId;
  elements.sessionList.innerHTML = sessions
    .map((session) => {
      const active = session.id === activeSessionId ? " active" : "";
      return `
        <div class="session-item${active}">
          <button type="button" class="session-open" data-session-id="${escapeText(
            session.id
          )}">
            <span>${escapeText(session.title)}</span>
            <small>${escapeText(session.id.slice(0, 8))}</small>
          </button>
          <button
            type="button"
            class="session-delete"
            data-delete-session-id="${escapeText(session.id)}"
            title="删除对话"
            aria-label="删除对话"
          >×</button>
        </div>
      `;
    })
    .join("");
}

async function deleteBackendSession(sessionId) {
  try {
    await requestJson(`/api/chat/sessions/${encodeURIComponent(sessionId)}`, {
      method: "DELETE",
    });
  } catch (error) {
    console.warn("Failed to delete backend session memory", error);
  }
}

function deleteSession(sessionId) {
  const wasActive = sessionId === activeSessionId;
  sessions = sessions.filter((session) => session.id !== sessionId);
  if (!sessions.length) {
    createSession();
  } else if (wasActive) {
    activeSessionId = sessions[0].id;
  }
  saveSessions();
  renderSessions();
  renderMessages();
  const debug = currentSession().lastDebug;
  if (debug) {
    renderDebug(debug);
  } else {
    resetDebug();
  }
  setStatus("已删除对话");
  deleteBackendSession(sessionId);
}

function switchSession(sessionId) {
  activeSessionId = sessionId;
  renderSessions();
  renderMessages();
  const debug = currentSession().lastDebug;
  if (debug) {
    renderDebug(debug);
  } else {
    resetDebug();
  }
}

function resetDebug() {
  elements.routerInfo.className = "list empty";
  elements.routerInfo.textContent = "等待请求。";
  elements.recommendations.className = "list empty";
  elements.recommendations.textContent = "recommendation intent 后显示。";
  elements.trace.className = "trace empty";
  elements.trace.innerHTML = "<li>等待执行。</li>";
  elements.sources.className = "list empty";
  elements.sources.textContent = "recipe_qa intent 后显示。";
  elements.quality.className = "list empty";
  elements.quality.textContent = "等待检查结果。";
  elements.rawJson.className = "raw-json empty";
  elements.rawJson.textContent = "{}";
}

function renderDebug(data) {
  renderRouter(data);
  renderRecommendations(data.recommendations || [], data.recommendation_type);
  renderTrace(data.execution_trace || []);
  renderSources(data.sources || []);
  renderQuality(data.quality_check);
  elements.rawJson.className = "raw-json";
  elements.rawJson.textContent = JSON.stringify(data, null, 2);
}

function renderRouter(data) {
  elements.routerInfo.className = "list";
  elements.routerInfo.innerHTML = `
    <div class="meta-row">
      ${tag(`session_id: ${data.session_id || activeSessionId}`)}
      ${tag(`intent: ${data.intent || "fallback"}`)}
      ${tag(`recommendation_type: ${data.recommendation_type || "n/a"}`)}
      ${tag(`active_recipe: ${data.active_recipe || "n/a"}`)}
      ${tag(`is_follow_up: ${data.is_follow_up ? "yes" : "no"}`)}
      ${tag(`confidence: ${(data.intent_confidence ?? 0).toFixed(2)}`)}
      ${tag(`source: ${data.intent_source || "unknown"}`)}
      ${tag(`clarification: ${data.needs_clarification ? "yes" : "no"}`)}
    </div>
    <p>rewritten_query：${escapeText(data.rewritten_query || "无")}</p>
  `;
}

function renderRecommendations(recommendations, recommendationType = "ingredients") {
  if (!recommendations.length) {
    elements.recommendations.className = "list empty";
    elements.recommendations.textContent = "没有推荐结果。";
    return;
  }

  elements.recommendations.className = "list";
  elements.recommendations.innerHTML = recommendations
    .map((item) => {
      const matched = item.matched_ingredients?.join("、") || "无";
      const missing = item.missing_ingredients?.join("、") || "无";
      const reasons = item.reasons?.join("；") || "无";
      const matchedLabel = recommendationType === "daily" ? "难度偏好" : "匹配";
      const matchedText = recommendationType === "daily" ? item.difficulty : matched;
      const missingLabel = recommendationType === "daily" ? "需准备" : "缺少";
      return `
        <article class="item">
          <h3>${escapeText(item.recipe_name)} · ${Number(item.score ?? 0).toFixed(1)} 分</h3>
          <p>${tag(item.difficulty)} ${tag(`${item.time_minutes} 分钟`)} ${
            item.beginner_friendly ? tag("新手友好") : tag("需谨慎", true)
          }</p>
          <p>${matchedLabel}：${escapeText(matchedText)}</p>
          <p>${missingLabel}：${escapeText(missing)}</p>
          <p>理由：${escapeText(reasons)}</p>
        </article>
      `;
    })
    .join("");
}

function renderTrace(trace) {
  if (!trace.length) {
    elements.trace.className = "trace empty";
    elements.trace.innerHTML = "<li>没有返回执行过程。</li>";
    return;
  }

  elements.trace.className = "trace";
  elements.trace.innerHTML = trace.map((item) => `<li>${escapeText(item)}</li>`).join("");
}

function renderSources(sources) {
  if (!sources.length) {
    elements.sources.className = "list empty";
    elements.sources.textContent = "没有返回 RAG 来源。";
    return;
  }

  elements.sources.className = "list";
  elements.sources.innerHTML = sources
    .map((source) => {
      const score = Number(source.score ?? 0).toFixed(4);
      return `
        <article class="item">
          <h3>${escapeText(source.recipe_name)} · ${escapeText(source.chunk_type)}</h3>
          <p>${tag(`score: ${score}`)} ${tag(source.metadata?.retrieval_source || "source")}</p>
          <p>${escapeText(source.content)}</p>
        </article>
      `;
    })
    .join("");
}

function renderQuality(quality) {
  if (!quality) {
    elements.quality.className = "list empty";
    elements.quality.textContent = "没有质量检查结果。";
    return;
  }

  const issues = quality.issues?.length ? quality.issues.join("；") : "无";
  const warnings = quality.safety_warnings?.length
    ? quality.safety_warnings.join("；")
    : "无";
  elements.quality.className = "list";
  elements.quality.innerHTML = `
    <div class="meta-row">
      ${tag(`passed: ${quality.passed ? "yes" : "no"}`, !quality.passed)}
      ${tag(`needs_repair: ${quality.needs_repair ? "yes" : "no"}`, quality.needs_repair)}
    </div>
    <p>issues：${escapeText(issues)}</p>
    <p>warnings：${escapeText(warnings)}</p>
  `;
}

async function sendChat() {
  const query = elements.chatQuery.value.trim();
  if (!query) {
    setStatus("请输入问题。", true);
    return;
  }

  elements.sendChat.disabled = true;
  setStatus("请求中...");
  appendMessage("user", query);
  try {
    const data = await requestJson("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        user_id: elements.userId.value.trim() || "demo_user",
        session_id: activeSessionId,
        query,
        ingredients: splitIngredients(elements.chatIngredients.value),
      }),
    });
    if (data.session_id && data.session_id !== activeSessionId) {
      activeSessionId = data.session_id;
    }
    appendMessage("agent", data.answer || data.clarification_question || "无回答");
    elements.chatQuery.value = "";
    updateSession({ lastDebug: data, updatedAt: new Date().toISOString() });
    renderDebug(data);
    renderSessions();
    setStatus("完成");
  } catch (error) {
    appendMessage("agent", `请求失败：${error.message}`);
    setStatus(error.message, true);
  } finally {
    elements.sendChat.disabled = false;
  }
}

document.querySelectorAll("[data-query]").forEach((button) => {
  button.addEventListener("click", () => {
    elements.chatQuery.value = button.dataset.query || "";
    elements.chatQuery.focus();
  });
});

elements.newSession.addEventListener("click", () => {
  createSession();
  renderSessions();
  renderMessages();
  resetDebug();
  setStatus("已新开对话");
});

elements.sessionList.addEventListener("click", (event) => {
  const deleteButton = event.target.closest("[data-delete-session-id]");
  if (deleteButton) {
    event.stopPropagation();
    deleteSession(deleteButton.dataset.deleteSessionId);
    return;
  }

  const button = event.target.closest("[data-session-id]");
  if (!button) {
    return;
  }
  switchSession(button.dataset.sessionId);
});

elements.sendChat.addEventListener("click", sendChat);
elements.chatQuery.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendChat();
  }
});

renderSessions();
renderMessages();
const initialDebug = currentSession().lastDebug;
if (initialDebug) {
  renderDebug(initialDebug);
} else {
  resetDebug();
}
