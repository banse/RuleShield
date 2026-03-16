<script lang="ts">
	import { invalidateAll } from '$app/navigation';
	import { onMount } from 'svelte';
	import { getGatewayBaseClient } from '$lib/gateway';

	let { data } = $props();
	let refreshing = $state(false);
	let profiles = $state<Array<{
		id: string;
		name: string;
		status: string;
		runtimeStatus: string;
		classification: string;
		occurrences: number;
		tokenReductionPct: number;
		optimizationConfidencePct: number;
		shadowRuns: number;
		lastValidatedAt: string;
		lastRunAt: string;
		path: string;
	}>>([]);
	let summary = $state({ total: 0, drafts: 0, active: 0, ready: 0 });
	let statusFilter = $state<'all' | 'draft' | 'active' | 'archived'>('all');
	let classFilter = $state<'all' | 'dynamic_workflow' | 'static_recurring' | 'monitor'>('all');
	let sortKey = $state<'optimizationConfidencePct' | 'shadowRuns' | 'tokenReductionPct' | 'occurrences' | 'name'>('optimizationConfidencePct');
	let sortDirection = $state<'asc' | 'desc'>('desc');
	let searchQuery = $state('');
	let payloadDrafts = $state<Record<string, string>>({});
	let selectedProfileId = $state<string | null>(null);
	let selectedProfile = $state<Record<string, unknown> | null>(null);
	let selectedProfileHistory = $state<Array<Record<string, unknown>>>([]);
	let selectedExecutionHistory = $state<Array<Record<string, unknown>>>([]);
	let selectedValidationRunId = $state<number | null>(null);
	let selectedExecutionRunId = $state<number | null>(null);
	let draftEditor = $state<{ name: string; promptTemplate: string; model: string }>({
		name: '',
		promptTemplate: '',
		model: ''
	});
	let draftShadowResult = $state<{
		profileId: string;
		totalRuns: number;
		avgSimilarityPct: number;
		avgConfidencePct: number;
		optimizedResponse: string;
	} | null>(null);
	let lastRunOutput = $state<{ profileId: string; responseText: string; model: string } | null>(null);
	let activationGuardrail = $state<{
		profileId: string;
		message: string;
		runs: number;
		confidencePct: number;
	} | null>(null);
	let detailLoading = $state(false);
	let toast = $state<{ message: string; type: 'success' | 'error' } | null>(null);
	let toastTimeout: ReturnType<typeof setTimeout> | null = null;
	let apiBase = $state('');

	onMount(() => {
		apiBase = getGatewayBaseClient();
		const interval = setInterval(async () => {
			refreshing = true;
			await invalidateAll();
			setTimeout(() => (refreshing = false), 250);
		}, 4000);

		return () => clearInterval(interval);
	});

	$effect(() => {
		profiles = [...data.profiles];
		summary = { ...data.summary };
		const nextDrafts: Record<string, string> = {};
		for (const profile of data.profiles) {
			nextDrafts[profile.id] = payloadDrafts[profile.id] ?? '';
		}
		payloadDrafts = nextDrafts;
		if (!selectedProfileId && data.profiles.length > 0) {
			void loadProfileDetail(data.profiles[0].id);
		}
	});

	let connected = $derived(data.connected);
	let filteredProfiles = $derived.by(() => {
		const filtered = profiles.filter((profile) => {
			const matchesStatus = statusFilter === 'all' || profile.status === statusFilter;
			const matchesClass = classFilter === 'all' || profile.classification === classFilter;
			const query = searchQuery.trim().toLowerCase();
			const matchesSearch =
				!query ||
				profile.id.toLowerCase().includes(query) ||
				profile.name.toLowerCase().includes(query);
			return matchesStatus && matchesClass && matchesSearch;
		});

		return filtered.toSorted((a, b) => {
			const direction = sortDirection === 'asc' ? 1 : -1;
			if (sortKey === 'name') {
				return a.name.localeCompare(b.name) * direction;
			}
			return ((a[sortKey] as number) - (b[sortKey] as number)) * direction;
		});
	});

	function showToast(message: string, type: 'success' | 'error' = 'success') {
		if (toastTimeout) clearTimeout(toastTimeout);
		toast = { message, type };
		toastTimeout = setTimeout(() => {
			toast = null;
		}, 2500);
	}

	function statusClass(status: string): string {
		if (status === 'active') return 'bg-accent/10 text-accent border-accent/20';
		if (status === 'archived') return 'bg-text-muted/10 text-text-muted border-border';
		return 'bg-warning/10 text-warning border-warning/20';
	}

	function runtimeClass(status: string): string {
		if (status === 'ready') return 'bg-primary/10 text-primary border-primary/20';
		if (status === 'archived') return 'bg-text-muted/10 text-text-muted border-border';
		return 'bg-surface-elevated text-text-secondary border-border';
	}

	async function loadProfileDetail(profileId: string) {
		selectedProfileId = profileId;
		detailLoading = true;
		try {
			const res = await fetch(`${apiBase}/api/cron-profiles/${profileId}`);
			if (!res.ok) {
				selectedProfile = null;
				selectedProfileHistory = [];
				showToast('Failed to load profile details', 'error');
				return;
			}
			const payload = await res.json();
			selectedProfile = payload.profile ?? null;
			selectedProfileHistory = Array.isArray(payload.history?.runs) ? payload.history.runs : [];
			selectedExecutionHistory = Array.isArray(payload.execution_history?.runs) ? payload.execution_history.runs : [];
			selectedValidationRunId = selectedProfileHistory.length
				? Number(selectedProfileHistory[0]?.id ?? 0) || null
				: null;
			selectedExecutionRunId = selectedExecutionHistory.length
				? Number(selectedExecutionHistory[0]?.id ?? 0) || null
				: null;
			draftEditor = {
				name: String(payload.profile?.name ?? ''),
				promptTemplate: String(payload.profile?.optimized_execution?.prompt_template ?? ''),
				model: String(payload.profile?.optimized_execution?.model ?? '')
			};
		} catch {
			selectedProfile = null;
			selectedProfileHistory = [];
			showToast('Connection error', 'error');
		} finally {
			detailLoading = false;
		}
	}

	async function activateProfile(profileId: string, force = false) {
		try {
			const res = await fetch(`${apiBase}/api/cron-profiles/${profileId}/activate`, {
				method: 'POST',
				headers: { 'content-type': 'application/json' },
				body: JSON.stringify({ force })
			});
			const payload = await res.json();
			if (!res.ok) {
				activationGuardrail = {
					profileId,
					message: String(payload.error ?? 'Activation failed'),
					runs: Number(payload.summary?.total_runs ?? 0),
					confidencePct: Number(payload.summary?.avg_optimization_confidence ?? 0) * 100
				};
				showToast(payload.error ?? 'Activation failed', 'error');
				return;
			}
			activationGuardrail = null;
			await invalidateAll();
			await loadProfileDetail(profileId);
			showToast(force ? 'Cron profile force-activated' : 'Cron profile activated');
		} catch {
			showToast('Connection error', 'error');
		}
	}

	async function runProfile(profileId: string) {
		const payloadText = payloadDrafts[profileId] ?? '';
		if (!payloadText.trim()) {
			showToast('Enter payload text first', 'error');
			return;
		}

		try {
			const res = await fetch(`${apiBase}/api/cron-profiles/${profileId}/execute`, {
				method: 'POST',
				headers: { 'content-type': 'application/json' },
				body: JSON.stringify({ payload_text: payloadText })
			});
			const payload = await res.json();
			if (!res.ok) {
				showToast(payload.error ?? 'Execution failed', 'error');
				return;
			}
			await invalidateAll();
			await loadProfileDetail(profileId);
			payloadDrafts[profileId] = '';
			const responseText = String(payload.execution?.response_text ?? '');
			lastRunOutput = {
				profileId,
				responseText,
				model: String(payload.execution?.model ?? '')
			};
			const preview = responseText.slice(0, 120);
			showToast(preview || 'Cron profile executed');
		} catch {
			showToast('Connection error', 'error');
		}
	}

	async function archiveProfile(profileId: string) {
		try {
			const res = await fetch(`${apiBase}/api/cron-profiles/${profileId}/archive`, {
				method: 'POST'
			});
			const payload = await res.json();
			if (!res.ok) {
				showToast(payload.error ?? 'Archive failed', 'error');
				return;
			}
			activationGuardrail = null;
			await invalidateAll();
			await loadProfileDetail(profileId);
			showToast('Cron profile archived');
		} catch {
			showToast('Connection error', 'error');
		}
	}

	async function restoreProfile(profileId: string) {
		try {
			const res = await fetch(`${apiBase}/api/cron-profiles/${profileId}/restore`, {
				method: 'POST'
			});
			const payload = await res.json();
			if (!res.ok) {
				showToast(payload.error ?? 'Restore failed', 'error');
				return;
			}
			await invalidateAll();
			await loadProfileDetail(profileId);
			showToast('Cron profile restored to draft');
		} catch {
			showToast('Connection error', 'error');
		}
	}

	async function duplicateProfile(profileId: string) {
		try {
			const res = await fetch(`${apiBase}/api/cron-profiles/${profileId}/duplicate`, {
				method: 'POST'
			});
			const payload = await res.json();
			if (!res.ok) {
				showToast(payload.error ?? 'Duplicate failed', 'error');
				return;
			}
			await invalidateAll();
			if (payload.profile?.id) {
				await loadProfileDetail(String(payload.profile.id));
			}
			showToast('Cron profile duplicated');
		} catch {
			showToast('Connection error', 'error');
		}
	}

	async function deleteProfile(profileId: string) {
		try {
			const res = await fetch(`${apiBase}/api/cron-profiles/${profileId}`, {
				method: 'DELETE'
			});
			const payload = await res.json();
			if (!res.ok) {
				showToast(payload.error ?? 'Delete failed', 'error');
				return;
			}
			await invalidateAll();
			if (selectedProfileId === profileId) {
				selectedProfileId = null;
				selectedProfile = null;
				selectedProfileHistory = [];
				selectedExecutionHistory = [];
				selectedValidationRunId = null;
				selectedExecutionRunId = null;
				draftShadowResult = null;
				lastRunOutput = null;
				activationGuardrail = null;
			}
			showToast('Cron profile deleted');
		} catch {
			showToast('Connection error', 'error');
		}
	}

	async function saveDraftEdits(profileId: string) {
		try {
			const res = await fetch(`${apiBase}/api/cron-profiles/${profileId}/update`, {
				method: 'POST',
				headers: { 'content-type': 'application/json' },
				body: JSON.stringify({
					name: draftEditor.name,
					prompt_template: draftEditor.promptTemplate,
					model: draftEditor.model
				})
			});
			const payload = await res.json();
			if (!res.ok) {
				showToast(payload.error ?? 'Profile update failed', 'error');
				return;
			}
			await invalidateAll();
			await loadProfileDetail(profileId);
			showToast('Draft profile updated');
		} catch {
			showToast('Connection error', 'error');
		}
	}

	async function runDraftShadow(profileId: string) {
		const payloadText = payloadDrafts[profileId] ?? '';
		if (!payloadText.trim()) {
			showToast('Enter payload text first', 'error');
			return;
		}

		try {
			const res = await fetch(`${apiBase}/api/cron-profiles/${profileId}/shadow-run`, {
				method: 'POST',
				headers: { 'content-type': 'application/json' },
				body: JSON.stringify({
					payload_text: payloadText,
					model: draftEditor.model,
					sample_limit: 3
				})
			});
			const payload = await res.json();
			if (!res.ok) {
				showToast(payload.error ?? 'Shadow run failed', 'error');
				return;
			}
			await invalidateAll();
			await loadProfileDetail(profileId);
			draftShadowResult = {
				profileId,
				totalRuns: Number(payload.summary?.total_runs ?? 0),
				avgSimilarityPct: Number(payload.summary?.avg_similarity ?? 0) * 100,
				avgConfidencePct: Number(payload.summary?.avg_optimization_confidence ?? 0) * 100,
				optimizedResponse: String(payload.optimized_response ?? '')
			};
			showToast('Draft shadow run stored');
		} catch {
			showToast('Connection error', 'error');
		}
	}

	function downloadLastRun() {
		if (!lastRunOutput?.responseText) return;
		const blob = new Blob([lastRunOutput.responseText], { type: 'text/plain;charset=utf-8' });
		const url = URL.createObjectURL(blob);
		const anchor = document.createElement('a');
		anchor.href = url;
		anchor.download = `${lastRunOutput.profileId}-last-run.txt`;
		anchor.click();
		URL.revokeObjectURL(url);
	}

	function downloadValidationHistory() {
		if (!selectedProfileId || selectedProfileHistory.length === 0) return;
		const payload = {
			profile_id: selectedProfileId,
			exported_at: new Date().toISOString(),
			runs: selectedProfileHistory
		};
		const blob = new Blob([JSON.stringify(payload, null, 2)], {
			type: 'application/json;charset=utf-8'
		});
		const url = URL.createObjectURL(blob);
		const anchor = document.createElement('a');
		anchor.href = url;
		anchor.download = `${selectedProfileId}-validation-history.json`;
		anchor.click();
		URL.revokeObjectURL(url);
	}

	function downloadValidationHistoryCsv() {
		if (!selectedProfileId || selectedProfileHistory.length === 0) return;
		const rows = [
			[
				'id',
				'created_at',
				'match_quality',
				'similarity_pct',
				'length_ratio_pct',
				'structure_score_pct',
				'optimization_confidence_pct',
				'prompt_text',
				'original_response',
				'optimized_response'
			],
			...selectedProfileHistory.map((run) => [
				String(run.id ?? ''),
				String(run.created_at ?? ''),
				String(run.match_quality ?? ''),
				Number(run.similarity_pct ?? 0).toFixed(1),
				(Number(run.length_ratio ?? 0) * 100).toFixed(1),
				Number(run.structure_score_pct ?? 0).toFixed(1),
				Number(run.optimization_confidence_pct ?? 0).toFixed(1),
				String(run.prompt_text ?? ''),
				String(run.original_response ?? ''),
				String(run.optimized_response ?? '')
			])
		];
		const csv = rows
			.map((row) =>
				row
					.map((value) => `"${value.replaceAll('"', '""')}"`)
					.join(',')
			)
			.join('\n');
		const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
		const url = URL.createObjectURL(blob);
		const anchor = document.createElement('a');
		anchor.href = url;
		anchor.download = `${selectedProfileId}-validation-history.csv`;
		anchor.click();
		URL.revokeObjectURL(url);
	}

	function selectValidationRun(runId: number) {
		selectedValidationRunId = runId;
	}

	function selectExecutionRun(runId: number) {
		selectedExecutionRunId = runId;
	}

	function diffAlertClass(value: number, kind: 'similarity' | 'length' | 'confidence'): string {
		if (kind === 'length') {
			if (value < 40) return 'border-error/20 bg-error/5 text-error';
			if (value < 70) return 'border-warning/20 bg-warning/5 text-warning';
			return 'border-accent/20 bg-accent/5 text-accent';
		}
		if (value < 40) return 'border-error/20 bg-error/5 text-error';
		if (value < 70) return 'border-warning/20 bg-warning/5 text-warning';
		return 'border-accent/20 bg-accent/5 text-accent';
	}

	function diffAlertLabel(value: number, kind: 'similarity' | 'length' | 'confidence'): string {
		if (kind === 'similarity') {
			if (value < 40) return 'Large wording drift';
			if (value < 70) return 'Moderate wording drift';
			return 'Close wording match';
		}
		if (kind === 'length') {
			if (value < 40) return 'Strong length mismatch';
			if (value < 70) return 'Moderate length mismatch';
			return 'Length is close';
		}
		if (value < 40) return 'Low activation confidence';
		if (value < 70) return 'Needs more validation';
		return 'Activation-ready confidence band';
	}

	let selectedValidationRun = $derived(
		selectedProfileHistory.find((run) => Number(run.id ?? 0) === selectedValidationRunId) ??
			selectedProfileHistory[0] ??
			null
	);
	let selectedExecutionRun = $derived(
		selectedExecutionHistory.find((run) => Number(run.id ?? 0) === selectedExecutionRunId) ??
			selectedExecutionHistory[0] ??
			null
	);
 </script>

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

<svelte:head>
	<title>RuleShield Cron Lab</title>
	<meta
		name="description"
		content="Minimal cron optimization dashboard for draft, validated, and active profiles."
	/>
</svelte:head>

<div class="min-h-screen bg-[#0B0D12] text-text-primary">
	<div class="mx-auto max-w-6xl px-6 py-8">
		<header class="mb-8 flex flex-col gap-4 border-b border-border pb-6 md:flex-row md:items-end md:justify-between">
			<div>
				<p class="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-text-muted">Cron Lab</p>
				<h1 class="text-3xl font-bold tracking-tight">Cron Optimization Profiles</h1>
				<p class="mt-2 max-w-2xl text-sm text-text-secondary">
					Ein operatives Board fuer den kompletten Cron-Profile-Lifecycle: Draft, Validation,
					Activation und Runtime-Status.
				</p>
			</div>

			<div class="flex items-center gap-3">
				<a
					href="/dashboard"
					class="rounded-lg border border-border bg-surface px-3 py-2 text-xs font-medium text-text-secondary transition-colors hover:border-primary/40 hover:text-primary"
				>
					Main Dashboard
				</a>
				<div class="rounded-lg border border-border bg-surface px-3 py-2 text-xs text-text-secondary">
					<span class:animate-pulse={connected && refreshing} class="mr-2 inline-block h-2 w-2 rounded-full bg-accent"></span>
					{connected ? 'Live Gateway' : 'Disconnected'}
				</div>
			</div>
		</header>

		<div class="mb-6 grid gap-4 md:grid-cols-4">
			<div class="rounded-xl border border-border bg-surface p-4">
				<p class="text-xs uppercase tracking-wider text-text-muted">Profiles</p>
				<p class="mt-2 font-mono text-3xl font-bold text-text-primary">{summary.total}</p>
				<p class="mt-1 text-xs text-text-muted">known cron optimization profiles</p>
			</div>
			<div class="rounded-xl border border-border bg-surface p-4">
				<p class="text-xs uppercase tracking-wider text-text-muted">Drafts</p>
				<p class="mt-2 font-mono text-3xl font-bold text-warning">{summary.drafts}</p>
				<p class="mt-1 text-xs text-text-muted">still under validation</p>
			</div>
			<div class="rounded-xl border border-border bg-surface p-4">
				<p class="text-xs uppercase tracking-wider text-text-muted">Active</p>
				<p class="mt-2 font-mono text-3xl font-bold text-accent">{summary.active}</p>
				<p class="mt-1 text-xs text-text-muted">explicitly activated</p>
			</div>
			<div class="rounded-xl border border-border bg-surface p-4">
				<p class="text-xs uppercase tracking-wider text-text-muted">Ready</p>
				<p class="mt-2 font-mono text-3xl font-bold text-primary">{summary.ready}</p>
				<p class="mt-1 text-xs text-text-muted">runtime-ready profiles</p>
			</div>
		</div>

		<div class="grid gap-6 xl:grid-cols-[1.4fr_0.9fr]">
		<section class="rounded-xl border border-border bg-surface p-5">
			<div class="mb-4 flex items-center justify-between gap-4">
				<div>
					<h2 class="text-sm font-semibold uppercase tracking-wider text-text-muted">Lifecycle Board</h2>
					<p class="mt-1 text-xs text-text-muted">
						Die wichtigsten Signale pro Profil: Status, Runtime-Zustand, Shadow-Runs,
						Optimization-Confidence und geschätzte Einsparung.
					</p>
				</div>
				<div class="rounded-lg border border-border bg-surface-elevated px-3 py-2 font-mono text-xs text-text-muted">
					/api/cron-profiles
				</div>
			</div>

			<div class="mb-4 grid gap-3 md:grid-cols-[1.2fr_0.7fr_0.8fr_0.8fr_0.7fr_auto]">
				<input
					class="rounded-lg border border-border bg-surface-elevated px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:border-primary/50 focus:outline-none"
					placeholder="Search by profile id or name..."
					bind:value={searchQuery}
				/>
				<select
					class="rounded-lg border border-border bg-surface-elevated px-3 py-2 text-sm text-text-primary focus:border-primary/50 focus:outline-none"
					bind:value={statusFilter}
				>
					<option value="all">All statuses</option>
					<option value="draft">Draft</option>
					<option value="active">Active</option>
					<option value="archived">Archived</option>
				</select>
				<select
					class="rounded-lg border border-border bg-surface-elevated px-3 py-2 text-sm text-text-primary focus:border-primary/50 focus:outline-none"
					bind:value={classFilter}
				>
					<option value="all">All classes</option>
					<option value="dynamic_workflow">dynamic_workflow</option>
					<option value="static_recurring">static_recurring</option>
					<option value="monitor">monitor</option>
				</select>
				<select
					class="rounded-lg border border-border bg-surface-elevated px-3 py-2 text-sm text-text-primary focus:border-primary/50 focus:outline-none"
					bind:value={sortKey}
				>
					<option value="optimizationConfidencePct">Sort: Confidence</option>
					<option value="shadowRuns">Sort: Shadow Runs</option>
					<option value="tokenReductionPct">Sort: Token Save</option>
					<option value="occurrences">Sort: Occurrences</option>
					<option value="name">Sort: Name</option>
				</select>
				<select
					class="rounded-lg border border-border bg-surface-elevated px-3 py-2 text-sm text-text-primary focus:border-primary/50 focus:outline-none"
					bind:value={sortDirection}
				>
					<option value="desc">Desc</option>
					<option value="asc">Asc</option>
				</select>
				<div class="rounded-lg border border-border bg-surface-elevated px-3 py-2 text-xs text-text-muted">
					Showing {filteredProfiles.length} / {profiles.length}
				</div>
			</div>

			<div class="overflow-x-auto">
				<table class="min-w-full text-left">
					<thead class="border-b border-border text-[10px] uppercase tracking-wider text-text-muted">
						<tr>
							<th class="px-3 py-2">Profile</th>
							<th class="px-3 py-2">Status</th>
							<th class="px-3 py-2">Runtime</th>
							<th class="px-3 py-2">Class</th>
							<th class="px-3 py-2">Shadow</th>
							<th class="px-3 py-2">Confidence</th>
							<th class="px-3 py-2">Token Save</th>
							<th class="px-3 py-2">Occur</th>
							<th class="px-3 py-2">Last Validated</th>
							<th class="px-3 py-2">Last Executed</th>
							<th class="px-3 py-2">Inspect</th>
							<th class="px-3 py-2">Action</th>
						</tr>
					</thead>
					<tbody>
						{#if filteredProfiles.length === 0}
							<tr>
								<td class="px-3 py-4 text-sm text-text-muted" colspan="12">
									{profiles.length === 0 ? 'No cron profiles found yet.' : 'No profiles match the current filters.'}
								</td>
							</tr>
						{:else}
							{#each filteredProfiles as profile}
								<tr class={`border-b border-border/60 ${selectedProfileId === profile.id ? 'bg-surface-elevated/40' : ''}`}>
									<td class="px-3 py-3">
										<p class="font-mono text-xs text-text-secondary">{profile.id}</p>
										<p class="mt-1 text-sm font-semibold text-text-primary">{profile.name}</p>
									</td>
									<td class="px-3 py-3">
										<span class={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase ${statusClass(profile.status)}`}>
											{profile.status}
										</span>
									</td>
									<td class="px-3 py-3">
										<span class={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase ${runtimeClass(profile.runtimeStatus)}`}>
											{profile.runtimeStatus}
										</span>
									</td>
									<td class="px-3 py-3 text-xs text-text-secondary">{profile.classification}</td>
									<td class="px-3 py-3 font-mono text-xs text-text-secondary">{profile.shadowRuns}</td>
									<td class="px-3 py-3 font-mono text-xs text-text-secondary">
										{profile.optimizationConfidencePct.toFixed(1)}%
									</td>
									<td class="px-3 py-3 font-mono text-xs text-text-secondary">
										{profile.tokenReductionPct.toFixed(1)}%
									</td>
									<td class="px-3 py-3 font-mono text-xs text-text-secondary">{profile.occurrences}</td>
									<td class="px-3 py-3 text-[11px] text-text-secondary">{profile.lastValidatedAt || 'n/a'}</td>
									<td class="px-3 py-3 text-[11px] text-text-secondary">{profile.lastRunAt || 'n/a'}</td>
									<td class="px-3 py-3">
										<div class="flex items-center gap-2">
											<button
												class="rounded-lg border border-border bg-surface-elevated px-2 py-1 text-[10px] font-semibold uppercase text-text-secondary transition-colors hover:border-primary/40 hover:text-primary"
												onclick={() => loadProfileDetail(profile.id)}
											>
												Open
											</button>
											<a
												href={`/cron-lab/${profile.id}`}
												class="rounded-lg border border-border bg-surface px-2 py-1 text-[10px] font-semibold uppercase text-text-secondary transition-colors hover:border-primary/40 hover:text-primary"
											>
												Page
											</a>
										</div>
									</td>
									<td class="px-3 py-3">
										{#if profile.status === 'draft'}
											<div class="space-y-2">
												<button
													class="rounded-lg border border-primary/30 bg-primary/10 px-2 py-1 text-[10px] font-semibold uppercase text-primary transition-colors hover:border-primary/60 hover:bg-primary/20"
													onclick={() => activateProfile(profile.id)}
												>
													Activate
												</button>
												{#if activationGuardrail?.profileId === profile.id}
													<button
														class="rounded-lg border border-error/30 bg-error/10 px-2 py-1 text-[10px] font-semibold uppercase text-error transition-colors hover:border-error/60 hover:bg-error/20"
														onclick={() => activateProfile(profile.id, true)}
													>
														Force
													</button>
												{/if}
												<button
													class="rounded-lg border border-warning/30 bg-warning/10 px-2 py-1 text-[10px] font-semibold uppercase text-warning transition-colors hover:border-warning/60 hover:bg-warning/20"
													onclick={() => archiveProfile(profile.id)}
												>
													Archive
												</button>
												<button
													class="rounded-lg border border-border bg-surface-elevated px-2 py-1 text-[10px] font-semibold uppercase text-text-secondary transition-colors hover:border-primary/40 hover:text-primary"
													onclick={() => duplicateProfile(profile.id)}
												>
													Duplicate
												</button>
											</div>
										{:else if profile.status === 'active'}
											<div class="min-w-[220px] space-y-2">
												<textarea
													class="min-h-[72px] w-full rounded-lg border border-border bg-surface-elevated px-3 py-2 text-xs text-text-primary placeholder:text-text-muted focus:border-accent/50 focus:outline-none"
													placeholder="Paste dynamic payload for this active profile..."
													value={payloadDrafts[profile.id] ?? ''}
													oninput={(event) => {
														payloadDrafts[profile.id] = (event.currentTarget as HTMLTextAreaElement).value;
													}}
												></textarea>
												<div class="flex items-center gap-2">
													<button
														class="rounded-lg border border-accent/30 bg-accent/10 px-2 py-1 text-[10px] font-semibold uppercase text-accent transition-colors hover:border-accent/60 hover:bg-accent/20"
														onclick={() => runProfile(profile.id)}
													>
														Run
													</button>
													<button
														class="rounded-lg border border-warning/30 bg-warning/10 px-2 py-1 text-[10px] font-semibold uppercase text-warning transition-colors hover:border-warning/60 hover:bg-warning/20"
														onclick={() => archiveProfile(profile.id)}
													>
														Archive
													</button>
													<button
														class="rounded-lg border border-border bg-surface-elevated px-2 py-1 text-[10px] font-semibold uppercase text-text-secondary transition-colors hover:border-primary/40 hover:text-primary"
														onclick={() => duplicateProfile(profile.id)}
													>
														Duplicate
													</button>
												</div>
											</div>
										{:else}
											<div class="space-y-2">
												<button
													class="rounded-lg border border-primary/30 bg-primary/10 px-2 py-1 text-[10px] font-semibold uppercase text-primary transition-colors hover:border-primary/60 hover:bg-primary/20"
													onclick={() => restoreProfile(profile.id)}
												>
													Restore
												</button>
												<button
													class="rounded-lg border border-border bg-surface-elevated px-2 py-1 text-[10px] font-semibold uppercase text-text-secondary transition-colors hover:border-primary/40 hover:text-primary"
													onclick={() => duplicateProfile(profile.id)}
												>
													Duplicate
												</button>
												<button
													class="rounded-lg border border-error/30 bg-error/10 px-2 py-1 text-[10px] font-semibold uppercase text-error transition-colors hover:border-error/60 hover:bg-error/20"
													onclick={() => deleteProfile(profile.id)}
												>
													Delete
												</button>
												<p class="max-w-[220px] text-[10px] leading-4 text-text-muted">
													Archived profiles are read-only and can be removed permanently here.
												</p>
											</div>
										{/if}
									</td>
								</tr>
							{/each}
						{/if}
					</tbody>
				</table>
			</div>
		</section>

		<aside class="rounded-xl border border-border bg-surface p-5">
			<div class="mb-4">
				<h2 class="text-sm font-semibold uppercase tracking-wider text-text-muted">Profile Detail</h2>
				<p class="mt-1 text-xs text-text-muted">
					Source prompt, compact prompt, validation summary and last execution without leaving the page.
				</p>
			</div>

			{#if detailLoading}
				<p class="text-sm text-text-muted">Loading profile detail...</p>
			{:else if !selectedProfile}
				<p class="text-sm text-text-muted">Select a profile from the table.</p>
			{:else}
				<div class="space-y-4">
					<div class="rounded-lg border border-border bg-surface-elevated/60 p-4">
						<p class="font-mono text-xs text-text-secondary">{String(selectedProfile.id ?? '')}</p>
						<p class="mt-1 text-sm font-semibold text-text-primary">{String(selectedProfile.name ?? '')}</p>
						<div class="mt-3 flex flex-wrap gap-2 text-[10px] uppercase">
							<span class={`rounded-full border px-2 py-0.5 font-semibold ${statusClass(String(selectedProfile.status ?? 'draft'))}`}>
								{String(selectedProfile.status ?? 'draft')}
							</span>
							<span class={`rounded-full border px-2 py-0.5 font-semibold ${runtimeClass(String(selectedProfile.runtime_status ?? 'draft'))}`}>
								{String(selectedProfile.runtime_status ?? 'draft')}
							</span>
						</div>
						<div class="mt-3 flex flex-wrap gap-2">
							{#if String(selectedProfile.status ?? 'draft') !== 'archived'}
								<button
									class="rounded-lg border border-border bg-surface px-3 py-2 text-[10px] font-semibold uppercase text-text-secondary transition-colors hover:border-primary/40 hover:text-primary"
									onclick={() => selectedProfileId && duplicateProfile(selectedProfileId)}
								>
									Duplicate Profile
								</button>
								<button
									class="rounded-lg border border-warning/30 bg-warning/10 px-3 py-2 text-[10px] font-semibold uppercase text-warning transition-colors hover:border-warning/60 hover:bg-warning/20"
									onclick={() => selectedProfileId && archiveProfile(selectedProfileId)}
								>
									Archive Profile
								</button>
							{:else}
								<button
									class="rounded-lg border border-primary/30 bg-primary/10 px-3 py-2 text-[10px] font-semibold uppercase text-primary transition-colors hover:border-primary/60 hover:bg-primary/20"
									onclick={() => selectedProfileId && restoreProfile(selectedProfileId)}
								>
									Restore To Draft
								</button>
								<button
									class="rounded-lg border border-border bg-surface px-3 py-2 text-[10px] font-semibold uppercase text-text-secondary transition-colors hover:border-primary/40 hover:text-primary"
									onclick={() => selectedProfileId && duplicateProfile(selectedProfileId)}
								>
									Duplicate Profile
								</button>
								<button
									class="rounded-lg border border-error/30 bg-error/10 px-3 py-2 text-[10px] font-semibold uppercase text-error transition-colors hover:border-error/60 hover:bg-error/20"
									onclick={() => selectedProfileId && deleteProfile(selectedProfileId)}
								>
									Delete Permanently
								</button>
							{/if}
						</div>
					</div>

					{#if String(selectedProfile.status ?? 'draft') === 'draft'}
						<div class="rounded-lg border border-primary/20 bg-primary/5 p-4">
							<div class="mb-3 flex items-center justify-between gap-3">
								<p class="text-[10px] font-semibold uppercase tracking-wider text-primary">Draft Editor</p>
								<div class="flex items-center gap-2">
									<button
										class="rounded-lg border border-warning/30 bg-warning/10 px-3 py-2 text-[10px] font-semibold uppercase text-warning transition-colors hover:border-warning/60 hover:bg-warning/20"
										onclick={() => selectedProfileId && runDraftShadow(selectedProfileId)}
									>
										Run Shadow
									</button>
									<button
										class="rounded-lg border border-primary/30 bg-primary/10 px-3 py-2 text-[10px] font-semibold uppercase text-primary transition-colors hover:border-primary/60 hover:bg-primary/20"
										onclick={() => selectedProfileId && saveDraftEdits(selectedProfileId)}
									>
										Save Draft
									</button>
								</div>
							</div>

							<div class="space-y-3">
								<div>
									<label for="draft-name" class="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-text-muted">Name</label>
									<input
										id="draft-name"
										class="w-full rounded-lg border border-border bg-surface-elevated px-3 py-2 text-sm text-text-primary focus:border-primary/50 focus:outline-none"
										bind:value={draftEditor.name}
									/>
								</div>

								<div>
									<label for="draft-prompt" class="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-text-muted">Compact Prompt</label>
									<textarea
										id="draft-prompt"
										class="min-h-[110px] w-full rounded-lg border border-border bg-surface-elevated px-3 py-2 text-sm leading-6 text-text-primary focus:border-primary/50 focus:outline-none"
										bind:value={draftEditor.promptTemplate}
									></textarea>
								</div>

								<div>
									<label for="draft-model" class="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-text-muted">Model</label>
									<input
										id="draft-model"
										class="w-full rounded-lg border border-border bg-surface-elevated px-3 py-2 font-mono text-sm text-text-primary focus:border-primary/50 focus:outline-none"
										bind:value={draftEditor.model}
									/>
								</div>
							</div>

							{#if draftShadowResult && draftShadowResult.profileId === selectedProfileId}
								<div class="rounded-lg border border-warning/20 bg-warning/5 p-4">
									<p class="text-[10px] font-semibold uppercase tracking-wider text-warning">Last Draft Shadow Run</p>
									<p class="mt-2 text-xs text-text-secondary">
										Runs: {draftShadowResult.totalRuns} · Similarity: {draftShadowResult.avgSimilarityPct.toFixed(1)}% · Confidence: {draftShadowResult.avgConfidencePct.toFixed(1)}%
									</p>
									{#if draftShadowResult.optimizedResponse}
										<pre class="mt-3 overflow-x-auto whitespace-pre-wrap rounded-lg border border-warning/10 bg-surface px-3 py-3 text-xs leading-6 text-text-secondary">{draftShadowResult.optimizedResponse}</pre>
									{/if}
								</div>
							{/if}
						</div>
					{/if}

					{#if activationGuardrail && activationGuardrail.profileId === selectedProfileId}
						<div class="rounded-lg border border-error/20 bg-error/5 p-4">
							<p class="text-[10px] font-semibold uppercase tracking-wider text-error">Activation Guardrail</p>
							<p class="mt-2 text-sm text-text-secondary">{activationGuardrail.message}</p>
							<p class="mt-2 text-xs text-text-secondary">
								Runs: {activationGuardrail.runs} · Confidence: {activationGuardrail.confidencePct.toFixed(1)}%
							</p>
							<div class="mt-3">
								<button
									class="rounded-lg border border-error/30 bg-error/10 px-3 py-2 text-[10px] font-semibold uppercase text-error transition-colors hover:border-error/60 hover:bg-error/20"
									onclick={() => selectedProfileId && activateProfile(selectedProfileId, true)}
								>
									Force Activate Anyway
								</button>
							</div>
						</div>
					{/if}

					<div class="rounded-lg border border-border bg-surface-elevated/60 p-4">
						<p class="mb-1 text-[10px] font-semibold uppercase tracking-wider text-text-muted">Source Prompt</p>
						<p class="text-sm leading-6 text-text-secondary">
							{String((selectedProfile.source as Record<string, unknown> | undefined)?.prompt_text ?? '')}
						</p>
					</div>

					<div class="rounded-lg border border-border bg-surface-elevated/60 p-4">
						<p class="mb-1 text-[10px] font-semibold uppercase tracking-wider text-text-muted">Compact Prompt</p>
						<p class="text-sm leading-6 text-text-secondary">
							{String((selectedProfile.optimized_execution as Record<string, unknown> | undefined)?.prompt_template ?? '')}
						</p>
					</div>

					<div class="grid gap-3 md:grid-cols-2">
						<div class="rounded-lg border border-border bg-surface-elevated/60 p-4">
							<p class="mb-1 text-[10px] font-semibold uppercase tracking-wider text-text-muted">Validation</p>
							<p class="text-xs text-text-secondary">
								Shadow runs: {Number((selectedProfile.validation as Record<string, unknown> | undefined)?.shadow_runs ?? 0)}
							</p>
							<p class="mt-1 text-xs text-text-secondary">
								Similarity: {(Number((selectedProfile.validation as Record<string, unknown> | undefined)?.avg_similarity ?? 0) * 100).toFixed(1)}%
							</p>
							<p class="mt-1 text-xs text-text-secondary">
								Confidence: {(Number((selectedProfile.validation as Record<string, unknown> | undefined)?.optimization_confidence ?? 0) * 100).toFixed(1)}%
							</p>
						</div>

						<div class="rounded-lg border border-border bg-surface-elevated/60 p-4">
							<p class="mb-1 text-[10px] font-semibold uppercase tracking-wider text-text-muted">Last Execution</p>
							<p class="text-xs text-text-secondary">
								Model: {String((selectedProfile.last_execution as Record<string, unknown> | undefined)?.model ?? 'n/a')}
							</p>
							<p class="mt-1 text-xs leading-5 text-text-secondary">
								{String((selectedProfile.last_execution as Record<string, unknown> | undefined)?.response_preview ?? 'No execution yet.')}
							</p>
							<p class="mt-2 text-[10px] text-text-muted">
								Last executed: {String((selectedProfile.last_run_at as string | undefined) ?? 'n/a')}
							</p>
						</div>
					</div>

					<div class="rounded-lg border border-border bg-surface-elevated/60 p-4">
						<div class="mb-3 flex items-center justify-between gap-3">
							<p class="text-[10px] font-semibold uppercase tracking-wider text-text-muted">Run Output</p>
							{#if lastRunOutput && lastRunOutput.profileId === selectedProfileId}
								<div class="flex items-center gap-2">
									<span class="font-mono text-[10px] text-text-muted">{lastRunOutput.model}</span>
									<button
										class="rounded-lg border border-border bg-surface px-2 py-1 text-[10px] font-semibold uppercase text-text-secondary transition-colors hover:border-primary/40 hover:text-primary"
										onclick={downloadLastRun}
									>
										Download
									</button>
								</div>
							{/if}
						</div>

						{#if lastRunOutput && lastRunOutput.profileId === selectedProfileId}
							<pre class="overflow-x-auto whitespace-pre-wrap rounded-lg border border-border/80 bg-surface px-3 py-3 text-xs leading-6 text-text-secondary">{lastRunOutput.responseText}</pre>
						{:else}
							<p class="text-sm text-text-muted">Run an active profile to inspect the full output here.</p>
						{/if}
					</div>

					<div class="rounded-lg border border-border bg-surface-elevated/60 p-4">
						<div class="mb-3 flex items-center justify-between gap-3">
							<p class="text-[10px] font-semibold uppercase tracking-wider text-text-muted">Execution History</p>
							<p class="font-mono text-[10px] text-text-muted">{selectedExecutionHistory.length} recent runs</p>
						</div>

						{#if selectedExecutionHistory.length === 0}
							<p class="text-sm text-text-muted">No active execution history yet.</p>
						{:else}
							<div class="space-y-3">
								{#each selectedExecutionHistory as run}
									<div class="rounded-lg border border-border/80 bg-surface px-3 py-3">
										<div class="mb-2 flex flex-wrap items-center justify-between gap-2">
											<span class="font-mono text-[10px] text-text-muted">{String(run.model ?? 'n/a')}</span>
											<div class="flex items-center gap-2">
												<span class="text-[10px] text-text-muted">{String(run.created_at ?? '')}</span>
												<button
													class="rounded-lg border border-border bg-surface-elevated px-2 py-1 text-[10px] font-semibold uppercase text-text-secondary transition-colors hover:border-primary/40 hover:text-primary"
													onclick={() => selectExecutionRun(Number(run.id ?? 0))}
												>
													Inspect Run
												</button>
											</div>
										</div>
										<p class="text-[11px] leading-5 text-text-secondary">
											{String(run.response_preview ?? '')}
										</p>
									</div>
								{/each}
							</div>
						{/if}
					</div>

					<div class="rounded-lg border border-border bg-surface-elevated/60 p-4">
						<div class="mb-3 flex items-center justify-between gap-3">
							<p class="text-[10px] font-semibold uppercase tracking-wider text-text-muted">Execution Diff</p>
							{#if selectedExecutionRun}
								<span class="font-mono text-[10px] text-text-muted">
									Run #{Number(selectedExecutionRun.id ?? 0)}
								</span>
							{/if}
						</div>

						{#if !selectedExecutionRun}
							<p class="text-sm text-text-muted">Pick an execution run to inspect payload and output.</p>
						{:else}
							<div class="grid gap-3 xl:grid-cols-2">
								<div class="rounded-lg border border-border/80 bg-surface px-3 py-3">
									<p class="mb-2 text-[10px] font-semibold uppercase tracking-wider text-text-muted">Payload</p>
									<pre class="overflow-x-auto whitespace-pre-wrap text-xs leading-6 text-text-secondary">{String(selectedExecutionRun.payload_text ?? '')}</pre>
								</div>
								<div class="rounded-lg border border-border/80 bg-surface px-3 py-3">
									<p class="mb-2 text-[10px] font-semibold uppercase tracking-wider text-text-muted">Response</p>
									<pre class="overflow-x-auto whitespace-pre-wrap text-xs leading-6 text-text-secondary">{String(selectedExecutionRun.response_text ?? '')}</pre>
								</div>
							</div>
						{/if}
					</div>

					<div class="rounded-lg border border-border bg-surface-elevated/60 p-4">
						<div class="mb-3 flex items-center justify-between gap-3">
							<p class="text-[10px] font-semibold uppercase tracking-wider text-text-muted">Validation History</p>
							<div class="flex items-center gap-2">
								<p class="font-mono text-[10px] text-text-muted">{selectedProfileHistory.length} recent runs</p>
								{#if selectedProfileHistory.length > 0}
									<button
										class="rounded-lg border border-border bg-surface px-2 py-1 text-[10px] font-semibold uppercase text-text-secondary transition-colors hover:border-primary/40 hover:text-primary"
										onclick={downloadValidationHistory}
									>
										Export JSON
									</button>
									<button
										class="rounded-lg border border-border bg-surface px-2 py-1 text-[10px] font-semibold uppercase text-text-secondary transition-colors hover:border-primary/40 hover:text-primary"
										onclick={downloadValidationHistoryCsv}
									>
										Export CSV
									</button>
								{/if}
							</div>
						</div>

						{#if selectedProfileHistory.length === 0}
							<p class="text-sm text-text-muted">No validation history yet.</p>
						{:else}
							<div class="space-y-3">
								{#each selectedProfileHistory as run}
									<div class="rounded-lg border border-border/80 bg-surface px-3 py-3">
										<div class="mb-2 flex flex-wrap items-center justify-between gap-2">
											<span class={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase ${run.match_quality === 'good' ? 'bg-accent/10 text-accent border-accent/20' : run.match_quality === 'partial' ? 'bg-warning/10 text-warning border-warning/20' : 'bg-error/10 text-error border-error/20'}`}>
												{String(run.match_quality ?? 'unknown')}
											</span>
											<div class="flex items-center gap-2">
												<span class="text-[10px] text-text-muted">{String(run.created_at ?? '')}</span>
												<button
													class="rounded-lg border border-border bg-surface-elevated px-2 py-1 text-[10px] font-semibold uppercase text-text-secondary transition-colors hover:border-primary/40 hover:text-primary"
													onclick={() => selectValidationRun(Number(run.id ?? 0))}
												>
													Inspect Diff
												</button>
											</div>
										</div>
										<div class="grid gap-3 md:grid-cols-3">
											<div>
												<p class="text-[10px] uppercase tracking-wider text-text-muted">Similarity</p>
												<p class="mt-1 font-mono text-xs text-text-secondary">{Number(run.similarity_pct ?? 0).toFixed(1)}%</p>
											</div>
											<div>
												<p class="text-[10px] uppercase tracking-wider text-text-muted">Structure</p>
												<p class="mt-1 font-mono text-xs text-text-secondary">{Number(run.structure_score_pct ?? 0).toFixed(1)}%</p>
											</div>
											<div>
												<p class="text-[10px] uppercase tracking-wider text-text-muted">Confidence</p>
												<p class="mt-1 font-mono text-xs text-text-secondary">{Number(run.optimization_confidence_pct ?? 0).toFixed(1)}%</p>
											</div>
										</div>
										<p class="mt-3 text-[11px] leading-5 text-text-secondary">
											{String(run.original_response ?? '').slice(0, 240)}
										</p>
									</div>
								{/each}
							</div>
						{/if}
					</div>

					<div class="rounded-lg border border-border bg-surface-elevated/60 p-4">
						<div class="mb-3 flex items-center justify-between gap-3">
							<p class="text-[10px] font-semibold uppercase tracking-wider text-text-muted">Validation Diff</p>
							{#if selectedValidationRun}
								<span class="font-mono text-[10px] text-text-muted">
									Run #{Number(selectedValidationRun.id ?? 0)}
								</span>
							{/if}
						</div>

						{#if !selectedValidationRun}
							<p class="text-sm text-text-muted">Pick a validation run to inspect the full comparison.</p>
						{:else}
							<div class="space-y-4">
								<div class="rounded-lg border border-border/80 bg-surface px-3 py-3">
									<p class="mb-1 text-[10px] font-semibold uppercase tracking-wider text-text-muted">Payload Prompt</p>
									<p class="text-sm leading-6 text-text-secondary">
										{String(selectedValidationRun.prompt_text ?? '')}
									</p>
								</div>

								<div class="grid gap-3 md:grid-cols-4">
									<div class={`rounded-lg border px-3 py-3 ${diffAlertClass(Number(selectedValidationRun.similarity_pct ?? 0), 'similarity')}`}>
										<p class="text-[10px] uppercase tracking-wider text-text-muted">Quality</p>
										<p class="mt-1 text-xs font-semibold uppercase text-text-secondary">
											{String(selectedValidationRun.match_quality ?? 'unknown')}
										</p>
										<p class="mt-2 text-[10px] leading-4">
											{diffAlertLabel(Number(selectedValidationRun.similarity_pct ?? 0), 'similarity')}
										</p>
									</div>
									<div class={`rounded-lg border px-3 py-3 ${diffAlertClass(Number(selectedValidationRun.similarity_pct ?? 0), 'similarity')}`}>
										<p class="text-[10px] uppercase tracking-wider text-text-muted">Similarity</p>
										<p class="mt-1 font-mono text-xs text-text-secondary">
											{Number(selectedValidationRun.similarity_pct ?? 0).toFixed(1)}%
										</p>
									</div>
									<div class={`rounded-lg border px-3 py-3 ${diffAlertClass(Number(selectedValidationRun.length_ratio ?? 0) * 100, 'length')}`}>
										<p class="text-[10px] uppercase tracking-wider text-text-muted">Length Ratio</p>
										<p class="mt-1 font-mono text-xs text-text-secondary">
											{(Number(selectedValidationRun.length_ratio ?? 0) * 100).toFixed(1)}%
										</p>
										<p class="mt-2 text-[10px] leading-4">
											{diffAlertLabel(Number(selectedValidationRun.length_ratio ?? 0) * 100, 'length')}
										</p>
									</div>
									<div class={`rounded-lg border px-3 py-3 ${diffAlertClass(Number(selectedValidationRun.optimization_confidence_pct ?? 0), 'confidence')}`}>
										<p class="text-[10px] uppercase tracking-wider text-text-muted">Confidence</p>
										<p class="mt-1 font-mono text-xs text-text-secondary">
											{Number(selectedValidationRun.optimization_confidence_pct ?? 0).toFixed(1)}%
										</p>
										<p class="mt-2 text-[10px] leading-4">
											{diffAlertLabel(Number(selectedValidationRun.optimization_confidence_pct ?? 0), 'confidence')}
										</p>
									</div>
								</div>

								<div class="grid gap-3 xl:grid-cols-2">
									<div class="rounded-lg border border-border/80 bg-surface px-3 py-3">
										<p class="mb-2 text-[10px] font-semibold uppercase tracking-wider text-text-muted">Original Output</p>
										<pre class="overflow-x-auto whitespace-pre-wrap text-xs leading-6 text-text-secondary">{String(selectedValidationRun.original_response ?? '')}</pre>
									</div>
									<div class="rounded-lg border border-border/80 bg-surface px-3 py-3">
										<p class="mb-2 text-[10px] font-semibold uppercase tracking-wider text-text-muted">Optimized Output</p>
										<pre class="overflow-x-auto whitespace-pre-wrap text-xs leading-6 text-text-secondary">{String(selectedValidationRun.optimized_response ?? '')}</pre>
									</div>
								</div>
							</div>
						{/if}
					</div>
				</div>
			{/if}
		</aside>
		</div>
	</div>
</div>
