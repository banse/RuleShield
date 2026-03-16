<script lang="ts">
	import { onMount, tick } from 'svelte';
	import {
		DEFAULT_GATEWAY_BASE,
		GATEWAY_BASE_STORAGE_KEY,
		getGatewayBaseClient
	} from '$lib/gateway';

	let apiBase = $state(DEFAULT_GATEWAY_BASE);

	type ScriptEntry = {
		path: string;
		name: string;
		type: string;
		default_model_profile_id?: string;
		status: 'active' | 'inactive' | 'failed' | 'not_started';
		active_run_id: string | null;
		last_run_id: string | null;
		last_return_code: number | null;
	};

	type ModelProfile = {
		id: string;
		label: string;
		provider: string;
		provider_label: string;
		model: string;
		fallback_model: string;
		script_suffix: string;
	};

	type RunEntry = {
		run_id: string;
		script_path: string;
		command: string[];
		status: string;
		model_profile_id?: string;
		started_at: number;
		ended_at: number | null;
		return_code: number | null;
		event_count: number;
	};

	type RunEvent = {
		ts: number;
		kind: 'input' | 'output';
		text: string;
	};

	type RuleEvent = {
		created_at?: string;
		rule_id?: string;
		event_type?: string;
		details?: {
			direction?: string;
			previous_confidence?: number;
			new_confidence?: number;
		};
	};

	type RunRuleShieldStats = {
		available: boolean;
		triggered_rules: number;
		would_trigger_shadow: number;
		cost_without: number;
		cost_with: number;
		savings_usd: number;
		savings_pct: number;
		shadow_enabled: boolean;
		confidence_up: number;
		confidence_down: number;
		recent_rule_events: RuleEvent[];
	};

	let loading = $state(true);
	let busyPath = $state<string | null>(null);
	let error = $state('');
	let scripts = $state<ScriptEntry[]>([]);
	let visibleScripts = $state<ScriptEntry[]>([]);
	let runs = $state<RunEntry[]>([]);
	let selectedRunId = $state<string>('');
	let selectedRunEvents = $state<RunEvent[]>([]);
	let selectedRunStatus = $state('');
	let selectedRunPinnedUntil = $state(0);
	let logPanel: HTMLDivElement | null = $state(null);
	let lastLogFingerprint = $state('');
	let shadowEnabled = $state(false);
	let shadowComparisons = $state(0);
	let activeRules = $state(0);
	let confidenceUp = $state(0);
	let confidenceDown = $state(0);
	let latestRuleEvents = $state<RuleEvent[]>([]);
	let selectedRunRuleShield = $state<RunRuleShieldStats | null>(null);
	let modelProfiles = $state<ModelProfile[]>([]);
	let selectedModelProfileId = $state('');
	let lastSelectedModelProfileId = $state('');
	const PROFILE_STORAGE_KEY = 'ruleshield_test_monitor_profile_id';
	const ALL_PROFILES_ID = '__all__';

	const statusLabel: Record<string, string> = {
		active: 'aktiv',
		inactive: 'nicht aktiv',
		failed: 'mit fehler abgebrochen',
		not_started: 'nicht gestartet'
	};

	function statusClasses(status: string): string {
		if (status === 'active') return 'bg-accent/10 text-accent border-accent/30';
		if (status === 'inactive') return 'bg-text-muted/10 text-text-secondary border-border';
		if (status === 'failed') return 'bg-error/10 text-error border-error/30';
		return 'bg-warning/10 text-warning border-warning/30';
	}

	function formatTime(ts: number | null): string {
		if (!ts) return '-';
		return new Date(ts * 1000).toLocaleTimeString();
	}

	function scriptPriority(entry: ScriptEntry): number {
		const key = `${entry.name} ${entry.path}`.toLowerCase();
		if (key.includes('health_check') || key.includes('health-check')) return 0;
		if (key.includes('suite')) return 1;
		return 2;
	}

	function scriptHasKnownProfileSuffix(script: ScriptEntry, profiles: ModelProfile[]): boolean {
		const lowerPath = script.path.toLowerCase();
		return profiles.some((profile) => lowerPath.endsWith(`.${profile.script_suffix.toLowerCase()}.sh`));
	}

	function applyProfileFilter(allScripts: ScriptEntry[], profiles: ModelProfile[], profileId: string): ScriptEntry[] {
		if (!profileId || profileId === ALL_PROFILES_ID) return allScripts;
		const selected = profiles.find((p) => p.id === profileId);
		if (!selected) return allScripts;

		const selectedSuffix = `.${selected.script_suffix.toLowerCase()}.sh`;
		const filtered = allScripts.filter((script) => script.path.toLowerCase().endsWith(selectedSuffix));
		const fallbackGenericScripts = allScripts.filter((script) => !scriptHasKnownProfileSuffix(script, profiles));
		const scriptsForProfile = filtered.length > 0 ? filtered : fallbackGenericScripts;

		return scriptsForProfile.sort((a, b) => {
			const prio = scriptPriority(a) - scriptPriority(b);
			if (prio !== 0) return prio;
			return a.name.localeCompare(b.name);
		});
	}

	function effectiveProfileIdForScript(script: ScriptEntry): string {
		if (selectedModelProfileId && selectedModelProfileId !== ALL_PROFILES_ID) {
			return selectedModelProfileId;
		}
		return script.default_model_profile_id ?? modelProfiles[0]?.id ?? '';
	}

	function relevantRunsForSelection(allRuns: RunEntry[], filteredScripts: ScriptEntry[], profileId: string): RunEntry[] {
		const visiblePaths = new Set(filteredScripts.map((script) => script.path));
		return allRuns.filter((run) => {
			if (!visiblePaths.has(run.script_path)) return false;
			if (!profileId || profileId === ALL_PROFILES_ID) return true;
			return run.model_profile_id === profileId;
		});
	}

	function sameScriptList(left: ScriptEntry[], right: ScriptEntry[]): boolean {
		if (left.length !== right.length) return false;
		return left.every((entry, index) => entry.path === right[index]?.path);
	}

	function resetRuleShieldLive() {
		selectedRunRuleShield = null;
		shadowEnabled = false;
		shadowComparisons = 0;
		activeRules = 0;
		confidenceUp = 0;
		confidenceDown = 0;
		latestRuleEvents = [];
	}

	function normalizeApiBase(input: string): string {
		return input.trim().replace(/\/+$/, '');
	}

	async function isReachableApiBase(base: string): Promise<boolean> {
		try {
			const res = await fetch(`${base}/health`);
			return res.ok;
		} catch {
			return false;
		}
	}

	async function resolveApiBase(): Promise<string> {
		const candidates = [getGatewayBaseClient(), DEFAULT_GATEWAY_BASE]
			.filter((value): value is string => Boolean(value))
			.map(normalizeApiBase);

		for (const candidate of candidates) {
			if (await isReachableApiBase(candidate)) {
				if (typeof localStorage !== 'undefined') {
					localStorage.setItem(GATEWAY_BASE_STORAGE_KEY, candidate);
				}
				return candidate;
			}
		}

		return DEFAULT_GATEWAY_BASE;
	}

	async function getJSON(path: string, fallback: any) {
		try {
			const res = await fetch(`${apiBase}${path}`);
			if (!res.ok) return fallback;
			return await res.json();
		} catch {
			return fallback;
		}
	}

	async function postJSON(path: string, body: Record<string, string>) {
		const res = await fetch(`${apiBase}${path}`, {
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
		const [scriptsData, runsData, profileData] = await Promise.all([
			getJSON('/api/test-monitor/scripts', { scripts: [] }),
			getJSON('/api/test-monitor/runs?limit=60', { runs: [] }),
			getJSON('/api/test-monitor/model-profiles', { profiles: [], default_profile_id: '' })
		]);
		scripts = (scriptsData.scripts ?? []).sort((a: ScriptEntry, b: ScriptEntry) => {
			const prio = scriptPriority(a) - scriptPriority(b);
			if (prio !== 0) return prio;
			return a.name.localeCompare(b.name);
		});
		runs = runsData.runs ?? [];
		modelProfiles = profileData.profiles ?? [];
		if (!selectedModelProfileId) {
			const storedProfile =
				typeof localStorage !== 'undefined' ? localStorage.getItem(PROFILE_STORAGE_KEY) : null;
			selectedModelProfileId =
				storedProfile ??
				profileData.default_profile_id ??
				scripts[0]?.default_model_profile_id ??
				modelProfiles[0]?.id ??
				'';
		}
		if (
			selectedModelProfileId &&
			selectedModelProfileId !== ALL_PROFILES_ID &&
			!modelProfiles.some((p) => p.id === selectedModelProfileId)
		) {
			selectedModelProfileId =
				profileData.default_profile_id ?? scripts[0]?.default_model_profile_id ?? modelProfiles[0]?.id ?? '';
		}

		if (lastSelectedModelProfileId && selectedModelProfileId !== lastSelectedModelProfileId) {
			selectedRunId = '';
			selectedRunEvents = [];
			selectedRunStatus = '';
			resetRuleShieldLive();
		}
		lastSelectedModelProfileId = selectedModelProfileId;

		visibleScripts = applyProfileFilter(scripts, modelProfiles, selectedModelProfileId);
		const relevantRuns = relevantRunsForSelection(runs, visibleScripts, selectedModelProfileId);

		const selectedRunVisible = relevantRuns.some((run) => run.run_id === selectedRunId);
		const keepPinnedSelection = Date.now() < selectedRunPinnedUntil;
		if (selectedRunId && !selectedRunVisible && !keepPinnedSelection) {
			selectedRunId = '';
			selectedRunEvents = [];
			selectedRunStatus = '';
			resetRuleShieldLive();
		}

		if (selectedRunId) {
			resetRuleShieldLive();
			const [eventsData, runRuleShieldData] = await Promise.all([
				getJSON(`/api/test-monitor/runs/${selectedRunId}/events?limit=700`, {
					events: [],
					status: ''
				}),
				getJSON(`/api/test-monitor/runs/${selectedRunId}/ruleshield`, {})
			]);
			selectedRunEvents = eventsData.events ?? [];
			selectedRunStatus = eventsData.status ?? '';
			if (runRuleShieldData?.available) {
				selectedRunRuleShield = {
					available: true,
					triggered_rules: Number(runRuleShieldData.triggered_rules ?? 0),
					would_trigger_shadow: Number(runRuleShieldData.would_trigger_shadow ?? 0),
					cost_without: Number(runRuleShieldData.cost_without ?? 0),
					cost_with: Number(runRuleShieldData.cost_with ?? 0),
					savings_usd: Number(runRuleShieldData.savings_usd ?? 0),
					savings_pct: Number(runRuleShieldData.savings_pct ?? 0),
					shadow_enabled: Boolean(runRuleShieldData.shadow_enabled),
					confidence_up: Number(runRuleShieldData.confidence_up ?? 0),
					confidence_down: Number(runRuleShieldData.confidence_down ?? 0),
					recent_rule_events: (runRuleShieldData.recent_rule_events ?? []).slice(0, 8)
				};
				shadowEnabled = selectedRunRuleShield.shadow_enabled;
				shadowComparisons = selectedRunRuleShield.would_trigger_shadow;
				activeRules = selectedRunRuleShield.triggered_rules;
				confidenceUp = selectedRunRuleShield.confidence_up;
				confidenceDown = selectedRunRuleShield.confidence_down;
				latestRuleEvents = selectedRunRuleShield.recent_rule_events;
			} else {
				resetRuleShieldLive();
			}
		} else {
			selectedRunEvents = [];
			selectedRunStatus = '';
			resetRuleShieldLive();
		}
	}

	async function startScript(scriptPath: string) {
		error = '';
		busyPath = scriptPath;
		try {
			const response = await postJSON('/api/test-monitor/start', {
				script_path: scriptPath,
				model_profile_id: effectiveProfileIdForScript(scripts.find((script) => script.path === scriptPath) ?? {
					path: scriptPath,
					name: '',
					type: 'shell',
					status: 'not_started',
					active_run_id: null,
					last_run_id: null,
					last_return_code: null
				})
			});
			selectedRunId = response.run_id;
			selectedRunPinnedUntil = Date.now() + 15000;
			selectedRunStatus = 'active';
			resetRuleShieldLive();
			const [eventsData, runRuleShieldData] = await Promise.all([
				getJSON(`/api/test-monitor/runs/${response.run_id}/events?limit=700`, {
					events: [],
					status: 'active'
				}),
				getJSON(`/api/test-monitor/runs/${response.run_id}/ruleshield`, {})
			]);
			selectedRunEvents = eventsData.events ?? [];
			selectedRunStatus = eventsData.status ?? 'active';
			if (runRuleShieldData?.available) {
				selectedRunRuleShield = {
					available: true,
					triggered_rules: Number(runRuleShieldData.triggered_rules ?? 0),
					would_trigger_shadow: Number(runRuleShieldData.would_trigger_shadow ?? 0),
					cost_without: Number(runRuleShieldData.cost_without ?? 0),
					cost_with: Number(runRuleShieldData.cost_with ?? 0),
					savings_usd: Number(runRuleShieldData.savings_usd ?? 0),
					savings_pct: Number(runRuleShieldData.savings_pct ?? 0),
					shadow_enabled: Boolean(runRuleShieldData.shadow_enabled),
					confidence_up: Number(runRuleShieldData.confidence_up ?? 0),
					confidence_down: Number(runRuleShieldData.confidence_down ?? 0),
					recent_rule_events: (runRuleShieldData.recent_rule_events ?? []).slice(0, 8)
				};
				shadowEnabled = selectedRunRuleShield.shadow_enabled;
				shadowComparisons = selectedRunRuleShield.would_trigger_shadow;
				activeRules = selectedRunRuleShield.triggered_rules;
				confidenceUp = selectedRunRuleShield.confidence_up;
				confidenceDown = selectedRunRuleShield.confidence_down;
				latestRuleEvents = selectedRunRuleShield.recent_rule_events;
			}
			await loadData();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Start failed';
		} finally {
			busyPath = null;
		}
	}

	async function stopRun(runId: string, scriptPath: string) {
		error = '';
		busyPath = scriptPath;
		try {
			await postJSON('/api/test-monitor/stop', { run_id: runId });
			await loadData();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Stop failed';
		} finally {
			busyPath = null;
		}
	}

	onMount(() => {
		let alive = true;
		(async () => {
			apiBase = await resolveApiBase();
			await loadData();
			if (alive) loading = false;
		})();

		const interval = setInterval(async () => {
			await loadData();
		}, 2000);

		return () => {
			alive = false;
			clearInterval(interval);
		};
	});

	$effect(() => {
		if (selectedModelProfileId && typeof localStorage !== 'undefined') {
			localStorage.setItem(PROFILE_STORAGE_KEY, selectedModelProfileId);
		}
		const nextVisibleScripts = applyProfileFilter(scripts, modelProfiles, selectedModelProfileId);
		if (!sameScriptList(visibleScripts, nextVisibleScripts)) {
			visibleScripts = nextVisibleScripts;
		}
		const relevantRuns = relevantRunsForSelection(runs, nextVisibleScripts, selectedModelProfileId);
		const nextSelectedRunId =
			selectedRunId &&
			(relevantRuns.some((run) => run.run_id === selectedRunId) || Date.now() < selectedRunPinnedUntil)
				? selectedRunId
				: '';
		if (nextSelectedRunId !== selectedRunId) {
			selectedRunId = nextSelectedRunId;
		}
	});

	$effect(() => {
		selectedRunId;
		selectedRunEvents.length;
		const lastEvent = selectedRunEvents.at(-1);
		const fingerprint = `${selectedRunId}|${selectedRunEvents.length}|${lastEvent?.ts ?? 0}|${lastEvent?.kind ?? ''}|${lastEvent?.text ?? ''}`;
		if (fingerprint === lastLogFingerprint) return;
		lastLogFingerprint = fingerprint;
		void tick().then(() => {
			if (logPanel) {
				logPanel.scrollTop = logPanel.scrollHeight;
			}
		});
	});
</script>

<svelte:head>
	<title>Test Monitor</title>
</svelte:head>

<div class="h-screen overflow-auto bg-[#0B0D12] px-6 py-6 text-text-primary">
	<div class="mx-auto flex max-w-7xl flex-col">
		<header class="mb-4 flex items-end justify-between border-b border-border pb-4">
			<div>
				<p class="text-xs uppercase tracking-[0.18em] text-text-muted">Ruleshield Monitoring</p>
				<h1 class="text-2xl font-bold">Rule Training</h1>
				<p class="mt-1 text-sm text-text-secondary">
					Start and stop scripts while monitoring prompt and response logs live.
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
			<div class="mb-3 rounded-lg border border-error/30 bg-error/10 px-3 py-2 text-sm text-error">{error}</div>
		{/if}

		<div class="grid min-w-0 gap-5 md:grid-cols-3 md:items-start">
			<section class="flex min-h-0 min-w-0 flex-col rounded-xl border border-border bg-surface p-4 md:col-span-1 md:max-h-[calc(100vh-10rem)]">
				<h2 class="mb-3 text-sm font-semibold uppercase tracking-wider text-text-muted">Test Scripts</h2>
				<div class="mb-3 rounded-md border border-border bg-surface-elevated/40 px-3 py-2 text-xs">
					<label class="mb-1 block text-[11px] uppercase tracking-wider text-text-muted" for="model-profile">
						Model / Provider Profile
					</label>
					<select
						id="model-profile"
						class="w-full rounded border border-border bg-[#0A0C10] px-2 py-1.5 text-xs text-text-secondary"
						bind:value={selectedModelProfileId}
					>
						<option value={ALL_PROFILES_ID}>Alle anzeigen</option>
						{#if modelProfiles.length === 0}
							<option value="">No model profiles</option>
						{:else}
							{#each modelProfiles as profile}
								<option value={profile.id}>{profile.label} · {profile.model}</option>
							{/each}
						{/if}
					</select>
					<p class="mt-1 text-[11px] text-text-muted">
						Vorbereitung für profil-spezifische Testfiles aktiv (Fallback auf aktuelle Files).
					</p>
				</div>
				<div class="max-h-[42rem] overflow-auto pr-1 md:max-h-[calc(100vh-20rem)]">
					{#if loading}
						<p class="text-sm text-text-muted">Loading…</p>
					{:else if visibleScripts.length === 0}
						<p class="text-sm text-text-muted">No test scripts found in `tests/` or `demo/`.</p>
					{:else}
							<div class="space-y-2">
								{#each visibleScripts as script}
									<div class="rounded-md border border-border bg-surface-elevated/50 px-3 py-3 text-xs">
										<p class="font-mono text-text-secondary">{script.name}</p>
										<div class="mt-3 flex items-center gap-2">
											<button
												class="rounded border border-accent/30 bg-accent/10 px-2.5 py-1 text-[11px] text-accent disabled:opacity-50"
												disabled={busyPath === script.path || script.status === 'active'}
												onclick={() => startScript(script.path)}
										>
											Start
										</button>
										<button
											class="rounded border border-error/30 bg-error/10 px-2.5 py-1 text-[11px] text-error disabled:opacity-50"
											disabled={busyPath === script.path || !script.active_run_id}
											onclick={() => script.active_run_id && stopRun(script.active_run_id, script.path)}
										>
											Stop
										</button>
										{#if script.last_run_id}
											<button
												class="rounded border border-border bg-surface px-2.5 py-1 text-[11px] text-text-secondary"
												onclick={() => (selectedRunId = script.last_run_id ?? '')}
											>
													Monitor
												</button>
											{/if}
											<span class={`ml-auto rounded border px-2 py-0.5 ${statusClasses(script.status)}`}>
												{statusLabel[script.status] ?? script.status}
											</span>
										</div>
									</div>
								{/each}
							</div>
					{/if}
				</div>
			</section>

			<div class="grid min-h-0 min-w-0 gap-5 md:col-span-2 md:max-h-[calc(100vh-10rem)] md:grid-rows-2">
				<section class="flex min-h-0 min-w-0 flex-col rounded-xl border border-border bg-surface p-4 md:overflow-hidden">
					<h2 class="mb-3 text-sm font-semibold uppercase tracking-wider text-text-muted">RuleShield Live</h2>
					<div class="grid gap-3 md:grid-cols-2">
						<div class="rounded-md border border-border bg-surface-elevated/40 px-3 py-2">
							<p class="text-[11px] uppercase tracking-wider text-text-muted">Shadow</p>
							<p class={`mt-1 text-sm font-semibold ${selectedRunRuleShield ? (shadowEnabled ? 'text-accent' : 'text-error') : 'text-text-muted'}`}>
								{selectedRunRuleShield ? (shadowEnabled ? 'active' : 'inactive') : '-'}
							</p>
						</div>
						<div class="rounded-md border border-border bg-surface-elevated/40 px-3 py-2">
							<p class="text-[11px] uppercase tracking-wider text-text-muted">Would Trigger (Shadow)</p>
							<p class="mt-1 text-sm font-semibold text-text-secondary">{shadowComparisons}</p>
						</div>
						<div class="rounded-md border border-border bg-surface-elevated/40 px-3 py-2">
							<p class="text-[11px] uppercase tracking-wider text-text-muted">Triggered Rules</p>
							<p class="mt-1 text-sm font-semibold text-text-secondary">
								{activeRules}
							</p>
						</div>
						<div class="rounded-md border border-border bg-surface-elevated/40 px-3 py-2">
							<p class="text-[11px] uppercase tracking-wider text-text-muted">Run Savings</p>
							<p class="mt-1 text-sm font-semibold text-text-secondary">
								{#if selectedRunRuleShield}
									${selectedRunRuleShield.savings_usd.toFixed(4)} ({selectedRunRuleShield.savings_pct.toFixed(1)}%)
								{:else}
									$0.0000 (0.0%)
								{/if}
							</p>
						</div>
					</div>
					{#if selectedRunRuleShield}
						<p class="mt-2 text-[11px] text-text-muted">
							Run cost with RuleShield: ${selectedRunRuleShield.cost_with.toFixed(4)} ·
							without RuleShield: ${selectedRunRuleShield.cost_without.toFixed(4)}
						</p>
					{:else}
						<p class="mt-2 text-[11px] text-text-muted">
							No RuleShield run data for the selected test yet.
						</p>
					{/if}
					{#if latestRuleEvents.length > 0}
						<div class="mt-3 min-h-0 min-w-0 flex-1 overflow-auto rounded-md border border-border bg-[#0A0C10] p-3 font-mono text-[12px]">
							{#each latestRuleEvents as event}
								<div class="mb-1 flex gap-2 text-text-secondary">
									<span class="text-text-muted">{event.created_at ?? '-'}</span>
									<span class="text-accent">{event.event_type ?? 'event'}</span>
									<span>{event.rule_id ?? '-'}</span>
									{#if event.event_type === 'confidence_update'}
										<span class={event.details?.direction === 'up' ? 'text-accent' : 'text-warning'}>
											{event.details?.previous_confidence ?? '?'} → {event.details?.new_confidence ?? '?'}
										</span>
									{/if}
								</div>
							{/each}
						</div>
					{/if}
				</section>

				<section class="flex min-h-0 min-w-0 flex-col rounded-xl border border-border bg-surface p-4 md:overflow-hidden">
					<div class="mb-3 flex items-center justify-between">
						<h2 class="text-sm font-semibold uppercase tracking-wider text-text-muted">Prompt Monitor</h2>
						<div class="min-w-0 text-xs text-text-muted">
							Run: <span class="font-mono text-text-secondary">{selectedRunId || '-'}</span>
							{#if selectedRunStatus}
								<span class={`ml-2 rounded border px-2 py-0.5 ${statusClasses(selectedRunStatus)}`}>
									{statusLabel[selectedRunStatus] ?? selectedRunStatus}
								</span>
							{/if}
						</div>
					</div>
					{#if selectedRunEvents.length === 0}
						<p class="text-sm text-text-muted">Noch keine Logs für den ausgewählten Run.</p>
					{:else}
						<div
							bind:this={logPanel}
							class="min-h-0 min-w-0 flex-1 overflow-auto rounded-md border border-border bg-[#0A0C10] p-3 font-mono text-[12px]"
						>
							{#each selectedRunEvents as event}
								<div class="mb-1 flex gap-2">
									<span class="text-text-muted">[{formatTime(event.ts)}]</span>
									<span class={event.kind === 'input' ? 'text-primary' : 'text-accent'}>
										{event.kind === 'input' ? 'IN' : 'OUT'}
									</span>
									<span class="whitespace-pre-wrap break-words text-text-secondary">{event.text}</span>
								</div>
							{/each}
						</div>
					{/if}
				</section>
			</div>
		</div>
	</div>
</div>
