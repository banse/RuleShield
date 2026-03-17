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
  const rulesData = await fetchJSON("/api/rules", { rules: [], total: 0, active: 0 });
  return {
    rules: (rulesData.rules ?? []).map((r) => ({
      id: String(r.id ?? ""),
      name: String(r.name ?? r.id ?? ""),
      hits: Number(r.hits ?? 0),
      confidence: Number(r.confidence ?? 0),
      confidence_level: String(r.confidence_level ?? "POSSIBLE"),
      enabled: Boolean(r.enabled ?? true),
      pattern_count: Number(r.pattern_count ?? 0)
    })),
    total: rulesData.total ?? 0,
    active: rulesData.active ?? 0,
    loadedAt: Date.now()
  };
};
export {
  load
};
