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
	const [profilesData, health] = await Promise.all([
		fetchJSON<{ profiles: Array<Record<string, unknown>>; total: number; drafts: number; active: number; ready: number }>(
			'/api/cron-profiles',
			{ profiles: [], total: 0, drafts: 0, active: 0, ready: 0 }
		),
		fetchJSON<{ status: string }>('/health', { status: 'disconnected' })
	]);

	const profiles = (profilesData.profiles ?? []).map((profile) => ({
		id: String(profile.id ?? ''),
		name: String(profile.name ?? profile.id ?? ''),
		status: String(profile.status ?? 'draft'),
		runtimeStatus: String(profile.runtime_status ?? 'draft'),
		classification: String(profile.classification ?? 'unknown'),
		occurrences: Number(profile.occurrences ?? 0),
		tokenReductionPct: Number(profile.token_reduction_pct ?? 0),
		optimizationConfidencePct: Number(profile.optimization_confidence ?? 0) * 100,
		shadowRuns: Number(profile.shadow_runs ?? 0),
		lastValidatedAt: String(profile.last_validated_at ?? ''),
		lastRunAt: String(profile.last_run_at ?? ''),
		path: String(profile.path ?? '')
	}));

	return {
		connected: health.status !== 'disconnected',
		summary: {
			total: Number(profilesData.total ?? profiles.length),
			drafts: Number(profilesData.drafts ?? 0),
			active: Number(profilesData.active ?? 0),
			ready: Number(profilesData.ready ?? 0)
		},
		profiles
	};
};
