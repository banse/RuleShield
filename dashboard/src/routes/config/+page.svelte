<script lang="ts">
	import { onMount } from 'svelte';

	const API_BASE = 'http://127.0.0.1:8337';

	type RuntimeConfig = {
		rules_enabled: boolean;
		shadow_mode: boolean;
		cache_enabled: boolean;
		router_enabled: boolean;
	};

	type RuleEntry = {
		id: string;
		name: string;
		enabled: boolean;
		status: string;
		deployment: string;
		confidence: number;
		hits: number;
	};

	let loading = $state(true);
	let busyGlobal = $state(false);
	let busyRuleId = $state('');
	let error = $state('');
	let runtimeConfig = $state<RuntimeConfig>({
		rules_enabled: true,
		shadow_mode: false,
		cache_enabled: true,
		router_enabled: true
	});
	let rules = $state<RuleEntry[]>([]);

	async function getJSON(path: string, fallback: any) {
		try {
			const res = await fetch(`${API_BASE}${path}`);
			if (!res.ok) return fallback;
			return await res.json();
		} catch {
			return fallback;
		}
	}

	async function postJSON(path: string, body: Record<string, unknown>) {
		const res = await fetch(`${API_BASE}${path}`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(body)
		});
		if (!res.ok) {
			const payload = await res.json().catch(() => ({}));
			throw new Error(payload.error || `Request failed (${res.status})`);
		}
		return await res.json();
	}

	async function loadData() {
		const [cfg, rulesData] = await Promise.all([
			getJSON('/api/runtime-config', runtimeConfig),
			getJSON('/api/rules', { rules: [] })
		]);
		runtimeConfig = {
			rules_enabled: Boolean(cfg.rules_enabled),
			shadow_mode: Boolean(cfg.shadow_mode),
			cache_enabled: Boolean(cfg.cache_enabled),
			router_enabled: Boolean(cfg.router_enabled)
		};
		rules = (rulesData.rules ?? []).sort((a: RuleEntry, b: RuleEntry) => a.name.localeCompare(b.name));
	}

	async function toggleGlobal(field: keyof RuntimeConfig) {
		error = '';
		busyGlobal = true;
		try {
			await postJSON('/api/runtime-config', { [field]: !runtimeConfig[field] });
			await loadData();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Update failed';
		} finally {
			busyGlobal = false;
		}
	}

	async function toggleRule(ruleId: string) {
		error = '';
		busyRuleId = ruleId;
		try {
			await postJSON(`/api/rules/${ruleId}/toggle`, {});
			await loadData();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Rule toggle failed';
		} finally {
			busyRuleId = '';
		}
	}

	onMount(() => {
		let alive = true;
		(async () => {
			await loadData();
			if (alive) loading = false;
		})();
		const interval = setInterval(loadData, 3000);
		return () => {
			alive = false;
			clearInterval(interval);
		};
	});

	function toggleLabel(active: boolean): string {
		return active ? 'ON' : 'OFF';
	}
</script>

<svelte:head>
	<title>RuleShield Config</title>
</svelte:head>

<div class="min-h-screen bg-[#0B0D12] px-6 py-8 text-text-primary">
	<div class="mx-auto max-w-6xl">
		<header class="mb-5 flex items-end justify-between border-b border-border pb-4">
			<div>
				<p class="text-xs uppercase tracking-[0.18em] text-text-muted">Minimal Configuration</p>
				<h1 class="text-2xl font-bold">RuleShield Config</h1>
				<p class="mt-1 text-sm text-text-secondary">
					Shadow mode, global runtime toggles und Rule-Schalter.
				</p>
			</div>
			<a
				href="/home"
				class="rounded-md border border-border bg-surface px-3 py-1.5 text-xs text-text-secondary hover:border-primary/40 hover:text-primary"
			>
				All Pages
			</a>
		</header>

		{#if error}
			<div class="mb-4 rounded-lg border border-error/30 bg-error/10 px-3 py-2 text-sm text-error">{error}</div>
		{/if}

		<section class="mb-5 rounded-xl border border-border bg-surface p-4">
			<h2 class="mb-3 text-sm font-semibold uppercase tracking-wider text-text-muted">Global Toggles</h2>
			<div class="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
				<button
					class="rounded-md border border-border bg-surface-elevated/50 px-3 py-3 text-left disabled:opacity-50"
					disabled={busyGlobal}
					onclick={() => toggleGlobal('rules_enabled')}
				>
					<p class="text-[11px] uppercase tracking-wider text-text-muted">Rules</p>
					<p class={`mt-1 text-sm font-semibold ${runtimeConfig.rules_enabled ? 'text-accent' : 'text-error'}`}>
						{toggleLabel(runtimeConfig.rules_enabled)}
					</p>
				</button>
				<button
					class="rounded-md border border-border bg-surface-elevated/50 px-3 py-3 text-left disabled:opacity-50"
					disabled={busyGlobal}
					onclick={() => toggleGlobal('shadow_mode')}
				>
					<p class="text-[11px] uppercase tracking-wider text-text-muted">Shadow Mode</p>
					<p class={`mt-1 text-sm font-semibold ${runtimeConfig.shadow_mode ? 'text-accent' : 'text-error'}`}>
						{toggleLabel(runtimeConfig.shadow_mode)}
					</p>
				</button>
				<button
					class="rounded-md border border-border bg-surface-elevated/50 px-3 py-3 text-left disabled:opacity-50"
					disabled={busyGlobal}
					onclick={() => toggleGlobal('cache_enabled')}
				>
					<p class="text-[11px] uppercase tracking-wider text-text-muted">Cache</p>
					<p class={`mt-1 text-sm font-semibold ${runtimeConfig.cache_enabled ? 'text-accent' : 'text-error'}`}>
						{toggleLabel(runtimeConfig.cache_enabled)}
					</p>
				</button>
				<button
					class="rounded-md border border-border bg-surface-elevated/50 px-3 py-3 text-left disabled:opacity-50"
					disabled={busyGlobal}
					onclick={() => toggleGlobal('router_enabled')}
				>
					<p class="text-[11px] uppercase tracking-wider text-text-muted">Router</p>
					<p class={`mt-1 text-sm font-semibold ${runtimeConfig.router_enabled ? 'text-accent' : 'text-error'}`}>
						{toggleLabel(runtimeConfig.router_enabled)}
					</p>
				</button>
			</div>
		</section>

		<section class="rounded-xl border border-border bg-surface p-4">
			<h2 class="mb-3 text-sm font-semibold uppercase tracking-wider text-text-muted">Rules</h2>
			{#if loading}
				<p class="text-sm text-text-muted">Loading…</p>
			{:else if rules.length === 0}
				<p class="text-sm text-text-muted">No rules found.</p>
			{:else}
				<div class="max-h-[62vh] overflow-auto pr-1">
					<div class="space-y-2">
						{#each rules as rule}
							<div class="rounded-md border border-border bg-surface-elevated/50 px-3 py-3 text-xs">
								<div class="flex items-center gap-2">
									<p class="font-mono text-text-secondary">{rule.name}</p>
									<span class="ml-auto rounded border border-border px-2 py-0.5 text-[11px] text-text-muted">
										{rule.deployment}
									</span>
									<span class="rounded border border-border px-2 py-0.5 text-[11px] text-text-muted">
										hits {rule.hits}
									</span>
								</div>
								<div class="mt-2 flex items-center gap-2">
									<button
										class={`rounded border px-2.5 py-1 text-[11px] ${
											rule.enabled
												? 'border-error/30 bg-error/10 text-error'
												: 'border-accent/30 bg-accent/10 text-accent'
										} disabled:opacity-50`}
										disabled={busyRuleId === rule.id}
										onclick={() => toggleRule(rule.id)}
									>
										{rule.enabled ? 'Disable' : 'Enable'}
									</button>
									<span class={`rounded border px-2 py-0.5 ${rule.enabled ? 'border-accent/30 text-accent' : 'border-warning/30 text-warning'}`}>
										{rule.status}
									</span>
									<span class="text-[11px] text-text-muted">confidence {Math.round((rule.confidence ?? 0) * 100)}%</span>
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/if}
		</section>
	</div>
</div>
