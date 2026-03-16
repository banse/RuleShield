<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { onMount } from 'svelte';
	import { getGatewayBaseClient } from '$lib/gateway';

	let { data } = $props();

	type Rule = {
		id: string;
		name: string;
		hits: number;
		confidence: number;
		confidence_level: string;
		enabled: boolean;
		pattern_count: number;
	};

	// Local mutable copy of rules for optimistic UI
	let rules = $state<Rule[]>([]);
	let total = $state(0);
	let active = $state(0);

	// Toast state
	let toast = $state<{ message: string; type: 'success' | 'error' } | null>(null);
	let toastTimeout: ReturnType<typeof setTimeout> | null = null;

	// Sort state
	let sortKey = $state<keyof Rule>('hits');
	let sortDir = $state<'asc' | 'desc'>('desc');
	let apiBase = $state('');

	// Sync from server data
	$effect(() => {
		rules = [...data.rules];
		total = data.total;
		active = data.active;
	});

	// Sorted rules
	let sortedRules = $derived.by(() => {
		const sorted = [...rules];
		sorted.sort((a, b) => {
			const av = a[sortKey];
			const bv = b[sortKey];
			if (typeof av === 'number' && typeof bv === 'number') {
				return sortDir === 'asc' ? av - bv : bv - av;
			}
			if (typeof av === 'string' && typeof bv === 'string') {
				return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
			}
			if (typeof av === 'boolean' && typeof bv === 'boolean') {
				return sortDir === 'asc' ? (av === bv ? 0 : av ? 1 : -1) : (av === bv ? 0 : av ? -1 : 1);
			}
			return 0;
		});
		return sorted;
	});

	let totalHits = $derived(rules.reduce((sum, r) => sum + r.hits, 0));
	let maxHits = $derived(Math.max(...rules.map((r) => r.hits), 1));

	function showToast(message: string, type: 'success' | 'error' = 'success') {
		if (toastTimeout) clearTimeout(toastTimeout);
		toast = { message, type };
		toastTimeout = setTimeout(() => {
			toast = null;
		}, 2500);
	}

	function handleSort(key: keyof Rule) {
		if (sortKey === key) {
			sortDir = sortDir === 'asc' ? 'desc' : 'asc';
		} else {
			sortKey = key;
			sortDir = key === 'name' || key === 'id' ? 'asc' : 'desc';
		}
	}

	function sortIndicator(key: keyof Rule): string {
		if (sortKey !== key) return '';
		return sortDir === 'asc' ? ' \u2191' : ' \u2193';
	}

	async function toggleRule(ruleId: string) {
		// Optimistic update
		const idx = rules.findIndex((r) => r.id === ruleId);
		if (idx === -1) return;

		const prev = rules[idx].enabled;
		rules[idx].enabled = !prev;
		active = rules.filter((r) => r.enabled).length;

		try {
			const res = await fetch(`${apiBase}/api/rules/${ruleId}/toggle`, {
				method: 'POST'
			});

			if (!res.ok) {
				// Revert on failure
				rules[idx].enabled = prev;
				active = rules.filter((r) => r.enabled).length;
				showToast('Failed to toggle rule', 'error');
				return;
			}

			const result = await res.json();
			rules[idx].enabled = result.enabled;
			active = rules.filter((r) => r.enabled).length;
			showToast(`${rules[idx].name} ${result.enabled ? 'enabled' : 'disabled'}`);
		} catch {
			rules[idx].enabled = prev;
			active = rules.filter((r) => r.enabled).length;
			showToast('Connection error', 'error');
		}
	}

	function confidenceColor(confidence: number): string {
		if (confidence >= 0.9) return 'bg-accent';
		if (confidence >= 0.75) return 'bg-warning';
		return 'bg-error';
	}

	function confidenceTextColor(confidence: number): string {
		if (confidence >= 0.9) return 'text-accent';
		if (confidence >= 0.75) return 'text-warning';
		return 'text-error';
	}

	function levelBadgeClasses(level: string): string {
		switch (level) {
			case 'CONFIRMED':
				return 'bg-accent/15 text-accent border-accent/30';
			case 'LIKELY':
				return 'bg-warning/15 text-warning border-warning/30';
			case 'POSSIBLE':
				return 'bg-error/15 text-error border-error/30';
			default:
				return 'bg-text-muted/15 text-text-muted border-text-muted/30';
		}
	}

	// Auto-refresh every 5 seconds
	onMount(() => {
		apiBase = getGatewayBaseClient();
		const interval = setInterval(async () => {
			await invalidateAll();
		}, 5000);
		return () => clearInterval(interval);
	});
</script>

<!-- Toast notification -->
{#if toast}
	<div
		class="fixed right-6 top-6 z-50 flex items-center gap-2 rounded-lg border px-4 py-3 shadow-lg transition-all duration-300 {toast.type === 'success' ? 'border-accent bg-surface-elevated' : 'border-error bg-surface-elevated'}"
	>
		<div
			class="h-2 w-2 rounded-full"
			class:bg-accent={toast.type === 'success'}
			class:bg-error={toast.type === 'error'}
		></div>
		<span
			class="text-sm font-medium"
			class:text-accent={toast.type === 'success'}
			class:text-error={toast.type === 'error'}
		>
			{toast.message}
		</span>
	</div>
{/if}

<!-- Header -->
<header class="border-b border-border px-8 py-5">
	<div class="mx-auto flex max-w-[1440px] items-center justify-between">
		<div class="flex items-center gap-3">
			<a
				href="/dashboard"
				class="flex items-center gap-2 rounded-lg px-2 py-1 text-text-muted transition-colors hover:bg-surface-elevated hover:text-text-secondary"
			>
				<svg
					width="16"
					height="16"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
				>
					<path d="M19 12H5M12 19l-7-7 7-7" />
				</svg>
				<span class="text-xs font-medium">Dashboard</span>
			</a>
			<span class="text-text-muted/40">|</span>
			<div class="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/20">
				<svg
					width="18"
					height="18"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					class="text-primary"
				>
					<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
				</svg>
			</div>
			<h1 class="text-lg font-semibold tracking-tight text-text-primary">Rule Explorer</h1>
		</div>

		<div class="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5">
			<span class="font-mono text-xs text-text-secondary">
				{rules.length} rules loaded
			</span>
		</div>
	</div>
</header>

<!-- Main Content -->
<main class="mx-auto max-w-[1440px] space-y-6 px-8 py-8">
	<!-- Stats bar -->
	<div class="grid grid-cols-3 gap-4">
		<div
			class="group rounded-xl border border-border bg-surface p-6 transition-all duration-200 hover:border-primary/40 hover:shadow-[0_0_20px_rgba(108,92,231,0.08)]"
		>
			<p class="mb-1 text-xs font-medium uppercase tracking-wider text-text-muted">
				Total Rules
			</p>
			<p class="font-mono text-3xl font-bold text-text-primary">{total}</p>
		</div>

		<div
			class="group rounded-xl border border-border bg-surface p-6 transition-all duration-200 hover:border-accent/40 hover:shadow-[0_0_20px_rgba(0,212,170,0.08)]"
		>
			<p class="mb-1 text-xs font-medium uppercase tracking-wider text-text-muted">
				Active Rules
			</p>
			<div class="flex items-baseline gap-2">
				<p class="font-mono text-3xl font-bold text-accent">{active}</p>
				<span class="font-mono text-sm text-accent/70">
					/ {total}
				</span>
			</div>
		</div>

		<div
			class="group rounded-xl border border-border bg-surface p-6 transition-all duration-200 hover:border-primary/40 hover:shadow-[0_0_20px_rgba(108,92,231,0.08)]"
		>
			<p class="mb-1 text-xs font-medium uppercase tracking-wider text-text-muted">
				Total Hits
			</p>
			<p class="font-mono text-3xl font-bold text-primary">{totalHits}</p>
		</div>
	</div>

	<!-- Rules Table -->
	<div class="rounded-xl border border-border bg-surface">
		<div class="border-b border-border px-6 py-4">
			<div class="flex items-center justify-between">
				<h2 class="text-sm font-semibold uppercase tracking-wider text-text-muted">
					All Rules
				</h2>
				<span class="text-xs text-text-muted">Click column headers to sort</span>
			</div>
		</div>

		<div class="overflow-x-auto">
			<table class="w-full">
				<thead>
					<tr
						class="border-b border-border/50 text-left text-xs font-medium uppercase tracking-wider text-text-muted"
					>
						<th
							class="cursor-pointer px-6 py-3 transition-colors hover:text-text-secondary"
							onclick={() => handleSort('name')}
						>
							Name{sortIndicator('name')}
						</th>
						<th
							class="cursor-pointer px-4 py-3 transition-colors hover:text-text-secondary"
							onclick={() => handleSort('id')}
						>
							ID{sortIndicator('id')}
						</th>
						<th
							class="w-24 cursor-pointer px-4 py-3 text-right transition-colors hover:text-text-secondary"
							onclick={() => handleSort('pattern_count')}
						>
							Patterns{sortIndicator('pattern_count')}
						</th>
						<th
							class="w-40 cursor-pointer px-4 py-3 text-right transition-colors hover:text-text-secondary"
							onclick={() => handleSort('hits')}
						>
							Hits{sortIndicator('hits')}
						</th>
						<th
							class="w-44 cursor-pointer px-4 py-3 text-right transition-colors hover:text-text-secondary"
							onclick={() => handleSort('confidence')}
						>
							Confidence{sortIndicator('confidence')}
						</th>
						<th
							class="w-28 cursor-pointer px-4 py-3 text-center transition-colors hover:text-text-secondary"
							onclick={() => handleSort('confidence_level')}
						>
							Level{sortIndicator('confidence_level')}
						</th>
						<th class="w-24 px-4 py-3 text-center">Status</th>
					</tr>
				</thead>
				<tbody>
					{#if sortedRules.length === 0}
						<tr>
							<td colspan="7" class="px-6 py-16 text-center text-sm text-text-muted">
								No rules loaded. Rules will appear here once the proxy is running.
							</td>
						</tr>
					{/if}
					{#each sortedRules as rule (rule.id)}
						<tr
							class="group border-b border-border/30 transition-all duration-200 hover:bg-surface-elevated/50 hover:shadow-[inset_0_0_40px_rgba(108,92,231,0.03)]"
							class:opacity-50={!rule.enabled}
						>
							<!-- Name -->
							<td class="px-6 py-4 text-sm font-medium text-text-primary">
								{rule.name}
							</td>

							<!-- ID -->
							<td class="px-4 py-4">
								<span class="font-mono text-xs text-text-muted">{rule.id}</span>
							</td>

							<!-- Patterns -->
							<td class="px-4 py-4 text-right">
								<span
									class="inline-flex items-center justify-center rounded-md bg-surface-elevated px-2 py-0.5 font-mono text-xs text-text-secondary"
								>
									{rule.pattern_count}
								</span>
							</td>

							<!-- Hits with bar -->
							<td class="px-4 py-4 text-right">
								<div class="flex items-center justify-end gap-3">
									<div class="h-1.5 w-20 overflow-hidden rounded-full bg-surface-elevated">
										<div
											class="h-full rounded-full bg-primary transition-all duration-500"
											style="width: {(rule.hits / maxHits) * 100}%"
										></div>
									</div>
									<span class="min-w-[2rem] font-mono text-sm font-semibold text-primary">
										{rule.hits}
									</span>
								</div>
							</td>

							<!-- Confidence with progress bar -->
							<td class="px-4 py-4 text-right">
								<div class="flex items-center justify-end gap-2">
									<div class="h-1.5 w-16 overflow-hidden rounded-full bg-surface-elevated">
										<div
											class="h-full rounded-full transition-all duration-500 {confidenceColor(rule.confidence)}"
											style="width: {rule.confidence * 100}%"
										></div>
									</div>
									<span class="min-w-[3rem] font-mono text-xs {confidenceTextColor(rule.confidence)}">
										{(rule.confidence * 100).toFixed(0)}%
									</span>
								</div>
							</td>

							<!-- Confidence Level Badge -->
							<td class="px-4 py-4 text-center">
								<span
									class="inline-flex items-center rounded-md border px-2 py-0.5 font-mono text-[10px] font-semibold uppercase {levelBadgeClasses(rule.confidence_level)}"
								>
									{rule.confidence_level}
								</span>
							</td>

							<!-- Toggle -->
							<td class="px-4 py-4 text-center">
								<button
									onclick={() => toggleRule(rule.id)}
									class="relative inline-flex h-6 w-11 cursor-pointer items-center rounded-full border transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-surface {rule.enabled ? 'bg-accent border-accent' : 'bg-surface-elevated border-border'}"
									aria-label="Toggle rule {rule.name}"
									aria-pressed={rule.enabled}
								>
									<span
										class="inline-block h-4 w-4 rounded-full transition-all duration-200"
										class:translate-x-5={rule.enabled}
										class:translate-x-1={!rule.enabled}
										class:bg-accent={rule.enabled}
										class:shadow-[0_0_8px_rgba(0,212,170,0.5)]={rule.enabled}
										class:bg-text-muted={!rule.enabled}
									></span>
								</button>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</div>

	<!-- Footer -->
	<footer class="flex items-center justify-between border-t border-border/50 pb-8 pt-6">
		<p class="text-xs text-text-muted">RuleShield Hermes -- Rule Explorer</p>
		<p class="font-mono text-xs text-text-muted">
			{#if data.loadedAt}
				Last update: {new Date(data.loadedAt).toLocaleTimeString()}
			{/if}
		</p>
	</footer>
</main>
