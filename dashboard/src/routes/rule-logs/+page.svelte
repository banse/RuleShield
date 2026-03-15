<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { onMount } from 'svelte';

	let { data } = $props();
	let refreshing = $state(false);

	onMount(() => {
		const interval = setInterval(async () => {
			refreshing = true;
			await invalidateAll();
			setTimeout(() => (refreshing = false), 200);
		}, 3000);
		return () => clearInterval(interval);
	});

	let events = $derived(data.events);
	let feedback = $derived(data.feedback);
	let stats = $derived(data.ruleStats);
	let rules = $derived(data.rules);
	let shadow = $derived(data.shadow);

	function dirClass(direction: string): string {
		if (direction === 'up') return 'text-accent';
		if (direction === 'down') return 'text-error';
		return 'text-text-muted';
	}

	function short(text: string, n = 80): string {
		if (!text) return '';
		return text.length > n ? `${text.slice(0, n)}...` : text;
	}

	function timeSince(timestamp: string): string {
		if (!timestamp) return '';
		const diff = Date.now() - new Date(timestamp).getTime();
		if (diff < 60000) return `${Math.floor(diff / 1000)}s ago`;
		if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
		return `${Math.floor(diff / 3600000)}h ago`;
	}
	
	let liveChangedRules = $derived(
		events
			.map((e) => e.rule_id)
			.filter((v, i, arr) => v && arr.indexOf(v) === i)
			.slice(0, 12)
	);
</script>

<svelte:head>
	<title>Rule Engine Log Board</title>
</svelte:head>

<div class="min-h-screen bg-[#0B0D12] text-text-primary">
	<div class="mx-auto max-w-6xl px-6 py-8">
		<header class="mb-6 flex items-end justify-between border-b border-border pb-4">
			<div>
				<p class="text-xs uppercase tracking-[0.18em] text-text-muted">Minimal Logs</p>
				<h1 class="text-2xl font-bold">Rule Engine Change Board</h1>
				<p class="mt-1 text-sm text-text-secondary">Confidence up/down events, live rule changes, and feedback stream.</p>
			</div>
			<div class="rounded-lg border border-border bg-surface px-3 py-2 text-xs text-text-secondary">
				<span class="mr-2 inline-block h-2 w-2 rounded-full bg-accent" class:animate-pulse={refreshing}></span>
				{data.connected ? 'Live' : 'Disconnected'}
			</div>
		</header>

		<div class="mb-5 grid gap-4 md:grid-cols-4">
			<div class="rounded-xl border border-border bg-surface p-4">
				<p class="text-xs uppercase tracking-wider text-text-muted">Shadow</p>
				<p class="mt-1 font-mono text-xl">{shadow?.enabled ? 'ON' : 'OFF'}</p>
			</div>
			<div class="rounded-xl border border-border bg-surface p-4">
				<p class="text-xs uppercase tracking-wider text-text-muted">Comparisons</p>
				<p class="mt-1 font-mono text-xl">{shadow?.total_comparisons ?? 0}</p>
			</div>
			<div class="rounded-xl border border-border bg-surface p-4">
				<p class="text-xs uppercase tracking-wider text-text-muted">Avg Similarity</p>
				<p class="mt-1 font-mono text-xl">{(shadow?.avg_similarity_pct ?? 0).toFixed(1)}%</p>
			</div>
			<div class="rounded-xl border border-border bg-surface p-4">
				<p class="text-xs uppercase tracking-wider text-text-muted">Changed Rules</p>
				<p class="mt-1 font-mono text-xl">{liveChangedRules.length}</p>
			</div>
		</div>

		<div class="grid gap-5 lg:grid-cols-[1.2fr_1fr]">
			<section class="rounded-xl border border-border bg-surface p-4">
				<h2 class="mb-3 text-sm font-semibold uppercase tracking-wider text-text-muted">Rule Value Changes</h2>
				<div class="space-y-2">
					{#if events.length === 0}
						<p class="text-sm text-text-muted">No events yet.</p>
					{:else}
						{#each events as e}
							<div class="rounded-md border border-border bg-surface-elevated/50 px-3 py-2 text-xs">
								<div class="flex items-center justify-between">
									<p class="font-mono text-text-secondary">{e.rule_id}</p>
									<p class="text-text-muted">{timeSince(e.created_at)}</p>
								</div>
								<div class="mt-1 flex items-center gap-3">
									<span class={dirClass(e.direction)}>{e.direction || 'event'}</span>
									<span class="text-text-secondary">{e.event_type}</span>
									{#if e.event_type === 'confidence_update'}
										<span class="font-mono text-text-secondary">
											{(e.old_confidence * 100).toFixed(1)}% → {(e.new_confidence * 100).toFixed(1)}%
										</span>
									{/if}
								</div>
							</div>
						{/each}
					{/if}
				</div>
			</section>

			<section class="rounded-xl border border-border bg-surface p-4">
				<h2 class="mb-3 text-sm font-semibold uppercase tracking-wider text-text-muted">Live Rule Changes</h2>
				<div class="space-y-2">
					{#each liveChangedRules as ruleId}
						{@const live = rules.find((r) => r.id === ruleId)}
						<div class="rounded-md border border-border bg-surface-elevated/50 px-3 py-2 text-xs">
							<p class="font-mono text-text-secondary">{ruleId}</p>
							{#if live}
								<p class="mt-1 text-text-muted">
									{live.status} · {live.enabled ? 'enabled' : 'disabled'} · conf {(live.confidence * 100).toFixed(1)}%
								</p>
							{:else}
								<p class="mt-1 text-text-muted">not in current rule list</p>
							{/if}
						</div>
					{/each}
				</div>
			</section>
		</div>

		<section class="mt-5 rounded-xl border border-border bg-surface p-4">
			<h2 class="mb-3 text-sm font-semibold uppercase tracking-wider text-text-muted">Feedback Stream</h2>
			<div class="overflow-x-auto">
				<table class="min-w-full text-left text-xs">
					<thead class="border-b border-border text-text-muted">
						<tr>
							<th class="px-2 py-2">Rule</th>
							<th class="px-2 py-2">Feedback</th>
							<th class="px-2 py-2">Prompt</th>
							<th class="px-2 py-2">When</th>
						</tr>
					</thead>
					<tbody>
						{#if feedback.length === 0}
							<tr><td class="px-2 py-3 text-text-muted" colspan="4">No feedback rows yet.</td></tr>
						{:else}
							{#each feedback as f}
								<tr class="border-b border-border/60">
									<td class="px-2 py-2 font-mono text-text-secondary">{f.rule_id}</td>
									<td class="px-2 py-2">
										<span class={f.feedback === 'accept' ? 'text-accent' : 'text-error'}>{f.feedback}</span>
									</td>
									<td class="px-2 py-2 text-text-secondary">{short(f.prompt_text, 100)}</td>
									<td class="px-2 py-2 text-text-muted">{timeSince(f.created_at)}</td>
								</tr>
							{/each}
						{/if}
					</tbody>
				</table>
			</div>
		</section>

		<section class="mt-5 rounded-xl border border-border bg-surface p-4">
			<h2 class="mb-3 text-sm font-semibold uppercase tracking-wider text-text-muted">Feedback by Rule</h2>
			<div class="overflow-x-auto">
				<table class="min-w-full text-left text-xs">
					<thead class="border-b border-border text-text-muted">
						<tr>
							<th class="px-2 py-2">Rule</th>
							<th class="px-2 py-2">Accept</th>
							<th class="px-2 py-2">Reject</th>
							<th class="px-2 py-2">Rate</th>
							<th class="px-2 py-2">Confidence</th>
						</tr>
					</thead>
					<tbody>
						{#if stats.length === 0}
							<tr><td class="px-2 py-3 text-text-muted" colspan="5">No feedback stats yet.</td></tr>
						{:else}
							{#each stats as s}
								<tr class="border-b border-border/60">
									<td class="px-2 py-2 font-mono text-text-secondary">{s.rule_id}</td>
									<td class="px-2 py-2 text-accent">{s.accept_count}</td>
									<td class="px-2 py-2 text-error">{s.reject_count}</td>
									<td class="px-2 py-2 text-text-secondary">{(s.acceptance_rate * 100).toFixed(1)}%</td>
									<td class="px-2 py-2 text-text-secondary">{(s.current_confidence * 100).toFixed(1)}%</td>
								</tr>
							{/each}
						{/if}
					</tbody>
				</table>
			</div>
		</section>
	</div>
</div>
