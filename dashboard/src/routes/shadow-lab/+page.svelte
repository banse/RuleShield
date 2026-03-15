<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { onMount } from 'svelte';

	let { data } = $props();
	let refreshing = $state(false);

	onMount(() => {
		const interval = setInterval(async () => {
			refreshing = true;
			await invalidateAll();
			setTimeout(() => (refreshing = false), 250);
		}, 3000);

		return () => clearInterval(interval);
	});

	let shadow = $derived(data.shadow);
	let candidates = $derived(data.candidateRules);
	let requests = $derived(data.recentShadowRequests);
	let connected = $derived(data.connected);

	function truncate(text: string, length: number): string {
		if (!text) return '';
		return text.length > length ? `${text.slice(0, length)}...` : text;
	}

	function formatLatency(ms: number): string {
		return ms < 1000 ? `${ms.toFixed(0)}ms` : `${(ms / 1000).toFixed(1)}s`;
	}

	function timeSince(timestamp: string): string {
		if (!timestamp) return '';
		const diff = Date.now() - new Date(timestamp).getTime();
		if (diff < 60000) return `${Math.floor(diff / 1000)}s ago`;
		if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
		return `${Math.floor(diff / 3600000)}h ago`;
	}

	function qualityClasses(quality: string): string {
		switch (quality) {
			case 'good':
				return 'bg-accent/10 text-accent border-accent/20';
			case 'partial':
				return 'bg-warning/10 text-warning border-warning/20';
			default:
				return 'bg-error/10 text-error border-error/20';
		}
	}
</script>

<svelte:head>
	<title>RuleShield Shadow Lab</title>
	<meta
		name="description"
		content="Minimal Shadow Mode dashboard for Hermes and RuleShield tuning."
	/>
</svelte:head>

<div class="min-h-screen bg-[#0B0D12] text-text-primary">
	<div class="mx-auto max-w-6xl px-6 py-8">
		<header class="mb-8 flex flex-col gap-4 border-b border-border pb-6 md:flex-row md:items-end md:justify-between">
			<div>
				<p class="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">Shadow Lab</p>
				<h1 class="text-3xl font-bold tracking-tight">Hermes Shadow Mode Tuning</h1>
				<p class="mt-2 max-w-2xl text-sm text-text-secondary">
					Ein minimales Live-Board fuer Candidate-Regeln, schlechte Shadow-Beispiele und die letzten
					shadow-relevanten Requests.
				</p>
			</div>

			<div class="flex items-center gap-3">
				<a
					href="/"
					class="rounded-lg border border-border bg-surface px-3 py-2 text-xs font-medium text-text-secondary transition-colors hover:border-primary/40 hover:text-primary"
				>
					Main Dashboard
				</a>
				<div class="rounded-lg border border-border bg-surface px-3 py-2 text-xs text-text-secondary">
					<span class:animate-pulse={connected && refreshing} class="mr-2 inline-block h-2 w-2 rounded-full bg-accent"></span>
					{connected ? `Live on :8337` : 'Disconnected'}
				</div>
			</div>
		</header>

		<div class="mb-6 grid gap-4 md:grid-cols-4">
			<div class="rounded-xl border border-border bg-surface p-4">
				<p class="text-xs uppercase tracking-wider text-text-muted">Recent Window</p>
				<p class="mt-2 font-mono text-3xl font-bold text-text-primary">{data.recentWindow}</p>
				<p class="mt-1 text-xs text-text-muted">last shadow comparisons</p>
			</div>
			<div class="rounded-xl border border-border bg-surface p-4">
				<p class="text-xs uppercase tracking-wider text-text-muted">Comparisons</p>
				<p class="mt-2 font-mono text-3xl font-bold text-primary">
					{shadow?.total_comparisons ?? 0}
				</p>
				<p class="mt-1 text-xs text-text-muted">recent shadow results</p>
			</div>
			<div class="rounded-xl border border-border bg-surface p-4">
				<p class="text-xs uppercase tracking-wider text-text-muted">Avg Similarity</p>
				<p class="mt-2 font-mono text-3xl font-bold text-warning">
					{shadow ? shadow.avg_similarity_pct.toFixed(1) : '0.0'}%
				</p>
				<p class="mt-1 text-xs text-text-muted">should trend upward</p>
			</div>
			<div class="rounded-xl border border-border bg-surface p-4">
				<p class="text-xs uppercase tracking-wider text-text-muted">Candidate Rules</p>
				<p class="mt-2 font-mono text-3xl font-bold text-accent">{candidates.length}</p>
				<p class="mt-1 text-xs text-text-muted">{shadow?.rules_ready ?? 0} ready to promote</p>
			</div>
		</div>

		<div class="grid gap-6 lg:grid-cols-[1.05fr_1.4fr]">
			<section class="rounded-xl border border-border bg-surface p-5">
				<div class="mb-4 flex items-center justify-between">
					<div>
						<h2 class="text-sm font-semibold uppercase tracking-wider text-text-muted">Candidates</h2>
						<p class="mt-1 text-xs text-text-muted">Current shadow-only rules and their live confidence.</p>
					</div>
				</div>

				<div class="space-y-3">
					{#if candidates.length === 0}
						<p class="text-sm text-text-muted">No candidate rules loaded.</p>
					{:else}
						{#each candidates as rule}
							<div class="rounded-lg border border-border bg-surface-elevated/60 p-3">
								<div class="flex items-start justify-between gap-3">
									<div>
										<p class="font-mono text-xs text-text-secondary">{rule.id}</p>
										<p class="mt-1 text-sm font-semibold text-text-primary">{rule.name}</p>
									</div>
									<span class="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-semibold uppercase text-primary">
										{rule.status}
									</span>
								</div>
								<div class="mt-3 grid grid-cols-2 gap-3 text-xs text-text-secondary">
									<div>
										<p class="text-text-muted">Shadow hits</p>
										<p class="mt-1 font-mono text-base text-text-primary">{rule.shadow_hits}</p>
									</div>
									<div>
										<p class="text-text-muted">Confidence</p>
										<p class="mt-1 font-mono text-base text-text-primary">
											{(rule.confidence * 100).toFixed(1)}%
										</p>
									</div>
								</div>
							</div>
						{/each}
					{/if}
				</div>
			</section>

			<section class="rounded-xl border border-border bg-surface p-5">
				<div class="mb-4">
					<h2 class="text-sm font-semibold uppercase tracking-wider text-text-muted">Tune Next</h2>
					<p class="mt-1 text-xs text-text-muted">
						Die schlechtesten Beispiele zuerst. Genau diese Dreiecke sind die Grundlage fuer Rule-Tuning.
					</p>
				</div>

				<div class="space-y-4">
					{#if !shadow?.tune_examples?.length}
						<p class="text-sm text-text-muted">Noch keine schlechten Shadow-Beispiele vorhanden.</p>
					{:else}
						{#each shadow.tune_examples as example}
							<div class="rounded-lg border border-error/20 bg-surface-elevated/60 p-4">
								<div class="mb-3 flex flex-wrap items-center justify-between gap-3">
									<div>
										<p class="font-mono text-xs text-text-secondary">{example.rule_id}</p>
										<p class="mt-1 text-xs text-text-muted">{example.created_at}</p>
									</div>
									<div class="flex items-center gap-2">
										<span class={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase ${qualityClasses(example.match_quality)}`}>
											{example.match_quality}
										</span>
										<span class="font-mono text-xs font-semibold text-error">
											{example.similarity_pct.toFixed(1)}%
										</span>
									</div>
								</div>

								<div class="grid gap-4 md:grid-cols-3">
									<div>
										<p class="mb-1 text-[10px] font-semibold uppercase tracking-wider text-text-muted">Prompt</p>
										<p class="text-sm leading-6 text-text-secondary">{truncate(example.prompt_text, 220)}</p>
									</div>
									<div>
										<p class="mb-1 text-[10px] font-semibold uppercase tracking-wider text-text-muted">Rule Response</p>
										<p class="text-sm leading-6 text-text-secondary">{truncate(example.rule_response, 220)}</p>
									</div>
									<div>
										<p class="mb-1 text-[10px] font-semibold uppercase tracking-wider text-text-muted">LLM Response</p>
										<p class="text-sm leading-6 text-text-secondary">{truncate(example.llm_response, 260)}</p>
									</div>
								</div>
							</div>
						{/each}
					{/if}
				</div>
			</section>
		</div>

		<section class="mt-6 rounded-xl border border-border bg-surface p-5">
			<div class="mb-4 flex items-center justify-between gap-4">
				<div>
					<h2 class="text-sm font-semibold uppercase tracking-wider text-text-muted">Recent Shadow Requests</h2>
					<p class="mt-1 text-xs text-text-muted">Nur die letzten Requests mit `shadow` im Prompt.</p>
				</div>
				<div class="rounded-lg border border-border bg-surface-elevated px-3 py-2 font-mono text-xs text-text-muted">
					/api/shadow?recent={data.recentWindow}
				</div>
			</div>

			<div class="overflow-x-auto">
				<table class="min-w-full text-left">
					<thead class="border-b border-border text-[10px] uppercase tracking-wider text-text-muted">
						<tr>
							<th class="px-3 py-2">Prompt</th>
							<th class="px-3 py-2">Model</th>
							<th class="px-3 py-2">Type</th>
							<th class="px-3 py-2">Latency</th>
							<th class="px-3 py-2">When</th>
						</tr>
					</thead>
					<tbody>
						{#if requests.length === 0}
							<tr>
								<td class="px-3 py-4 text-sm text-text-muted" colspan="5">No recent shadow-related requests.</td>
							</tr>
						{:else}
							{#each requests as request}
								<tr class="border-b border-border/60">
									<td class="px-3 py-3 text-sm text-text-secondary">{truncate(request.prompt, 90)}</td>
									<td class="px-3 py-3 font-mono text-xs text-text-secondary">{request.model}</td>
									<td class="px-3 py-3 text-xs text-text-secondary">{request.type}</td>
									<td class="px-3 py-3 font-mono text-xs text-text-secondary">{formatLatency(request.latency_ms)}</td>
									<td class="px-3 py-3 text-xs text-text-muted">{timeSince(request.timestamp)}</td>
								</tr>
							{/each}
						{/if}
					</tbody>
				</table>
			</div>
		</section>
	</div>
</div>
