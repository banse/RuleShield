import type { PageServerLoad } from './$types';
import { getGatewayBaseServer } from '$lib/gateway';

const API_BASE = getGatewayBaseServer();

async function fetchJSON<T>(path: string, fallback: T): Promise<T> {
	try {
		const res = await fetch(`${API_BASE}${path}`, {
			signal: AbortSignal.timeout(2000)
		});
		if (!res.ok) return fallback;
		return (await res.json()) as T;
	} catch {
		return fallback;
	}
}

export const load: PageServerLoad = async () => {
	const [stats, requestsData, rulesData, shadow, health] = await Promise.all([
		fetchJSON<Record<string, number>>('/api/stats', {}),
		fetchJSON<{ requests: Array<Record<string, unknown>> }>('/api/requests', { requests: [] }),
		fetchJSON<{ rules: Array<Record<string, unknown>>; total: number; active: number }>(
			'/api/rules',
			{ rules: [], total: 0, active: 0 }
		),
		fetchJSON<Record<string, unknown> | null>('/api/shadow', null),
		fetchJSON<{ status: string }>('/health', { status: 'disconnected' })
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
			prompt: String(r.prompt ?? ''),
			type: String(r.resolution_type ?? 'llm'),
			cost: Number(r.cost ?? 0),
			latency_ms: Number(r.latency_ms ?? 0),
			timestamp: String(r.created_at ?? ''),
			model: String(r.model ?? '')
		})),
		rules: (rulesData.rules ?? []).map((r) => ({
			id: String(r.id ?? ''),
			name: String(r.name ?? r.id ?? ''),
			hits: Number(r.hits ?? r.hit_count ?? 0),
			shadow_hits: Number(r.shadow_hits ?? r.shadow_hit_count ?? 0),
			confidence: Number(r.confidence ?? 0),
			confidence_level: String(r.confidence_level ?? ''),
			enabled: Boolean(r.enabled ?? true),
			deployment: String(r.deployment ?? 'production'),
			status: String(r.status ?? (Boolean(r.enabled ?? true) ? 'live' : 'paused')),
			pattern_count: Number(r.pattern_count ?? 0)
		})),
		rulesTotal: rulesData.total ?? 0,
		rulesActive: rulesData.active ?? 0,
		shadow: shadow
			? {
					enabled: Boolean(shadow.enabled ?? false),
					avg_similarity: Number(shadow.avg_similarity ?? 0),
					avg_similarity_pct: Number(
						shadow.avg_similarity_pct ?? Number(shadow.avg_similarity ?? 0) * 100
					),
					rules_ready: Number(shadow.rules_ready ?? 0),
					total_comparisons: Number(shadow.total_comparisons ?? 0),
					by_rule: Array.isArray(shadow.by_rule) ? shadow.by_rule : [],
					entries: Array.isArray(shadow.entries) ? shadow.entries : [],
					tune_examples: Array.isArray(shadow.tune_examples) ? shadow.tune_examples : []
				}
			: null,
		connected: health.status !== 'disconnected',
		loadedAt: Date.now()
	};
};
