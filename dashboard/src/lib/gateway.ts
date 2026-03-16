export const GATEWAY_BASE_STORAGE_KEY = 'ruleshield_api_base';
export const DEFAULT_GATEWAY_BASE = 'http://127.0.0.1:8347';

function normalizeBase(input: string): string {
	return input.trim().replace(/\/+$/, '');
}

export function getGatewayBaseServer(): string {
	return normalizeBase(
		process.env.RULESHIELD_API_BASE ??
			process.env.VITE_RULESHIELD_API_BASE ??
			DEFAULT_GATEWAY_BASE
	);
}

export function getGatewayBaseClient(): string {
	const params = new URL(window.location.href).searchParams;
	const queryBase = params.get('api_base') ?? params.get('gateway') ?? params.get('gateway_url');
	const queryPort = params.get('port');
	const queryPortBase = queryPort ? `http://127.0.0.1:${queryPort}` : null;
	const rawStoredBase =
		typeof localStorage !== 'undefined' ? localStorage.getItem(GATEWAY_BASE_STORAGE_KEY) : null;
	const storedBase = rawStoredBase?.endsWith(':8337') ? null : rawStoredBase;
	const envBase = import.meta.env.VITE_RULESHIELD_API_BASE;
	const chosen = queryBase ?? queryPortBase ?? storedBase ?? envBase ?? DEFAULT_GATEWAY_BASE;
	const normalized = normalizeBase(chosen);
	if (typeof localStorage !== 'undefined') {
		localStorage.setItem(GATEWAY_BASE_STORAGE_KEY, normalized);
	}
	return normalized;
}

export function gatewayLabelFromBase(base: string): string {
	try {
		const parsed = new URL(base);
		return parsed.host;
	} catch {
		return base;
	}
}
