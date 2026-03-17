// @ts-nocheck
import type { PageServerLoad } from './$types';

const API_BASE = 'http://localhost:8337';

async function fetchJSON<T>(path: string, fallback: T): Promise<T> {
	try {
		const res = await fetch(`${API_BASE}${path}`, {
			signal: AbortSignal.timeout(3000)
		});
		if (!res.ok) return fallback;
		return (await res.json()) as T;
	} catch {
		return fallback;
	}
}

export const load = async () => {
	const [stats, requestsData] = await Promise.all([
		fetchJSON<Record<string, number>>('/api/stats', {}),
		fetchJSON<{ requests: Array<Record<string, unknown>> }>('/api/requests?limit=100', {
			requests: []
		})
	]);

	// Compute breakdown from requests
	const requests = requestsData.requests ?? [];
	const breakdown: Record<string, number> = {
		cache: 0,
		rule: 0,
		routed: 0,
		template: 0,
		passthrough: 0,
		llm: 0
	};

	let totalCost = 0;

	for (const r of requests) {
		const rtype = String(r.resolution_type ?? 'llm').toLowerCase();
		if (rtype in breakdown) {
			breakdown[rtype]++;
		}
		totalCost += Number(r.cost_usd ?? r.cost ?? 0);
	}

	// Top rules: group rule-type requests by prompt
	const ruleHits = new Map<string, { prompt: string; hits: number }>();
	for (const r of requests) {
		const rtype = String(r.resolution_type ?? 'llm').toLowerCase();
		if (rtype === 'rule') {
			const prompt = String(r.prompt_text ?? r.prompt ?? '').slice(0, 60);
			const hash = String(r.prompt_hash ?? prompt);
			const existing = ruleHits.get(hash);
			if (existing) {
				existing.hits++;
			} else {
				ruleHits.set(hash, { prompt, hits: 1 });
			}
		}
	}
	const topRules = [...ruleHits.values()]
		.sort((a, b) => b.hits - a.hits)
		.slice(0, 5);

	// Top 3 most expensive prompts
	const expensivePrompts = requests
		.filter((r) => Number(r.cost_usd ?? r.cost ?? 0) > 0)
		.sort((a, b) => Number(b.cost_usd ?? b.cost ?? 0) - Number(a.cost_usd ?? a.cost ?? 0))
		.slice(0, 3)
		.map((r) => ({
			prompt: String(r.prompt_text ?? r.prompt ?? '').slice(0, 60),
			cost: Number(r.cost_usd ?? r.cost ?? 0),
			model: String(r.model ?? 'unknown')
		}));

	const costWithout = stats.cost_without ?? totalCost;
	const costWith = stats.cost_with ?? 0;
	const savedUsd = stats.savings_usd ?? costWithout - costWith;
	const savedPct = stats.savings_pct ?? (costWithout > 0 ? (savedUsd / costWithout) * 100 : 0);

	return {
		totalRequests: stats.total_requests ?? requests.length,
		breakdown,
		costWithout,
		costWith,
		savedUsd,
		savedPct,
		topRules,
		expensivePrompts,
		connected: costWithout > 0 || requests.length > 0,
		loadedAt: Date.now()
	};
};
;null as any as PageServerLoad;