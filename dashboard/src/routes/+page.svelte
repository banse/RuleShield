<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { onMount } from 'svelte';

	let { data } = $props();

	let now = $state(Date.now());
	let refreshing = $state(false);

	// Auto-refresh every 2 seconds
	onMount(() => {
		const interval = setInterval(async () => {
			refreshing = true;
			await invalidateAll();
			now = Date.now();
			setTimeout(() => (refreshing = false), 300);
		}, 2000);

		return () => clearInterval(interval);
	});

	// Derived stats
	let stats = $derived(data.stats);
	let connected = $derived(data.connected);
	let requests = $derived(data.requests);
	let rules = $derived(data.rules);
	let shadow = $derived(data.shadow);

	let cachePct = $derived(
		stats.total_requests > 0 ? Math.round((stats.cache_hits / stats.total_requests) * 100) : 0
	);
	let rulePct = $derived(
		stats.total_requests > 0 ? Math.round((stats.rule_hits / stats.total_requests) * 100) : 0
	);
	let routedPct = $derived(
		stats.total_requests > 0 ? Math.round((stats.routed / stats.total_requests) * 100) : 0
	);
	let passthroughPct = $derived(
		stats.total_requests > 0 ? Math.round((stats.passthrough / stats.total_requests) * 100) : 0
	);
	let llmPct = $derived(
		stats.total_requests > 0 ? Math.round((stats.llm_calls / stats.total_requests) * 100) : 0
	);

	function formatCost(cost: number): string {
		return '$' + cost.toFixed(2);
	}

	function formatLatency(ms: number): string {
		if (ms < 1000) return ms.toFixed(0) + 'ms';
		return (ms / 1000).toFixed(1) + 's';
	}

	function truncate(str: string, len: number): string {
		if (!str) return '';
		return str.length > len ? str.slice(0, len) + '...' : str;
	}

	function typeBadgeClasses(type: string): string {
		switch (type?.toUpperCase()) {
			case 'CACHE':
				return 'bg-accent/15 text-accent border-accent/30';
			case 'RULE':
				return 'bg-primary/15 text-primary border-primary/30';
			case 'ROUTED':
				return 'bg-routed/15 text-routed border-routed/30';
			case 'PASSTHROUGH':
				return 'bg-[#3B82F6]/15 text-[#3B82F6] border-[#3B82F6]/30';
			case 'LLM':
				return 'bg-warning/15 text-warning border-warning/30';
			default:
				return 'bg-text-muted/15 text-text-muted border-text-muted/30';
		}
	}

	function ruleStatusClasses(status: string): string {
		switch (status) {
			case 'candidate':
				return 'bg-primary/10 text-primary';
			case 'paused':
				return 'bg-warning/10 text-warning';
			default:
				return 'bg-accent/10 text-accent';
		}
	}

	function shadowQualityClasses(quality: string): string {
		switch (quality) {
			case 'good':
				return 'bg-accent/10 text-accent';
			case 'partial':
				return 'bg-warning/10 text-warning';
			default:
				return 'bg-error/10 text-error';
		}
	}

	function timeSince(timestamp: string): string {
		if (!timestamp) return '';
		const diff = Date.now() - new Date(timestamp).getTime();
		if (diff < 60000) return Math.floor(diff / 1000) + 's ago';
		if (diff < 3600000) return Math.floor(diff / 60000) + 'm ago';
		return Math.floor(diff / 3600000) + 'h ago';
	}
</script>

<!-- Header -->
<header class="border-b border-border px-8 py-5">
	<div class="mx-auto flex max-w-[1440px] items-center justify-between">
		<div class="flex items-center gap-3">
			<div class="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/20">
				<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-primary">
					<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
				</svg>
			</div>
			<h1 class="text-lg font-semibold tracking-tight text-text-primary">RuleShield</h1>
			<span class="rounded-md bg-surface-elevated px-2 py-0.5 text-xs font-medium text-text-muted">Dashboard</span>
			<a
				href="/home"
				class="ml-2 flex items-center gap-1.5 rounded-md border border-border bg-surface px-2.5 py-1 text-xs font-medium text-text-muted transition-all hover:border-primary/40 hover:text-primary"
			>
				<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
					<rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="3" y="14" width="7" height="7" /><rect x="14" y="14" width="7" height="7" />
				</svg>
				All Pages
			</a>
		</div>

		<div class="flex items-center gap-4">
			<!-- Refresh indicator -->
			<div class="flex items-center gap-2">
				<div
					class="h-1.5 w-1.5 rounded-full transition-all duration-300"
					class:bg-accent={connected}
					class:bg-error={!connected}
					class:shadow-[0_0_8px_rgba(0,212,170,0.6)]={connected && refreshing}
				></div>
				<span class="text-xs font-medium" class:text-accent={connected} class:text-error={!connected}>
					{connected ? 'Live' : 'Disconnected'}
				</span>
			</div>

			<!-- Connection status -->
			<div class="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5">
				<div
					class="h-2 w-2 rounded-full"
					class:bg-accent={connected}
					class:bg-error={!connected}
					class:animate-pulse={connected}
				></div>
				<span class="font-mono text-xs text-text-secondary">
					{connected ? 'gateway online' : 'offline'}
				</span>
			</div>
		</div>
	</div>
</header>

<!-- Main Content -->
<main class="mx-auto max-w-[1440px] space-y-6 px-8 py-8">

	<!-- Row 1: Metric Cards -->
	<div class="grid grid-cols-6 gap-4">
		<!-- Total Requests -->
		<div class="group rounded-xl border border-border bg-surface p-6 transition-all duration-200 hover:border-primary/40 hover:shadow-[0_0_20px_rgba(108,92,231,0.08)]">
			<p class="mb-1 text-xs font-medium uppercase tracking-wider text-text-muted">Total Requests</p>
			<p class="font-mono text-3xl font-bold text-text-primary">{stats.total_requests}</p>
		</div>

		<!-- Cache Hits -->
		<div class="group rounded-xl border border-border bg-surface p-6 transition-all duration-200 hover:border-accent/40 hover:shadow-[0_0_20px_rgba(0,212,170,0.08)]">
			<p class="mb-1 text-xs font-medium uppercase tracking-wider text-text-muted">Cache Hits</p>
			<div class="flex items-baseline gap-2">
				<p class="font-mono text-3xl font-bold text-accent">{stats.cache_hits}</p>
				<span class="font-mono text-sm text-accent/70">{cachePct}%</span>
			</div>
		</div>

		<!-- Rule Hits -->
		<div class="group rounded-xl border border-border bg-surface p-6 transition-all duration-200 hover:border-primary/40 hover:shadow-[0_0_20px_rgba(108,92,231,0.08)]">
			<p class="mb-1 text-xs font-medium uppercase tracking-wider text-text-muted">Rule Hits</p>
			<div class="flex items-baseline gap-2">
				<p class="font-mono text-3xl font-bold text-primary">{stats.rule_hits}</p>
				<span class="font-mono text-sm text-primary/70">{rulePct}%</span>
			</div>
		</div>

		<!-- Routed -->
		<div class="group rounded-xl border border-border bg-surface p-6 transition-all duration-200 hover:border-routed/40 hover:shadow-[0_0_20px_rgba(74,158,255,0.08)]">
			<p class="mb-1 text-xs font-medium uppercase tracking-wider text-text-muted">Routed</p>
			<div class="flex items-baseline gap-2">
				<p class="font-mono text-3xl font-bold text-routed">{stats.routed}</p>
				<span class="font-mono text-sm text-routed/70">{routedPct}%</span>
			</div>
		</div>

		<!-- Passthrough -->
		<div class="group rounded-xl border border-border bg-surface p-6 transition-all duration-200 hover:border-[#3B82F6]/40 hover:shadow-[0_0_20px_rgba(59,130,246,0.08)]">
			<p class="mb-1 text-xs font-medium uppercase tracking-wider text-text-muted">Passthrough</p>
			<div class="flex items-baseline gap-2">
				<p class="font-mono text-3xl font-bold text-[#3B82F6]">{stats.passthrough}</p>
				<span class="font-mono text-sm text-[#3B82F6]/70">{passthroughPct}%</span>
			</div>
		</div>

		<!-- LLM Calls -->
		<div class="group rounded-xl border border-border bg-surface p-6 transition-all duration-200 hover:border-warning/40 hover:shadow-[0_0_20px_rgba(255,184,77,0.08)]">
			<p class="mb-1 text-xs font-medium uppercase tracking-wider text-text-muted">LLM Calls</p>
			<div class="flex items-baseline gap-2">
				<p class="font-mono text-3xl font-bold text-warning">{stats.llm_calls}</p>
				<span class="font-mono text-sm text-warning/70">{llmPct}%</span>
			</div>
		</div>
	</div>

	<!-- Row 2: Savings Panel -->
	<div class="rounded-xl border border-border bg-surface p-8">
		<div class="mb-6 flex items-center gap-2">
			<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-accent">
				<path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
			</svg>
			<h2 class="text-sm font-semibold uppercase tracking-wider text-text-muted">Cost Savings</h2>
		</div>

		<div class="grid grid-cols-[1fr_1fr_auto] items-end gap-12">
			<!-- Cost breakdown -->
			<div class="space-y-4">
				<div>
					<p class="mb-1 text-xs text-text-muted">Cost Without RuleShield</p>
					<p class="font-mono text-2xl font-semibold text-text-secondary">{formatCost(stats.cost_without)}</p>
				</div>
				<div>
					<p class="mb-1 text-xs text-text-muted">Cost With RuleShield</p>
					<p class="font-mono text-2xl font-semibold text-text-primary">{formatCost(stats.cost_with)}</p>
				</div>
			</div>

			<!-- Progress bar -->
			<div class="space-y-3">
				<div class="flex items-center justify-between">
					<p class="text-xs text-text-muted">Savings Rate</p>
					<p class="font-mono text-sm font-semibold text-accent">{stats.savings_pct.toFixed(1)}%</p>
				</div>
				<div class="h-3 overflow-hidden rounded-full bg-surface-elevated">
					<div
						class="h-full rounded-full transition-all duration-700 ease-out"
						style="width: {Math.min(stats.savings_pct, 100)}%; background: linear-gradient(90deg, #6C5CE7, #00D4AA);"
					></div>
				</div>
				<div class="flex justify-between font-mono text-xs text-text-muted">
					<span>0%</span>
					<span>100%</span>
				</div>
			</div>

			<!-- Big saved number -->
			<div class="text-right">
				<p class="mb-1 text-xs text-text-muted">Total Saved</p>
				<p class="font-mono text-5xl font-bold text-accent" style="text-shadow: 0 0 30px rgba(0, 212, 170, 0.3);">
					{formatCost(stats.saved)}
				</p>
			</div>
		</div>
	</div>

	<!-- Row 3: Two columns -->
	<div class="grid grid-cols-[1.5fr_1fr] gap-6">
		<!-- Recent Requests Table -->
		<div class="rounded-xl border border-border bg-surface">
			<div class="border-b border-border px-6 py-4">
				<h2 class="text-sm font-semibold uppercase tracking-wider text-text-muted">Recent Requests</h2>
			</div>

			<div class="overflow-x-auto">
				<table class="w-full">
					<thead>
						<tr class="border-b border-border/50 text-left text-xs font-medium uppercase tracking-wider text-text-muted">
							<th class="px-6 py-3 w-12">#</th>
							<th class="px-4 py-3">Prompt</th>
							<th class="px-4 py-3 w-24">Type</th>
							<th class="px-4 py-3 w-20 text-right">Cost</th>
							<th class="px-4 py-3 w-20 text-right">Time</th>
						</tr>
					</thead>
					<tbody>
						{#if requests.length === 0}
							<tr>
								<td colspan="5" class="px-6 py-12 text-center text-sm text-text-muted">
									No requests yet. Send a request through RuleShield to see it here.
								</td>
							</tr>
						{/if}
						{#each requests.slice(0, 10) as req, i}
							<tr class="border-b border-border/30 transition-colors hover:bg-surface-elevated/50">
								<td class="px-6 py-3 font-mono text-xs text-text-muted">{req.id}</td>
								<td class="max-w-[300px] px-4 py-3">
									<span class="block truncate font-mono text-xs text-text-secondary" title={req.prompt}>
										"{truncate(req.prompt, 45)}"
									</span>
								</td>
								<td class="px-4 py-3">
									<span class="inline-flex items-center rounded-md border px-2 py-0.5 font-mono text-[10px] font-semibold uppercase {typeBadgeClasses(req.type)}">
										{req.type}
									</span>
								</td>
								<td class="px-4 py-3 text-right font-mono text-xs text-text-secondary">
									{formatCost(req.cost)}
								</td>
								<td class="px-4 py-3 text-right font-mono text-xs text-text-muted">
									{formatLatency(req.latency_ms)}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>

		<!-- Top Rules Table -->
		<div class="rounded-xl border border-border bg-surface">
			<div class="flex items-center justify-between border-b border-border px-6 py-4">
				<h2 class="text-sm font-semibold uppercase tracking-wider text-text-muted">Top Rules</h2>
				<a
					href="/rules"
					class="flex items-center gap-1.5 rounded-md border border-border bg-surface-elevated px-3 py-1.5 text-xs font-medium text-text-secondary transition-all hover:border-primary/40 hover:text-primary"
				>
					Rule Explorer
					<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<path d="M5 12h14M12 5l7 7-7 7" />
					</svg>
				</a>
			</div>

			<div class="overflow-x-auto">
				<table class="w-full">
					<thead>
						<tr class="border-b border-border/50 text-left text-xs font-medium uppercase tracking-wider text-text-muted">
							<th class="px-6 py-3">Rule</th>
							<th class="px-4 py-3 w-16 text-right">Hits</th>
							<th class="px-4 py-3 w-24 text-right">Confidence</th>
							<th class="px-4 py-3 w-20 text-right">Status</th>
						</tr>
					</thead>
					<tbody>
						{#if rules.length === 0}
							<tr>
								<td colspan="4" class="px-6 py-12 text-center text-sm text-text-muted">
									No rules defined yet.
								</td>
							</tr>
						{/if}
						{#each rules as rule}
							<tr class="border-b border-border/30 transition-colors hover:bg-surface-elevated/50">
								<td class="px-6 py-3 text-sm text-text-primary">{rule.name}</td>
								<td class="px-4 py-3 text-right font-mono text-sm font-semibold text-primary">{rule.hits}</td>
									<td class="px-4 py-3 text-right">
										<div class="flex items-center justify-end gap-2">
											<div class="h-1.5 w-16 overflow-hidden rounded-full bg-surface-elevated">
												<div
													class="h-full rounded-full bg-accent"
													style="width: {Math.min(rule.confidence * 100, 100)}%"
												></div>
											</div>
											<span class="font-mono text-xs text-text-secondary">{(rule.confidence * 100).toFixed(0)}%</span>
										</div>
									</td>
									<td class="px-4 py-3 text-right">
										<span class={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${ruleStatusClasses(rule.status)}`}>
											<span class="h-1.5 w-1.5 rounded-full bg-current"></span>
											{rule.status}
										</span>
									</td>
								</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	</div>

	<!-- Row 4: Shadow Mode Panel (conditional) -->
		{#if shadow && shadow.total_comparisons > 0}
			<div class="rounded-xl border border-primary/30 bg-surface p-8">
			<div class="mb-6 flex items-center gap-2">
				<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-primary">
					<circle cx="12" cy="12" r="10" />
					<path d="M12 16v-4M12 8h.01" />
				</svg>
				<h2 class="text-sm font-semibold uppercase tracking-wider text-text-muted">Shadow Mode</h2>
				<span class="rounded-full bg-primary/15 px-2 py-0.5 text-[10px] font-semibold uppercase text-primary">Experimental</span>
			</div>

			<div class="grid grid-cols-3 gap-8">
					<div>
						<p class="mb-1 text-xs text-text-muted">Average Similarity</p>
						<div class="flex items-baseline gap-2">
							<p class="font-mono text-3xl font-bold text-primary">{shadow.avg_similarity_pct.toFixed(1)}%</p>
						</div>
						<div class="mt-2 h-2 overflow-hidden rounded-full bg-surface-elevated">
							<div
								class="h-full rounded-full bg-primary transition-all duration-500"
								style="width: {shadow.avg_similarity_pct}%"
							></div>
						</div>
					</div>

					<div>
						<p class="mb-1 text-xs text-text-muted">Rules Ready for Activation</p>
						<p class="font-mono text-3xl font-bold text-accent">{shadow.rules_ready}</p>
						<p class="mt-1 text-xs text-text-muted">of {shadow.total_comparisons} shadow comparisons</p>
					</div>

					<div>
						<p class="mb-1 text-xs text-text-muted">Total Shadow Comparisons</p>
						<p class="font-mono text-3xl font-bold text-text-primary">{shadow.total_comparisons}</p>
					</div>
				</div>

				{#if shadow.entries && shadow.entries.length > 0}
					<div class="mt-6 border-t border-border pt-4">
						<p class="mb-3 text-xs font-medium uppercase tracking-wider text-text-muted">Recent Shadow Comparisons</p>
						<div class="space-y-2">
							{#each shadow.entries.slice(0, 5) as entry}
								<div class="flex items-center justify-between rounded-lg bg-surface-elevated/50 px-4 py-2">
									<span class="font-mono text-xs text-text-secondary">{entry.rule_id}</span>
									<div class="flex items-center gap-4">
										<span class="text-xs text-text-muted">{entry.comparisons} comparisons</span>
										<span class={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${shadowQualityClasses(entry.quality)}`}>
											{entry.quality}
										</span>
										<span class="font-mono text-xs font-semibold"
											class:text-accent={entry.avg_similarity_pct >= 80}
											class:text-warning={entry.avg_similarity_pct < 80 && entry.avg_similarity_pct >= 60}
											class:text-error={entry.avg_similarity_pct < 60}>
											{entry.avg_similarity_pct.toFixed(1)}%
										</span>
									</div>
								</div>
							{/each}
					</div>
				</div>
			{/if}

			{#if shadow.tune_examples && shadow.tune_examples.length > 0}
				<div class="mt-6 border-t border-border pt-4">
					<p class="mb-3 text-xs font-medium uppercase tracking-wider text-text-muted">Tune Next</p>
					<div class="space-y-3">
						{#each shadow.tune_examples as example}
							<div class="rounded-lg border border-error/20 bg-surface-elevated/60 p-4">
								<div class="mb-3 flex items-center justify-between gap-3">
									<span class="font-mono text-xs text-text-secondary">{example.rule_id}</span>
									<div class="flex items-center gap-3">
										<span class={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${shadowQualityClasses(example.match_quality)}`}>
											{example.match_quality}
										</span>
										<span class="font-mono text-xs font-semibold text-error">
											{example.similarity_pct.toFixed(1)}%
										</span>
									</div>
								</div>
								<div class="grid gap-3 md:grid-cols-3">
									<div>
										<p class="mb-1 text-[10px] font-semibold uppercase tracking-wider text-text-muted">Prompt</p>
										<p class="text-xs leading-5 text-text-secondary">{truncate(example.prompt_text, 180)}</p>
									</div>
									<div>
										<p class="mb-1 text-[10px] font-semibold uppercase tracking-wider text-text-muted">Rule Response</p>
										<p class="text-xs leading-5 text-text-secondary">{truncate(example.rule_response, 180)}</p>
									</div>
									<div>
										<p class="mb-1 text-[10px] font-semibold uppercase tracking-wider text-text-muted">LLM Response</p>
										<p class="text-xs leading-5 text-text-secondary">{truncate(example.llm_response, 180)}</p>
									</div>
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	{/if}

	<!-- Footer -->
	<footer class="flex items-center justify-between border-t border-border/50 pt-6 pb-8">
		<p class="text-xs text-text-muted">
			RuleShield Hermes -- LLM Cost Optimizer
		</p>
		<p class="font-mono text-xs text-text-muted">
			{#if data.loadedAt}
				Last update: {new Date(data.loadedAt).toLocaleTimeString()}
			{/if}
		</p>
	</footer>
</main>
