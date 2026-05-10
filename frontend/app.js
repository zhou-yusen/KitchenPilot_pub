const $ = (selector) => document.querySelector(selector);

const elements = {
  baseUrl: $("#baseUrl"),
  userId: $("#userId"),
  chatQuery: $("#chatQuery"),
  chatIngredients: $("#chatIngredients"),
  recommendIngredients: $("#recommendIngredients"),
  sendChat: $("#sendChat"),
  sendRecommend: $("#sendRecommend"),
  sendDaily: $("#sendDaily"),
  chatStatus: $("#chatStatus"),
  recommendStatus: $("#recommendStatus"),
  answerBox: $("#answerBox"),
  recommendations: $("#recommendations"),
  sources: $("#sources"),
  trace: $("#trace"),
};

function apiBase() {
  return elements.baseUrl.value.trim().replace(/\/+$/, "");
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

function setBusy(buttons, busy) {
  buttons.forEach((button) => {
    button.disabled = busy;
  });
}

function setStatus(element, message, isError = false) {
  element.textContent = message;
  element.classList.toggle("error", isError);
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

function renderChatResult(data) {
  const quality = data.quality_check;
  const qualityText = quality
    ? quality.passed
      ? "quality: passed"
      : "quality: needs review"
    : "quality: n/a";
  const warnings = quality?.safety_warnings?.length
    ? tag(`safety: ${quality.safety_warnings.length}`, true)
    : "";

  elements.answerBox.classList.remove("empty");
  elements.answerBox.innerHTML = `
    <div class="meta-row">
      ${tag(`intent: ${data.intent || "unknown"}`)}
      ${tag(`confidence: ${(data.intent_confidence ?? 0).toFixed(2)}`)}
      ${tag(qualityText, quality && !quality.passed)}
      ${warnings}
    </div>
    <div>${escapeText(data.answer || data.clarification_question || "无回答")}</div>
  `;

  renderSources(data.sources || []);
  renderTrace(data.execution_trace || []);

  if (data.recommendations?.length) {
    renderRecommendations(data.recommendations);
  }
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

function renderTrace(trace) {
  if (!trace.length) {
    elements.trace.className = "trace empty";
    elements.trace.innerHTML = "<li>没有返回执行轨迹。</li>";
    return;
  }

  elements.trace.className = "trace";
  elements.trace.innerHTML = trace.map((item) => `<li>${escapeText(item)}</li>`).join("");
}

function renderRecommendations(recommendations) {
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
      return `
        <article class="item">
          <h3>${escapeText(item.recipe_name)} · ${Number(item.score ?? 0).toFixed(1)} 分</h3>
          <p>${tag(item.difficulty)} ${tag(`${item.time_minutes} 分钟`)} ${
            item.beginner_friendly ? tag("新手友好") : tag("需谨慎", true)
          }</p>
          <p>匹配：${escapeText(matched)}</p>
          <p>缺少：${escapeText(missing)}</p>
          <p>理由：${escapeText(reasons)}</p>
        </article>
      `;
    })
    .join("");
}

async function sendChat() {
  const query = elements.chatQuery.value.trim();
  if (!query) {
    setStatus(elements.chatStatus, "请输入问题。", true);
    return;
  }

  setBusy([elements.sendChat], true);
  setStatus(elements.chatStatus, "请求中...");
  try {
    const data = await requestJson("/api/chat", {
      method: "POST",
      body: JSON.stringify({
        user_id: elements.userId.value.trim() || "demo_user",
        query,
        ingredients: splitIngredients(elements.chatIngredients.value),
      }),
    });
    renderChatResult(data);
    setStatus(elements.chatStatus, "完成");
  } catch (error) {
    setStatus(elements.chatStatus, error.message, true);
  } finally {
    setBusy([elements.sendChat], false);
  }
}

async function sendRecommendations() {
  setBusy([elements.sendRecommend, elements.sendDaily], true);
  setStatus(elements.recommendStatus, "请求中...");
  try {
    const data = await requestJson("/api/recommend/ingredients", {
      method: "POST",
      body: JSON.stringify({
        user_id: elements.userId.value.trim() || "demo_user",
        ingredients: splitIngredients(elements.recommendIngredients.value),
      }),
    });
    renderRecommendations(data.recommendations || []);
    setStatus(elements.recommendStatus, "完成");
  } catch (error) {
    setStatus(elements.recommendStatus, error.message, true);
  } finally {
    setBusy([elements.sendRecommend, elements.sendDaily], false);
  }
}

async function sendDailyRecommendations() {
  const userId = encodeURIComponent(elements.userId.value.trim() || "demo_user");
  setBusy([elements.sendRecommend, elements.sendDaily], true);
  setStatus(elements.recommendStatus, "请求中...");
  try {
    const data = await requestJson(`/api/recommend/daily/${userId}`);
    renderRecommendations(data.recommendations || []);
    setStatus(elements.recommendStatus, "完成");
  } catch (error) {
    setStatus(elements.recommendStatus, error.message, true);
  } finally {
    setBusy([elements.sendRecommend, elements.sendDaily], false);
  }
}

document.querySelectorAll("[data-query]").forEach((button) => {
  button.addEventListener("click", () => {
    elements.chatQuery.value = button.dataset.query || "";
    elements.chatQuery.focus();
  });
});

elements.sendChat.addEventListener("click", sendChat);
elements.sendRecommend.addEventListener("click", sendRecommendations);
elements.sendDaily.addEventListener("click", sendDailyRecommendations);
