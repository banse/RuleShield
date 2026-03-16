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
    const errorCell =
      errorText && href
        ? `<a class="error-link" href="${href}" target="_blank" rel="noopener noreferrer">${errorText}</a>`
        : (errorText || "-");

    tr.innerHTML = `
      <td>${test.name || test.id || "-"}</td>
      <td><span class="path">${test.script_path || "-"}</span></td>
      <td>${test.group || "-"}</td>
      <td>${hasRun ? formatDate(lastRun.ended_at || lastRun.started_at) : "-"}</td>
      <td><span class="status ${statusClass(status, hasRun)}">${statusLabel(status, hasRun)}</span></td>
      <td class="error">${errorCell}</td>
    `;
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
    const statusBadge = `<span class="status ${statusClass(status, true)}">${statusLabel(status, true)}</span>`;
    const errorLine = status === "failed" && item.error ? `\nerror: ${item.error}` : "";
    const excerpt = String(item.log_excerpt || "").trim() || "[no log excerpt]";

    const logHrefValue = logHref(item.log_path || "");
    const logPathHtml = logHrefValue
      ? `<a class="log-link" href="${logHrefValue}" target="_blank" rel="noopener noreferrer">${item.log_path || "-"}</a>`
      : `${item.log_path || "-"}`;

    card.innerHTML = `
      <div class="log-head">
        <div class="log-title">${item.name || item.case_id || "-"}</div>
        <div>${statusBadge}</div>
      </div>
      <div class="log-meta">run: ${item.run_id || "-"} | suite: ${item.suite_id || "-"} | at: ${stamp}</div>
      <div class="log-path">${logPathHtml}</div>
      <pre class="log-body">${excerpt}${errorLine}</pre>
    `;
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
  rows.innerHTML = `<tr><td colspan="6" class="error">Failed to load summary: ${String(err)}</td></tr>`;
});
