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
