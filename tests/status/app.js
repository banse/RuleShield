function formatDate(value) {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

function statusClass(status, hasRun) {
  if (!hasRun) return "status-never";
  if (status === "success") return "status-success";
  if (status === "failed") return "status-failed";
  return "status-never";
}

function statusLabel(status, hasRun) {
  if (!hasRun) return "never";
  if (status === "success") return "success";
  if (status === "failed") return "failed";
  return "unknown";
}

function logHref(logPath) {
  const raw = String(logPath || "").trim();
  if (!raw) return "";
  const clean = raw.replace(/^\.?\//, "");
  return `/${clean}`;
}

async function loadSummary() {
  const resp = await fetch("./data/summary.json", { cache: "no-store" });
  if (!resp.ok) {
    return { generated_at: "", tests: [] };
  }
  return await resp.json();
}

function render(summary) {
  const generatedAt = document.getElementById("generatedAt");
  const gatewayStatus = document.getElementById("gatewayStatus");
  const gatewayPort = document.getElementById("gatewayPort");
  const rows = document.getElementById("rows");
  generatedAt.textContent = `Summary generated: ${formatDate(summary.generated_at)}`;
  const gateway = summary.gateway || {};
  gatewayStatus.textContent = `Gateway status: ${gateway.status || "-"}`;
  gatewayPort.textContent = `Gateway port: ${gateway.configured_port || "-"}`;

  const tests = Array.isArray(summary.tests) ? summary.tests : [];
  rows.innerHTML = "";
  for (const test of tests) {
    const tr = document.createElement("tr");
    const lastRun = test.last_run || null;
    const hasRun = Boolean(lastRun);
    const status = hasRun ? String(lastRun.status || "") : "";
    const errorText = hasRun && status === "failed" ? String(lastRun.error || "") : "";
    const logPath = hasRun ? String(lastRun.log_path || "") : "";
    const href = logHref(logPath);
    const tdName = document.createElement("td");
    tdName.textContent = test.name || test.id || "-";
    tr.appendChild(tdName);

    const tdPath = document.createElement("td");
    const spanPath = document.createElement("span");
    spanPath.className = "path";
    spanPath.textContent = test.script_path || "-";
    tdPath.appendChild(spanPath);
    tr.appendChild(tdPath);

    const tdGroup = document.createElement("td");
    tdGroup.textContent = test.group || "-";
    tr.appendChild(tdGroup);

    const tdDate = document.createElement("td");
    tdDate.textContent = hasRun ? formatDate(lastRun.ended_at || lastRun.started_at) : "-";
    tr.appendChild(tdDate);

    const tdStatus = document.createElement("td");
    const spanStatus = document.createElement("span");
    spanStatus.className = "status " + statusClass(status, hasRun);
    spanStatus.textContent = statusLabel(status, hasRun);
    tdStatus.appendChild(spanStatus);
    tr.appendChild(tdStatus);

    const tdError = document.createElement("td");
    tdError.className = "error";
    if (errorText && href) {
      const a = document.createElement("a");
      a.className = "error-link";
      a.href = href;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.textContent = errorText;
      tdError.appendChild(a);
    } else {
      tdError.textContent = errorText || "-";
    }
    tr.appendChild(tdError);
    rows.appendChild(tr);
  }

  renderStoryLogs(summary);
}

function renderStoryLogs(summary) {
  const feed = document.getElementById("logFeed");
  const logs = Array.isArray(summary.story_logs) ? summary.story_logs : [];
  feed.innerHTML = "";
  if (!logs.length) {
    feed.innerHTML = `<div class="log-card"><div class="log-meta">No story logs yet. Run a suite to populate this feed.</div></div>`;
    return;
  }

  for (const item of logs) {
    const card = document.createElement("article");
    card.className = "log-card";
    const stamp = formatDate(item.ended_at || item.started_at);
    const status = String(item.status || "unknown");
    const errorLine = status === "failed" && item.error ? "\nerror: " + item.error : "";
    const excerpt = String(item.log_excerpt || "").trim() || "[no log excerpt]";

    const logHrefValue = logHref(item.log_path || "");

    const logHead = document.createElement("div");
    logHead.className = "log-head";
    const logTitle = document.createElement("div");
    logTitle.className = "log-title";
    logTitle.textContent = item.name || item.case_id || "-";
    logHead.appendChild(logTitle);
    const badgeWrapper = document.createElement("div");
    const badgeSpan = document.createElement("span");
    badgeSpan.className = "status " + statusClass(status, true);
    badgeSpan.textContent = statusLabel(status, true);
    badgeWrapper.appendChild(badgeSpan);
    logHead.appendChild(badgeWrapper);
    card.appendChild(logHead);

    const logMeta = document.createElement("div");
    logMeta.className = "log-meta";
    logMeta.textContent = "run: " + (item.run_id || "-") + " | suite: " + (item.suite_id || "-") + " | at: " + stamp;
    card.appendChild(logMeta);

    const logPathDiv = document.createElement("div");
    logPathDiv.className = "log-path";
    if (logHrefValue) {
      const logLink = document.createElement("a");
      logLink.className = "log-link";
      logLink.href = logHrefValue;
      logLink.target = "_blank";
      logLink.rel = "noopener noreferrer";
      logLink.textContent = item.log_path || "-";
      logPathDiv.appendChild(logLink);
    } else {
      logPathDiv.textContent = item.log_path || "-";
    }
    card.appendChild(logPathDiv);

    const logBody = document.createElement("pre");
    logBody.className = "log-body";
    logBody.textContent = excerpt + errorLine;
    card.appendChild(logBody);
    feed.appendChild(card);
  }
}

function wireTabs() {
  const tabTests = document.getElementById("tabTests");
  const tabLogs = document.getElementById("tabLogs");
  const panelTests = document.getElementById("panelTests");
  const panelLogs = document.getElementById("panelLogs");

  const activate = (which) => {
    const testsActive = which === "tests";
    tabTests.classList.toggle("active", testsActive);
    tabLogs.classList.toggle("active", !testsActive);
    panelTests.classList.toggle("active", testsActive);
    panelLogs.classList.toggle("active", !testsActive);
  };

  tabTests.addEventListener("click", () => activate("tests"));
  tabLogs.addEventListener("click", () => activate("logs"));
}

async function main() {
  wireTabs();
  const summary = await loadSummary();
  render(summary);
}

main().catch((err) => {
  const rows = document.getElementById("rows");
  rows.textContent = "";
  const tr = document.createElement("tr");
  const td = document.createElement("td");
  td.setAttribute("colspan", "6");
  td.className = "error";
  td.textContent = "Failed to load summary: " + String(err);
  tr.appendChild(td);
  rows.appendChild(tr);
});
