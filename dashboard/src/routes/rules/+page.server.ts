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
	const rulesData = await fetchJSON<{
		rules: Array<Record<string, unknown>>;
		total: number;
		active: number;
	}>('/api/rules', { rules: [], total: 0, active: 0 });

	return {
		rules: (rulesData.rules ?? []).map((r) => ({
			id: String(r.id ?? ''),
			name: String(r.name ?? r.id ?? ''),
			hits: Number(r.hits ?? 0),
			confidence: Number(r.confidence ?? 0),
			confidence_level: String(r.confidence_level ?? 'POSSIBLE'),
			enabled: Boolean(r.enabled ?? true),
			pattern_count: Number(r.pattern_count ?? 0)
		})),
		total: rulesData.total ?? 0,
		active: rulesData.active ?? 0,
		loadedAt: Date.now()
	};
};
