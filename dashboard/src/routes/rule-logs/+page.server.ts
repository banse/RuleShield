import type { PageServerLoad } from './$types';

const API_BASE = 'http://127.0.0.1:8337';

async function fetchJSON<T>(path: string, fallback: T): Promise<T> {
	try {
		const res = await fetch(`${API_BASE}${path}`, { signal: AbortSignal.timeout(2000) });
		if (!res.ok) return fallback;
		return (await res.json()) as T;
	} catch {
		return fallback;
	}
}

export const load: PageServerLoad = async () => {
	const [eventsData, feedbackData, rulesData, shadowData, health] = await Promise.all([
		fetchJSON<{ events: Array<Record<string, unknown>>; limit: number }>('/api/rule-events?limit=120', {
			events: [],
			limit: 120
		}),
		fetchJSON<{ entries: Array<Record<string, unknown>>; stats: Array<Record<string, unknown>>; limit: number }>(
			'/api/feedback?limit=80',
			{ entries: [], stats: [], limit: 80 }
		),
		fetchJSON<{ rules: Array<Record<string, unknown>> }>('/api/rules', { rules: [] }),
		fetchJSON<Record<string, unknown> | null>('/api/shadow', null),
		fetchJSON<{ status: string }>('/health', { status: 'disconnected' })
	]);

	return {
		connected: health.status !== 'disconnected',
		loadedAt: Date.now(),
		events: (eventsData.events ?? []).map((e) => ({
			id: Number(e.id ?? 0),
			rule_id: String(e.rule_id ?? ''),
			event_type: String(e.event_type ?? ''),
			direction: String(e.direction ?? ''),
			old_confidence: Number(e.old_confidence ?? 0),
			new_confidence: Number(e.new_confidence ?? 0),
			delta: Number(e.delta ?? 0),
			created_at: String(e.created_at ?? '')
		})),
		feedback: (feedbackData.entries ?? []).map((f) => ({
			id: Number(f.id ?? 0),
			rule_id: String(f.rule_id ?? ''),
			feedback: String(f.feedback ?? ''),
			prompt_text: String(f.prompt_text ?? ''),
			created_at: String(f.created_at ?? '')
		})),
		ruleStats: (feedbackData.stats ?? []).map((s) => ({
			rule_id: String(s.rule_id ?? ''),
			accept_count: Number(s.accept_count ?? 0),
			reject_count: Number(s.reject_count ?? 0),
			acceptance_rate: Number(s.acceptance_rate ?? 0),
			current_confidence: Number(s.current_confidence ?? 0)
		})),
		rules: (rulesData.rules ?? []).map((r) => ({
			id: String(r.id ?? ''),
			enabled: Boolean(r.enabled ?? true),
			confidence: Number(r.confidence ?? 0),
			status: String(r.status ?? 'live'),
			deployment: String(r.deployment ?? 'production')
		})),
		shadow: shadowData
			? {
					enabled: Boolean(shadowData.enabled ?? false),
					total_comparisons: Number(shadowData.total_comparisons ?? 0),
					avg_similarity_pct: Number(
						shadowData.avg_similarity_pct ?? Number(shadowData.avg_similarity ?? 0) * 100
					)
				}
			: null
	};
};
