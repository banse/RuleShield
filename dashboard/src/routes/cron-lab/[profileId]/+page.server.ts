import type { PageServerLoad } from './$types';

const API_BASE = 'http://127.0.0.1:8337';

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

export const load: PageServerLoad = async ({ params }) => {
	const profileId = params.profileId;
	const [detail, health] = await Promise.all([
		fetchJSON<Record<string, unknown>>(`/api/cron-profiles/${profileId}`, {}),
		fetchJSON<{ status: string }>('/health', { status: 'disconnected' })
	]);

	return {
		connected: health.status !== 'disconnected',
		profileId,
		detail
	};
};
