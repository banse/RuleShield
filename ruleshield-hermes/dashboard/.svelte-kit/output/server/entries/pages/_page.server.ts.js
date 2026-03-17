const API_BASE = "http://localhost:8337";
async function fetchJSON(path, fallback) {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      signal: AbortSignal.timeout(2e3)
    });
    if (!res.ok) return fallback;
    return await res.json();
  } catch {
    return fallback;
  }
}
const load = async () => {
  const [stats, requestsData, rulesData, shadow, health] = await Promise.all([
    fetchJSON("/api/stats", {}),
    fetchJSON("/api/requests", { requests: [] }),
    fetchJSON(
      "/api/rules",
      { rules: [], total: 0, active: 0 }
    ),
    fetchJSON("/api/shadow", null),
    fetchJSON("/health", { status: "disconnected" })
  ]);
  return {
    stats: {
      total_requests: stats.total_requests ?? 0,
      cache_hits: stats.cache_hits ?? 0,
      rule_hits: stats.rule_hits ?? 0,
      routed: stats.routed_calls ?? 0,
      passthrough: stats.passthrough_calls ?? 0,
      llm_calls: stats.llm_calls ?? 0,
      cost_without: stats.cost_without ?? 0,
      cost_with: stats.cost_with ?? 0,
      saved: stats.savings_usd ?? 0,
      savings_pct: stats.savings_pct ?? 0,
      uptime_seconds: stats.uptime_seconds ?? 0
    },
    requests: (requestsData.requests ?? []).map((r) => ({
      id: r.id ?? 0,
      prompt: String(r.prompt ?? ""),
      type: String(r.resolution_type ?? "llm"),
      cost: Number(r.cost ?? 0),
      latency_ms: Number(r.latency_ms ?? 0),
      timestamp: String(r.created_at ?? ""),
      model: String(r.model ?? "")
    })),
    rules: (rulesData.rules ?? []).map((r) => ({
      id: String(r.id ?? ""),
      name: String(r.name ?? r.id ?? ""),
      hits: Number(r.hits ?? r.hit_count ?? 0),
      confidence: Number(r.confidence ?? 0),
      confidence_level: String(r.confidence_level ?? ""),
      enabled: Boolean(r.enabled ?? true),
      pattern_count: Number(r.pattern_count ?? 0)
    })),
    rulesTotal: rulesData.total ?? 0,
    rulesActive: rulesData.active ?? 0,
    shadow: shadow ? {
      enabled: Boolean(shadow.enabled ?? false),
      avg_similarity: Number(shadow.avg_similarity ?? 0),
      rules_ready: Number(shadow.rules_ready ?? 0),
      total_comparisons: Number(shadow.total_comparisons ?? 0),
      by_rule: Array.isArray(shadow.by_rule) ? shadow.by_rule : []
    } : null,
    connected: health.status !== "disconnected",
    loadedAt: Date.now()
  };
};
export {
  load
};
