<script lang="ts">
	let { data } = $props();

	let profile = $derived((data.detail?.profile as Record<string, unknown> | undefined) ?? null);
	let history = $derived(
		(data.detail?.history as { runs?: Array<Record<string, unknown>> } | undefined)?.runs ?? []
	);
	let executionHistory = $derived(
		(data.detail?.execution_history as { runs?: Array<Record<string, unknown>> } | undefined)?.runs ?? []
	);
	let automation = $derived((data.detail?.automation as Record<string, unknown> | undefined) ?? null);
</script>

<svelte:head>
	<title>Cron Profile Detail</title>
</svelte:head>

<div class="min-h-screen bg-[#0B0D12] text-text-primary">
	<div class="mx-auto max-w-5xl px-6 py-8">
		<div class="mb-6 flex items-center justify-between gap-4">
			<div>
				<p class="text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">Cron Profile</p>
				<h1 class="mt-2 text-3xl font-bold tracking-tight">{String(profile?.name ?? data.profileId)}</h1>
				<p class="mt-2 font-mono text-xs text-text-muted">{data.profileId}</p>
			</div>
			<div class="flex items-center gap-3">
				<a
					href="/cron-lab"
					class="rounded-lg border border-border bg-surface px-3 py-2 text-xs font-medium text-text-secondary transition-colors hover:border-primary/40 hover:text-primary"
				>
					Back to Cron Lab
				</a>
				<div class="rounded-lg border border-border bg-surface px-3 py-2 text-xs text-text-secondary">
					{data.connected ? 'Live on :8337' : 'Disconnected'}
				</div>
			</div>
		</div>

		{#if !profile}
			<div class="rounded-xl border border-border bg-surface p-6 text-sm text-text-muted">
				Profile not found.
			</div>
		{:else}
			<div class="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
				<section class="space-y-6">
					<div class="rounded-xl border border-border bg-surface p-5">
						<h2 class="text-sm font-semibold uppercase tracking-wider text-text-muted">Overview</h2>
						<div class="mt-4 grid gap-3 md:grid-cols-2">
							<div class="rounded-lg border border-border bg-surface-elevated/60 p-4">
								<p class="text-[10px] uppercase tracking-wider text-text-muted">Status</p>
								<p class="mt-2 text-sm text-text-primary">{String(profile.status ?? 'draft')}</p>
							</div>
							<div class="rounded-lg border border-border bg-surface-elevated/60 p-4">
								<p class="text-[10px] uppercase tracking-wider text-text-muted">Runtime</p>
								<p class="mt-2 text-sm text-text-primary">{String(profile.runtime_status ?? 'draft')}</p>
							</div>
							<div class="rounded-lg border border-border bg-surface-elevated/60 p-4">
								<p class="text-[10px] uppercase tracking-wider text-text-muted">Last Validated</p>
								<p class="mt-2 text-sm text-text-primary">{String((profile.validation as Record<string, unknown> | undefined)?.last_validated_at ?? 'n/a')}</p>
							</div>
							<div class="rounded-lg border border-border bg-surface-elevated/60 p-4">
								<p class="text-[10px] uppercase tracking-wider text-text-muted">Last Executed</p>
								<p class="mt-2 text-sm text-text-primary">{String(profile.last_run_at ?? 'n/a')}</p>
							</div>
						</div>
					</div>

					<div class="rounded-xl border border-border bg-surface p-5">
						<h2 class="text-sm font-semibold uppercase tracking-wider text-text-muted">Compact Prompt</h2>
						<pre class="mt-4 overflow-x-auto whitespace-pre-wrap rounded-lg border border-border/80 bg-surface-elevated px-4 py-4 text-xs leading-6 text-text-secondary">{String((profile.optimized_execution as Record<string, unknown> | undefined)?.prompt_template ?? '')}</pre>
					</div>

					<div class="rounded-xl border border-border bg-surface p-5">
						<div class="mb-3 flex items-center justify-between gap-3">
							<h2 class="text-sm font-semibold uppercase tracking-wider text-text-muted">Validation History</h2>
							<p class="font-mono text-[10px] text-text-muted">{history.length} recent runs</p>
						</div>
						<div class="space-y-3">
							{#if history.length === 0}
								<p class="text-sm text-text-muted">No validation history yet.</p>
							{:else}
								{#each history as run}
									<div class="rounded-lg border border-border/80 bg-surface-elevated/60 p-4">
										<div class="mb-2 flex flex-wrap items-center justify-between gap-2">
											<p class="text-[10px] uppercase tracking-wider text-text-muted">{String(run.created_at ?? '')}</p>
											<p class="font-mono text-[10px] text-text-secondary">
												{Number(run.similarity_pct ?? 0).toFixed(1)}% similarity
											</p>
										</div>
										<div class="grid gap-3 md:grid-cols-2">
											<pre class="overflow-x-auto whitespace-pre-wrap rounded-lg border border-border bg-surface px-3 py-3 text-xs leading-6 text-text-secondary">{String(run.original_response ?? '')}</pre>
											<pre class="overflow-x-auto whitespace-pre-wrap rounded-lg border border-border bg-surface px-3 py-3 text-xs leading-6 text-text-secondary">{String(run.optimized_response ?? '')}</pre>
										</div>
									</div>
								{/each}
							{/if}
						</div>
					</div>
				</section>

				<aside class="space-y-6">
					<div class="rounded-xl border border-border bg-surface p-5">
						<h2 class="text-sm font-semibold uppercase tracking-wider text-text-muted">Execution History</h2>
						<div class="mt-4 space-y-3">
							{#if executionHistory.length === 0}
								<p class="text-sm text-text-muted">No execution history yet.</p>
							{:else}
								{#each executionHistory as run}
									<div class="rounded-lg border border-border/80 bg-surface-elevated/60 p-4">
										<p class="text-[10px] uppercase tracking-wider text-text-muted">{String(run.created_at ?? '')}</p>
										<p class="mt-2 font-mono text-[10px] text-text-muted">{String(run.model ?? '')}</p>
										<pre class="mt-3 overflow-x-auto whitespace-pre-wrap rounded-lg border border-border bg-surface px-3 py-3 text-xs leading-6 text-text-secondary">{String(run.response_preview ?? '')}</pre>
									</div>
								{/each}
							{/if}
						</div>
					</div>

					<div class="rounded-xl border border-border bg-surface p-5">
						<h2 class="text-sm font-semibold uppercase tracking-wider text-text-muted">Automation Suggestion</h2>
						{#if !automation}
							<p class="mt-4 text-sm text-text-muted">Activate the profile to generate an automation suggestion.</p>
						{:else}
							<p class="mt-3 text-xs text-text-secondary">
								Generated for Codex automations using the inferred schedule from the source workflow.
							</p>
							<pre class="mt-4 overflow-x-auto whitespace-pre-wrap rounded-lg border border-border/80 bg-surface-elevated px-3 py-3 text-xs leading-6 text-text-secondary">{String(automation.directive ?? '')}</pre>
						{/if}
					</div>
				</aside>
			</div>
		{/if}
	</div>
</div>
