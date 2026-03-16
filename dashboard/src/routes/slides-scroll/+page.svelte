<script lang="ts">
	const sections = [
		{
			kicker: 'Hermes Agent Hackathon 2026',
			title: 'RuleShield',
			subtitle: 'The Agent That Optimizes Itself',
			body: 'A scrollable presentation version, styled like the landing page.'
		},
		{
			kicker: 'Slide 2',
			title: 'The Problem',
			subtitle: '$420.69 / month on repetitive calls',
			body: 'Many prompts are repeated patterns like greetings, status checks, and confirmations.'
		},
		{
			kicker: 'Slide 3',
			title: 'How RuleShield saves YOU money',
			subtitle: 'Reduce paid calls before they happen',
			body: 'Cache hits and rule responses can return at zero cost, while smart routing sends easy tasks to cheaper models.'
		},
		{
			kicker: 'Slide 4',
			title: 'RuleShield Intelligence Pipeline',
			subtitle: 'Intercept before the expensive call',
			body: 'Cache -> Rules -> Bridge -> Router -> LLM.'
		},
		{
			kicker: 'Slide 5',
			title: 'Two-Command Setup',
			subtitle: 'Fast local start',
			body: 'npm run setup:hermes\nnpm run start'
		},
		{
			kicker: 'Slide 6',
			title: 'Model-Aware Intelligence',
			subtitle: 'Not all requests deserve the same model',
			body: 'Simple intent can be handled by rules or cheaper model paths, complex requests still use stronger models.'
		},
		{
			kicker: 'Slide 7',
			title: 'Deep Hermes Integration',
			subtitle: 'Skill + MCP + feedback loop',
			body: 'RuleShield integrates into Hermes workflows and enables iterative optimization.'
		},
		{
			kicker: 'Slide 8',
			title: 'Self-Evolution Path',
			subtitle: 'Now -> Next -> Future',
			body: 'From optimization and monitoring toward adaptive, self-improving behavior.'
		},
		{
			kicker: 'Slide 9',
			title: 'Architecture',
			subtitle: 'Hermes Agent + RuleShield Proxy + Dashboard',
			body: 'One clear control layer between your agent and upstream models.'
		},
		{
			kicker: 'Slide 10',
			title: 'Try it now',
			subtitle: 'Two commands to start',
			body: 'npm run setup:hermes\nnpm run start'
		}
	];
</script>

<svelte:head>
	<title>RuleShield - Scroll Presentation</title>
	<meta
		name="description"
		content="Scrollable RuleShield presentation with landing-page look and feel."
	/>
</svelte:head>

<div class="min-h-screen bg-[#0A0A0F] text-text-primary">
	<div class="pointer-events-none fixed inset-0 overflow-hidden">
		<div class="absolute left-1/2 top-[-180px] h-[560px] w-[860px] -translate-x-1/2 rounded-full bg-primary/[0.08] blur-[130px]"></div>
		<div class="absolute bottom-[-140px] right-[10%] h-[420px] w-[520px] rounded-full bg-accent/[0.08] blur-[120px]"></div>
	</div>

	<header class="sticky top-0 z-20 border-b border-border/70 bg-[#0A0A0F]/80 backdrop-blur-xl">
		<div class="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
			<a href="/home" class="flex items-center gap-2">
				<div class="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent text-sm font-bold text-white">R</div>
				<span class="text-base font-bold">Rule<span class="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">Shield</span></span>
			</a>
			<div class="flex items-center gap-3">
				<a href="/slides" class="rounded-md border border-border px-3 py-1.5 text-xs text-text-muted hover:text-text-primary">Classic Slides</a>
				<a href="/home" class="rounded-md border border-border px-3 py-1.5 text-xs text-text-muted hover:text-text-primary">All Pages</a>
			</div>
		</div>
	</header>

	<main class="relative z-10 mx-auto max-w-6xl px-6 py-10">
		<div class="mb-8 rounded-xl border border-border bg-surface p-5">
			<p class="text-xs uppercase tracking-[0.2em] text-text-muted">Scrollable Deck</p>
			<h1 class="mt-2 text-3xl font-extrabold sm:text-4xl">RuleShield Presentation (Landing Style)</h1>
			<p class="mt-3 text-sm text-text-secondary">This page mirrors the slide content in a vertical, record-friendly flow.</p>
		</div>

		<div class="space-y-6">
			{#each sections as section, idx}
				<section class="rounded-2xl border border-border bg-surface p-7 sm:p-10">
					<div class="mb-4 inline-flex items-center gap-2 rounded-full border border-border px-3 py-1">
						<div class="h-2 w-2 rounded-full bg-accent"></div>
						<span class="text-[11px] font-medium uppercase tracking-[0.16em] text-text-muted">{section.kicker}</span>
					</div>
					<h2 class="text-2xl font-bold sm:text-4xl">{section.title}</h2>
					<p class="mt-2 text-base text-accent sm:text-xl">{section.subtitle}</p>
					{#if section.body.includes('\n')}
						<pre class="mt-5 overflow-x-auto rounded-lg border border-border bg-[#090B15] px-4 py-3 font-mono text-sm text-accent">{section.body}</pre>
					{:else}
						<p class="mt-4 max-w-3xl text-base leading-relaxed text-text-secondary">{section.body}</p>
					{/if}
					<div class="mt-6 text-xs text-text-muted">Section {idx + 1} / {sections.length}</div>
				</section>
			{/each}
		</div>
	</main>
</div>
