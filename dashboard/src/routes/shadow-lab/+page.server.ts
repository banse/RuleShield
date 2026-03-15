import type { PageServerLoad } from './$types';

const API_BASE = 'http://127.0.0.1:8337';
const RECENT_COMPARISONS = 25;
const REQUEST_LIMIT = 30;

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
	const [shadow, rulesData, requestsData, health] = await Promise.all([
		fetchJSON<Record<string, unknown> | null>(
			`/api/shadow?recent=${RECENT_COMPARISONS}`,
			null
		),
		fetchJSON<{ rules: Array<Record<string, unknown>> }>('/api/rules', { rules: [] }),
		fetchJSON<{ requests: Array<Record<string, unknown>> }>(
			`/api/requests?limit=${REQUEST_LIMIT}`,
			{ requests: [] }
		),
		fetchJSON<{ status: string }>('/health', { status: 'disconnected' })
	]);

	const candidateRules = (rulesData.rules ?? [])
		.filter((rule) => String(rule.deployment ?? 'production') === 'candidate')
		.map((rule) => ({
			id: String(rule.id ?? ''),
			name: String(rule.name ?? rule.id ?? ''),
			shadow_hits: Number(rule.shadow_hits ?? 0),
			confidence: Number(rule.confidence ?? 0),
			status: String(rule.status ?? 'candidate')
		}))
		.sort((a, b) => b.shadow_hits - a.shadow_hits);

	const recentShadowRequests = (requestsData.requests ?? [])
		.map((request) => ({
			id: Number(request.id ?? 0),
			prompt: String(request.prompt ?? ''),
			model: String(request.model ?? ''),
			type: String(request.resolution_type ?? 'unknown'),
			latency_ms: Number(request.latency_ms ?? 0),
			timestamp: String(request.created_at ?? '')
		}))
		.filter((request) => request.prompt.toLowerCase().includes('shadow'))
		.slice(0, 12);

	return {
		connected: health.status !== 'disconnected',
		loadedAt: Date.now(),
		recentWindow: RECENT_COMPARISONS,
		shadow: shadow
			? {
					enabled: Boolean(shadow.enabled ?? false),
					total_comparisons: Number(shadow.total_comparisons ?? 0),
					avg_similarity_pct: Number(
						shadow.avg_similarity_pct ?? Number(shadow.avg_similarity ?? 0) * 100
					),
					rules_ready: Number(shadow.rules_ready ?? 0),
					entries: Array.isArray(shadow.entries) ? shadow.entries : [],
					tune_examples: Array.isArray(shadow.tune_examples) ? shadow.tune_examples : []
				}
			: null,
		candidateRules,
		recentShadowRequests
	};
};
