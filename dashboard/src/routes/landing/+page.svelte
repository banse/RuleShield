<script lang="ts">
	let scrollY = $state(0);
	let navScrolled = $state(false);
	let mobileMenuOpen = $state(false);

	// Animated counter states
	let savingsCount = $state(0);
	let heroVisible = $state(false);
	let problemVisible = $state(false);
	let layersVisible = $state(false);
	let matrixVisible = $state(false);
	let shadowVisible = $state(false);
	let integrationVisible = $state(false);
	let resultsVisible = $state(false);
	let pricingVisible = $state(false);
	let roadmapVisible = $state(false);
	let ctaVisible = $state(false);

	$effect(() => {
		const handleScroll = () => {
			scrollY = window.scrollY;
			navScrolled = scrollY > 20;
		};
		window.addEventListener('scroll', handleScroll, { passive: true });
		return () => window.removeEventListener('scroll', handleScroll);
	});

	// IntersectionObserver for scroll-triggered animations
	$effect(() => {
		const observer = new IntersectionObserver(
			(entries) => {
				entries.forEach((entry) => {
					if (entry.isIntersecting) {
						const id = entry.target.getAttribute('data-section');
						if (id === 'hero') heroVisible = true;
						if (id === 'problem') problemVisible = true;
						if (id === 'layers') layersVisible = true;
						if (id === 'matrix') matrixVisible = true;
						if (id === 'shadow') shadowVisible = true;
						if (id === 'integration') integrationVisible = true;
						if (id === 'results') resultsVisible = true;
						if (id === 'pricing') pricingVisible = true;
						if (id === 'roadmap') roadmapVisible = true;
						if (id === 'cta') ctaVisible = true;
					}
				});
			},
			{ threshold: 0.15 }
		);

		const sections = document.querySelectorAll('[data-section]');
		sections.forEach((s) => observer.observe(s));
		return () => observer.disconnect();
	});

	// Animated savings counter
	$effect(() => {
		if (!heroVisible) return;
		const target = 12847;
		const duration = 2000;
		const start = performance.now();

		function tick(now: number) {
			const elapsed = now - start;
			const progress = Math.min(elapsed / duration, 1);
			const eased = 1 - Math.pow(1 - progress, 3);
			savingsCount = Math.round(target * eased);
			if (progress < 1) requestAnimationFrame(tick);
		}
		requestAnimationFrame(tick);
	});

	function scrollTo(id: string) {
		mobileMenuOpen = false;
		const el = document.getElementById(id);
		if (el) el.scrollIntoView({ behavior: 'smooth' });
	}

	function formatMoney(n: number): string {
		return n.toLocaleString('en-US');
	}

	const navLinks = [
		{ label: 'Features', id: 'features' },
		{ label: 'Pricing', id: 'pricing' },
		{ label: 'Docs', href: '#' },
		{ label: 'GitHub', href: 'https://github.com/ruleshield' }
	];
</script>

<svelte:head>
	<title>RuleShield Hermes - One Line of Code. 80% Less LLM Cost.</title>
	<meta name="description" content="Drop-in LLM cost optimizer. Semantic caching, auto-learned rules, and smart routing. One import, up to 82% savings." />
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
	<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
</svelte:head>

<!-- ===== NAV BAR ===== -->
<nav
	class="fixed top-0 left-0 right-0 z-50 transition-all duration-300"
	class:nav-scrolled={navScrolled}
>
	<div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
		<button onclick={() => scrollTo('hero')} class="flex items-center gap-2 group cursor-pointer">
			<div class="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center text-white font-bold text-sm">R</div>
			<span class="text-lg font-bold text-text-primary">Rule<span class="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">Shield</span></span>
		</button>

		<!-- Desktop nav -->
		<div class="hidden md:flex items-center gap-8">
			{#each navLinks as link}
				{#if link.id}
					<button onclick={() => scrollTo(link.id)} class="text-sm text-text-secondary hover:text-text-primary transition-colors cursor-pointer">{link.label}</button>
				{:else}
					<a href={link.href} class="text-sm text-text-secondary hover:text-text-primary transition-colors">{link.label}</a>
				{/if}
			{/each}
			<button onclick={() => scrollTo('cta')} class="btn-primary text-sm px-5 py-2">Get Started</button>
		</div>

		<!-- Mobile hamburger -->
		<button class="md:hidden text-text-primary cursor-pointer" onclick={() => (mobileMenuOpen = !mobileMenuOpen)}>
			<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				{#if mobileMenuOpen}
					<path d="M18 6L6 18M6 6l12 12" />
				{:else}
					<path d="M3 12h18M3 6h18M3 18h18" />
				{/if}
			</svg>
		</button>
	</div>

	<!-- Mobile menu -->
	{#if mobileMenuOpen}
		<div class="md:hidden bg-surface/95 backdrop-blur-xl border-t border-border">
			<div class="px-6 py-4 flex flex-col gap-4">
				{#each navLinks as link}
					{#if link.id}
						<button onclick={() => scrollTo(link.id)} class="text-left text-text-secondary hover:text-text-primary transition-colors cursor-pointer">{link.label}</button>
					{:else}
						<a href={link.href} class="text-text-secondary hover:text-text-primary transition-colors">{link.label}</a>
					{/if}
				{/each}
				<button onclick={() => scrollTo('cta')} class="btn-primary text-sm px-5 py-2.5 w-full">Get Started</button>
			</div>
		</div>
	{/if}
</nav>

<main class="overflow-x-hidden">
	<!-- ===== HERO ===== -->
	<section id="hero" data-section="hero" class="relative pt-32 pb-24 px-6">
		<!-- Background glow effects -->
		<div class="absolute inset-0 overflow-hidden pointer-events-none">
			<div class="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-primary/5 rounded-full blur-[120px]"></div>
			<div class="absolute top-1/3 left-1/3 w-[400px] h-[400px] bg-accent/5 rounded-full blur-[100px]"></div>
		</div>

		<div class="max-w-5xl mx-auto text-center relative z-10">
			<div class="transition-all duration-700 {heroVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}">
				<!-- Overline -->
				<div class="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-border bg-surface/50 backdrop-blur-sm mb-8">
					<div class="w-2 h-2 rounded-full bg-accent animate-pulse"></div>
					<span class="text-xs font-medium tracking-widest text-text-muted uppercase">Drop-in LLM Cost Optimizer</span>
				</div>

				<!-- Headline -->
				<h1 class="text-5xl sm:text-6xl lg:text-7xl font-extrabold leading-tight mb-6">
					<span class="text-text-primary">One line of code.</span><br />
					<span class="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">80% less LLM cost.</span>
				</h1>

				<!-- Subheadline -->
				<p class="text-lg sm:text-xl text-text-secondary max-w-2xl mx-auto mb-10 leading-relaxed">
					RuleShield sits between your app and any LLM API.
					Semantic caching, auto-learned rules, and smart routing —
					no code changes beyond the import.
				</p>

				<!-- CTAs -->
				<div class="flex flex-col sm:flex-row items-center justify-center gap-4 mb-10">
					<button onclick={() => scrollTo('cta')} class="btn-primary text-base px-8 py-3.5 w-full sm:w-auto">
						Start Free
						<svg class="inline-block ml-2 w-4 h-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 8h10M9 4l4 4-4 4"/></svg>
					</button>
					<a href="/slides" class="btn-ghost text-base px-8 py-3.5 w-full sm:w-auto text-center">
						View Demo
					</a>
				</div>

				<!-- Trust bar -->
				<div class="flex items-center justify-center gap-2 text-sm text-text-muted mb-16">
					<svg class="w-4 h-4 text-accent" viewBox="0 0 16 16" fill="currentColor"><path d="M8 0l2.09 5.27L16 6.18l-4.18 3.64L13.18 16 8 12.72 2.82 16l1.36-6.18L0 6.18l5.91-.91z"/></svg>
					<span>Proven <strong class="text-accent">47-82% savings</strong> across 4 test scenarios</span>
				</div>
			</div>

			<!-- Code comparison -->
			<div class="transition-all duration-700 delay-300 {heroVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-12'}">
				<div class="max-w-3xl mx-auto bg-surface rounded-2xl border border-border overflow-hidden shadow-2xl shadow-primary/5">
					<div class="grid grid-cols-1 sm:grid-cols-2 divide-y sm:divide-y-0 sm:divide-x divide-border">
						<!-- Before -->
						<div class="p-6">
							<div class="flex items-center gap-2 mb-4">
								<div class="w-3 h-3 rounded-full bg-error/60"></div>
								<span class="text-xs font-medium text-text-muted uppercase tracking-wider">Before</span>
							</div>
							<pre class="font-mono text-sm text-text-secondary leading-relaxed"><code><span class="text-text-muted">from</span> <span class="text-error/80">openai</span> <span class="text-text-muted">import</span> OpenAI

client = OpenAI()
<span class="text-text-muted"># Every call hits the API</span>
<span class="text-text-muted"># $$$$ per month</span></code></pre>
						</div>

						<!-- After -->
						<div class="p-6 bg-accent/[0.02]">
							<div class="flex items-center gap-2 mb-4">
								<div class="w-3 h-3 rounded-full bg-accent"></div>
								<span class="text-xs font-medium text-accent uppercase tracking-wider">After</span>
							</div>
							<pre class="font-mono text-sm text-text-secondary leading-relaxed"><code><span class="text-text-muted">from</span> <span class="text-accent">ruleshield</span> <span class="text-text-muted">import</span> OpenAI

client = OpenAI()
<span class="text-text-muted"># Identical API. Smart routing.</span>
<span class="text-text-muted"># 80% less cost.</span></code></pre>
						</div>
					</div>

					<!-- Savings counter -->
					<div class="border-t border-border bg-surface-elevated/50 px-6 py-5 flex flex-col sm:flex-row items-center justify-between gap-4">
						<span class="text-sm text-text-muted">Estimated monthly savings</span>
						<div class="flex items-center gap-2">
							<span class="text-3xl font-bold text-accent font-mono tabular-nums">${formatMoney(savingsCount)}</span>
							<span class="text-xs text-text-muted">/month</span>
						</div>
					</div>
				</div>
			</div>
		</div>
	</section>

	<!-- ===== PROBLEM SECTION ===== -->
	<section id="problem" data-section="problem" class="py-24 px-6 relative">
		<div class="max-w-5xl mx-auto">
			<div class="text-center mb-16 transition-all duration-700 {problemVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}">
				<h2 class="text-3xl sm:text-4xl font-bold text-text-primary mb-4">You're burning money on repeat questions.</h2>
				<p class="text-lg text-text-secondary max-w-xl mx-auto">Most LLM API calls are predictable. But every one costs the same.</p>
			</div>

			<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
				{#each [
					{ icon: '🔄', stat: '60-80%', title: 'Repetitive Requests', desc: 'Most LLM calls ask questions that have already been answered. You pay full price every time.' },
					{ icon: '💸', stat: '$$$', title: 'Every Call Costs the Same', desc: 'Simple lookups cost as much as complex reasoning. No intelligence in your billing.' },
					{ icon: '🔍', stat: '0%', title: 'Zero Visibility', desc: 'No insight into which requests are repetitive, which could be cached, or which need a cheaper model.' }
				] as card, i}
					<div
						class="pain-card group transition-all duration-700"
						style="transition-delay: {i * 150}ms"
						class:opacity-100={problemVisible}
						class:translate-y-0={problemVisible}
						class:opacity-0={!problemVisible}
						class:translate-y-8={!problemVisible}
					>
						<div class="text-4xl mb-4">{card.icon}</div>
						<div class="text-2xl font-bold text-accent mb-2 font-mono">{card.stat}</div>
						<h3 class="text-lg font-semibold text-text-primary mb-2">{card.title}</h3>
						<p class="text-sm text-text-secondary leading-relaxed">{card.desc}</p>
					</div>
				{/each}
			</div>

			<p class="text-center text-xl font-semibold text-text-primary mt-16 transition-all duration-700 delay-500 {problemVisible ? 'opacity-100' : 'opacity-0'}">
				RuleShield learns what <span class="text-accent">doesn't need an LLM</span>.
			</p>
		</div>
	</section>

	<!-- ===== 4-LAYER INTELLIGENCE ===== -->
	<section id="features" data-section="layers" class="py-24 px-6 relative">
		<div class="absolute inset-0 overflow-hidden pointer-events-none">
			<div class="absolute top-1/2 left-0 w-[600px] h-[600px] bg-primary/3 rounded-full blur-[150px]"></div>
			<div class="absolute bottom-0 right-0 w-[500px] h-[500px] bg-accent/3 rounded-full blur-[120px]"></div>
		</div>

		<div class="max-w-5xl mx-auto relative z-10">
			<div class="text-center mb-16 transition-all duration-700 {layersVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}">
				<div class="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-primary/30 bg-primary/5 mb-6">
					<span class="text-xs font-medium text-primary">Core Architecture</span>
				</div>
				<h2 class="text-3xl sm:text-4xl font-bold text-text-primary mb-4">Four layers. One import.</h2>
				<p class="text-lg text-text-secondary max-w-xl mx-auto">Each layer catches what the previous one missed. Together, they eliminate up to 82% of LLM costs.</p>
			</div>

			<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
				{#each [
					{
						layer: '01',
						title: 'Semantic Cache',
						cost: '$0',
						color: 'accent',
						desc: 'Identical and similar requests answered from cache in <5ms. No LLM call needed.',
						stat: '73%',
						statLabel: 'Cache Hit Rate',
						icon: `<svg class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>`
					},
					{
						layer: '02',
						title: 'Rule Engine',
						cost: '$0',
						color: 'primary',
						desc: '75 auto-learned decision rules handle patterns with SAP-grade accuracy scoring.',
						stat: '97%',
						statLabel: 'Rule Accuracy',
						icon: `<svg class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2a10 10 0 100 20 10 10 0 000-20zm0 5v5l3 3"/></svg>`
					},
					{
						layer: '03',
						title: 'Hermes Bridge',
						cost: '$0.001',
						color: 'accent',
						desc: 'Local cheap model handles mid-complexity queries. 100x cheaper than cloud LLMs.',
						stat: '100x',
						statLabel: 'Cost Reduction',
						icon: `<svg class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18"/></svg>`
					},
					{
						layer: '04',
						title: 'Smart Router',
						cost: 'auto',
						color: 'primary',
						desc: 'Complexity-based model routing. Simple queries go to Haiku, complex ones to Opus.',
						stat: 'Auto',
						statLabel: 'Model Selection',
						icon: `<svg class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M16 3h5v5M4 20L21 3M21 16v5h-5M15 15l6 6M4 4l5 5"/></svg>`
					}
				] as layer, i}
					<div
						class="layer-card group transition-all duration-700"
						style="transition-delay: {i * 150}ms"
						class:opacity-100={layersVisible}
						class:translate-y-0={layersVisible}
						class:opacity-0={!layersVisible}
						class:translate-y-8={!layersVisible}
					>
						<div class="flex items-start justify-between mb-6">
							<div class="flex items-center gap-3">
								<div class="w-10 h-10 rounded-xl bg-{layer.color}/10 border border-{layer.color}/20 flex items-center justify-center text-{layer.color}">
									{@html layer.icon}
								</div>
								<div>
									<span class="text-[10px] font-mono text-text-muted uppercase tracking-widest">Layer {layer.layer}</span>
									<h3 class="text-lg font-semibold text-text-primary">{layer.title}</h3>
								</div>
							</div>
							<span class="font-mono text-sm font-bold {layer.color === 'accent' ? 'text-accent' : 'text-primary'}">{layer.cost}</span>
						</div>
						<p class="text-sm text-text-secondary leading-relaxed mb-6">{layer.desc}</p>
						<div class="flex items-center gap-3 pt-4 border-t border-border">
							<span class="text-2xl font-bold font-mono {layer.color === 'accent' ? 'text-accent' : 'text-primary'}">{layer.stat}</span>
							<span class="text-xs text-text-muted">{layer.statLabel}</span>
						</div>
					</div>
				{/each}
			</div>
		</div>
	</section>

	<!-- ===== MODEL-AWARE INTELLIGENCE ===== -->
	<section data-section="matrix" class="py-24 px-6">
		<div class="max-w-5xl mx-auto">
			<div class="text-center mb-16 transition-all duration-700 {matrixVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}">
				<h2 class="text-3xl sm:text-4xl font-bold text-text-primary mb-4">Model-Aware Intelligence</h2>
				<p class="text-lg text-text-secondary max-w-xl mx-auto">Expensive models get premium treatment. RuleShield knows which rules fire for each tier.</p>
			</div>

			<div class="transition-all duration-700 delay-200 {matrixVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}">
				<div class="bg-surface rounded-2xl border border-border overflow-hidden">
					<div class="overflow-x-auto">
						<table class="w-full text-sm">
							<thead>
								<tr class="border-b border-border">
									<th class="text-left px-6 py-4 text-text-muted font-medium">Layer</th>
									<th class="px-6 py-4 text-center">
										<span class="text-text-muted font-medium">Haiku</span>
										<span class="block text-[10px] text-text-muted/60 font-mono">$0.25/M</span>
									</th>
									<th class="px-6 py-4 text-center">
										<span class="text-text-muted font-medium">Sonnet</span>
										<span class="block text-[10px] text-text-muted/60 font-mono">$3/M</span>
									</th>
									<th class="px-6 py-4 text-center">
										<span class="text-text-muted font-medium">Opus</span>
										<span class="block text-[10px] text-text-muted/60 font-mono">$15/M</span>
									</th>
								</tr>
							</thead>
							<tbody>
								{#each [
									{ layer: 'Semantic Cache', haiku: true, sonnet: true, opus: true },
									{ layer: 'Rule Engine', haiku: true, sonnet: true, opus: false },
									{ layer: 'Hermes Bridge', haiku: false, sonnet: true, opus: true },
									{ layer: 'Smart Router', haiku: false, sonnet: false, opus: true }
								] as row, i}
									<tr class="border-b border-border/50 last:border-0 hover:bg-surface-elevated/50 transition-colors">
										<td class="px-6 py-4 font-medium text-text-primary">{row.layer}</td>
										<td class="px-6 py-4 text-center">{#if row.haiku}<span class="text-accent text-lg">&#10003;</span>{:else}<span class="text-text-muted/30">--</span>{/if}</td>
										<td class="px-6 py-4 text-center">{#if row.sonnet}<span class="text-accent text-lg">&#10003;</span>{:else}<span class="text-text-muted/30">--</span>{/if}</td>
										<td class="px-6 py-4 text-center">{#if row.opus}<span class="text-accent text-lg">&#10003;</span>{:else}<span class="text-text-muted/30">--</span>{/if}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</div>
			</div>
		</div>
	</section>

	<!-- ===== SHADOW MODE ===== -->
	<section data-section="shadow" class="py-24 px-6 relative">
		<div class="absolute inset-0 overflow-hidden pointer-events-none">
			<div class="absolute top-1/2 right-0 w-[500px] h-[500px] bg-accent/3 rounded-full blur-[150px]"></div>
		</div>

		<div class="max-w-5xl mx-auto relative z-10">
			<div class="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
				<div class="transition-all duration-700 {shadowVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}">
					<div class="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-accent/30 bg-accent/5 mb-6">
						<span class="text-xs font-medium text-accent">Zero Risk</span>
					</div>
					<h2 class="text-3xl sm:text-4xl font-bold text-text-primary mb-4">Prove savings before you commit.</h2>
					<p class="text-lg text-text-secondary mb-8 leading-relaxed">
						Shadow Mode runs parallel to your LLM. Same responses go to your users.
						You see what RuleShield <em>would have saved</em> — with zero risk.
					</p>
					<div class="flex flex-wrap gap-6">
						<div>
							<div class="text-2xl font-bold text-accent font-mono">14 days</div>
							<div class="text-xs text-text-muted mt-1">Average trial</div>
						</div>
						<div>
							<div class="text-2xl font-bold text-accent font-mono">94.7%</div>
							<div class="text-xs text-text-muted mt-1">Shadow accuracy</div>
						</div>
						<div>
							<div class="text-2xl font-bold text-accent font-mono">142</div>
							<div class="text-xs text-text-muted mt-1">Auto-learned rules</div>
						</div>
					</div>
				</div>

				<!-- Dashboard mockup -->
				<div class="transition-all duration-700 delay-300 {shadowVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-12'}">
					<div class="bg-surface rounded-2xl border border-border p-6 shadow-2xl shadow-accent/5">
						<div class="flex items-center justify-between mb-6">
							<div class="flex items-center gap-2">
								<div class="w-2 h-2 rounded-full bg-accent animate-pulse"></div>
								<span class="text-sm font-medium text-text-primary">Shadow Mode Active</span>
							</div>
							<span class="text-xs text-text-muted font-mono">14 days running</span>
						</div>
						<div class="grid grid-cols-3 gap-4 mb-6">
							<div class="bg-bg rounded-xl p-4 text-center">
								<div class="text-xl font-bold text-accent font-mono">$4,291</div>
								<div class="text-[10px] text-text-muted mt-1 uppercase tracking-wider">Saved</div>
							</div>
							<div class="bg-bg rounded-xl p-4 text-center">
								<div class="text-xl font-bold text-primary font-mono">142</div>
								<div class="text-[10px] text-text-muted mt-1 uppercase tracking-wider">Rules</div>
							</div>
							<div class="bg-bg rounded-xl p-4 text-center">
								<div class="text-xl font-bold text-accent font-mono">94.7%</div>
								<div class="text-[10px] text-text-muted mt-1 uppercase tracking-wider">Accuracy</div>
							</div>
						</div>
						<!-- Mini chart mock -->
						<div class="bg-bg rounded-xl p-4 mb-4">
							<div class="flex items-end justify-between h-16 gap-1">
								{#each [30, 45, 38, 55, 62, 48, 70, 65, 78, 72, 85, 80, 88, 92] as height}
									<div class="flex-1 bg-gradient-to-t from-accent/20 to-accent/60 rounded-sm" style="height: {height}%"></div>
								{/each}
							</div>
							<div class="flex justify-between mt-2">
								<span class="text-[10px] text-text-muted">Day 1</span>
								<span class="text-[10px] text-text-muted">Day 14</span>
							</div>
						</div>
						<button class="w-full py-2.5 rounded-lg bg-accent/10 border border-accent/20 text-accent text-sm font-medium hover:bg-accent/20 transition-colors cursor-pointer">
							Activate Rules
						</button>
					</div>
				</div>
			</div>
		</div>
	</section>

	<!-- ===== DEEP INTEGRATION ===== -->
	<section data-section="integration" class="py-24 px-6">
		<div class="max-w-5xl mx-auto">
			<div class="text-center mb-16 transition-all duration-700 {integrationVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}">
				<h2 class="text-3xl sm:text-4xl font-bold text-text-primary mb-4">The agent that optimizes itself.</h2>
				<p class="text-lg text-text-secondary max-w-xl mx-auto">Deep integration with the Hermes ecosystem for autonomous cost optimization.</p>
			</div>

			<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
				{#each [
					{
						title: 'Hermes Skill',
						desc: 'Native Hermes agent skill. RuleShield runs as part of your agent reasoning loop, not just a proxy.',
						tag: 'Agent Native',
						iconPath: '<circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/>'
					},
					{
						title: 'MCP Server',
						desc: 'Model Context Protocol server for real-time rule inspection, cache stats, and configuration from any MCP client.',
						tag: 'Protocol',
						iconPath: '<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>'
					},
					{
						title: 'Feedback Loop',
						desc: 'User corrections feed back into rule refinement. The system gets smarter with every interaction.',
						tag: 'Self-Learning',
						iconPath: '<path d="M21 12a9 9 0 11-6.219-8.56"/><polyline points="22 2 22 8 16 8"/>'
					}
				] as card, i}
					<div
						class="integration-card group transition-all duration-700"
						style="transition-delay: {i * 150}ms"
						class:opacity-100={integrationVisible}
						class:translate-y-0={integrationVisible}
						class:opacity-0={!integrationVisible}
						class:translate-y-8={!integrationVisible}
					>
						<div class="w-12 h-12 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary mb-5">
							<svg class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">{@html card.iconPath}</svg>
						</div>
						<div class="inline-flex px-2 py-0.5 rounded text-[10px] font-medium text-primary bg-primary/10 mb-3">{card.tag}</div>
						<h3 class="text-lg font-semibold text-text-primary mb-2">{card.title}</h3>
						<p class="text-sm text-text-secondary leading-relaxed">{card.desc}</p>
					</div>
				{/each}
			</div>
		</div>
	</section>

	<!-- ===== PROVEN RESULTS ===== -->
	<section data-section="results" class="py-24 px-6 relative">
		<div class="absolute inset-0 overflow-hidden pointer-events-none">
			<div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-accent/5 rounded-full blur-[150px]"></div>
		</div>

		<div class="max-w-5xl mx-auto relative z-10">
			<div class="text-center mb-16 transition-all duration-700 {resultsVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}">
				<div class="text-7xl sm:text-8xl font-extrabold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent mb-4 results-glow">
					47-82%
				</div>
				<h2 class="text-3xl sm:text-4xl font-bold text-text-primary mb-4">Proven Cost Reduction</h2>
				<p class="text-lg text-text-secondary max-w-xl mx-auto">Tested across four real-world scenarios with different query patterns.</p>
			</div>

			<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
				{#each [
					{ scenario: 'Customer Support', savings: '82%', queries: '10K', desc: 'FAQ-heavy with high repetition' },
					{ scenario: 'Code Review', savings: '61%', queries: '5K', desc: 'Pattern-rich code analysis' },
					{ scenario: 'Data Analysis', savings: '47%', queries: '8K', desc: 'Mixed complexity queries' },
					{ scenario: 'Content Gen', savings: '73%', queries: '12K', desc: 'Template-based generation' }
				] as result, i}
					<div
						class="result-card transition-all duration-700"
						style="transition-delay: {i * 100}ms"
						class:opacity-100={resultsVisible}
						class:translate-y-0={resultsVisible}
						class:opacity-0={!resultsVisible}
						class:translate-y-8={!resultsVisible}
					>
						<div class="text-3xl font-bold text-accent font-mono mb-1">{result.savings}</div>
						<h3 class="text-sm font-semibold text-text-primary mb-1">{result.scenario}</h3>
						<p class="text-xs text-text-muted mb-3">{result.desc}</p>
						<div class="text-[10px] text-text-muted font-mono">{result.queries} queries tested</div>
					</div>
				{/each}
			</div>
		</div>
	</section>

	<!-- ===== PRICING ===== -->
	<section id="pricing" data-section="pricing" class="py-24 px-6">
		<div class="max-w-5xl mx-auto">
			<div class="text-center mb-16 transition-all duration-700 {pricingVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}">
				<h2 class="text-3xl sm:text-4xl font-bold text-text-primary mb-4">Simple, savings-aligned pricing.</h2>
				<p class="text-lg text-text-secondary max-w-xl mx-auto">We only make money when you save money.</p>
			</div>

			<div class="grid grid-cols-1 md:grid-cols-3 gap-6 transition-all duration-700 delay-200 {pricingVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}">
				<!-- Free -->
				<div class="pricing-card">
					<div class="mb-6">
						<h3 class="text-lg font-semibold text-text-primary mb-1">Free</h3>
						<div class="text-4xl font-bold text-text-primary font-mono">$0</div>
						<p class="text-sm text-text-muted mt-2">For individual developers</p>
					</div>
					<ul class="space-y-3 mb-8 text-sm text-text-secondary">
						<li class="flex items-center gap-2"><span class="text-accent">&#10003;</span> Up to $500/mo savings</li>
						<li class="flex items-center gap-2"><span class="text-accent">&#10003;</span> 1 project</li>
						<li class="flex items-center gap-2"><span class="text-accent">&#10003;</span> Semantic cache</li>
						<li class="flex items-center gap-2"><span class="text-accent">&#10003;</span> Basic rules</li>
						<li class="flex items-center gap-2"><span class="text-accent">&#10003;</span> Community support</li>
					</ul>
					<button class="btn-ghost w-full py-2.5 text-sm cursor-pointer">Start Free</button>
				</div>

				<!-- Pro -->
				<div class="pricing-card pricing-card-featured relative">
					<div class="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-gradient-to-r from-primary to-accent text-white text-xs font-semibold">
						Most Popular
					</div>
					<div class="mb-6">
						<h3 class="text-lg font-semibold text-text-primary mb-1">Pro</h3>
						<div class="text-4xl font-bold text-text-primary font-mono">15%</div>
						<p class="text-sm text-text-muted mt-2">of verified savings</p>
					</div>
					<ul class="space-y-3 mb-8 text-sm text-text-secondary">
						<li class="flex items-center gap-2"><span class="text-accent">&#10003;</span> Unlimited savings</li>
						<li class="flex items-center gap-2"><span class="text-accent">&#10003;</span> 10 projects</li>
						<li class="flex items-center gap-2"><span class="text-accent">&#10003;</span> Shadow Mode</li>
						<li class="flex items-center gap-2"><span class="text-accent">&#10003;</span> Smart Router</li>
						<li class="flex items-center gap-2"><span class="text-accent">&#10003;</span> Hermes Bridge</li>
						<li class="flex items-center gap-2"><span class="text-accent">&#10003;</span> Priority support</li>
					</ul>
					<button class="btn-primary w-full py-2.5 text-sm cursor-pointer">Start Free Trial</button>
				</div>

				<!-- Enterprise -->
				<div class="pricing-card">
					<div class="mb-6">
						<h3 class="text-lg font-semibold text-text-primary mb-1">Enterprise</h3>
						<div class="text-4xl font-bold text-text-primary font-mono">Custom</div>
						<p class="text-sm text-text-muted mt-2">For large teams</p>
					</div>
					<ul class="space-y-3 mb-8 text-sm text-text-secondary">
						<li class="flex items-center gap-2"><span class="text-accent">&#10003;</span> Volume discounts</li>
						<li class="flex items-center gap-2"><span class="text-accent">&#10003;</span> Unlimited projects</li>
						<li class="flex items-center gap-2"><span class="text-accent">&#10003;</span> SSO & SAML</li>
						<li class="flex items-center gap-2"><span class="text-accent">&#10003;</span> Custom rules</li>
						<li class="flex items-center gap-2"><span class="text-accent">&#10003;</span> SLA guarantee</li>
						<li class="flex items-center gap-2"><span class="text-accent">&#10003;</span> Dedicated support</li>
					</ul>
					<button class="btn-ghost w-full py-2.5 text-sm cursor-pointer">Contact Sales</button>
				</div>
			</div>

			<p class="text-center text-sm text-text-muted mt-8 transition-all duration-700 delay-500 {pricingVisible ? 'opacity-100' : 'opacity-0'}">
				<span class="text-accent font-semibold">3x ROI guaranteed</span> or your money back. No credit card required to start.
			</p>
		</div>
	</section>

	<!-- ===== SELF-EVOLUTION ROADMAP ===== -->
	<section data-section="roadmap" class="py-24 px-6">
		<div class="max-w-4xl mx-auto">
			<div class="text-center mb-16 transition-all duration-700 {roadmapVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}">
				<h2 class="text-3xl sm:text-4xl font-bold text-text-primary mb-4">Self-Evolution Roadmap</h2>
				<p class="text-lg text-text-secondary max-w-xl mx-auto">RuleShield doesn't just save you money -- it gets smarter over time.</p>
			</div>

			<div class="relative transition-all duration-700 delay-200 {roadmapVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}">
				<!-- Timeline line -->
				<div class="absolute left-6 md:left-1/2 top-0 bottom-0 w-px bg-gradient-to-b from-primary via-accent to-primary/20"></div>

				{#each [
					{
						phase: 'NOW',
						title: 'Cache + Rules + Router',
						items: ['Semantic caching with embedding similarity', 'Auto-extracted decision rules', 'Complexity-based model routing', 'Hermes Bridge for local inference'],
						status: 'live'
					},
					{
						phase: 'NEXT',
						title: 'Shadow + Feedback + Cron',
						items: ['Shadow Mode validation', 'User feedback integration', 'Scheduled rule retraining', 'A/B testing framework'],
						status: 'building'
					},
					{
						phase: 'FUTURE',
						title: 'RL + GEPA + Marketplace',
						items: ['Reinforcement learning optimization', 'GEPA evolutionary patterns', 'Community rule marketplace', 'Multi-tenant cost sharing'],
						status: 'planned'
					}
				] as milestone, i}
					<div class="relative flex items-start gap-6 mb-12 last:mb-0 {i % 2 === 0 ? 'md:flex-row' : 'md:flex-row-reverse'} flex-row">
						<div class="hidden md:block md:w-1/2"></div>
						<!-- Dot on timeline -->
						<div class="absolute left-6 md:left-1/2 -translate-x-1/2 w-3 h-3 rounded-full {milestone.status === 'live' ? 'bg-accent shadow-[0_0_12px_rgba(0,212,170,0.5)]' : milestone.status === 'building' ? 'bg-primary shadow-[0_0_12px_rgba(108,92,231,0.5)]' : 'bg-border'} z-10 mt-6"></div>
						<div class="ml-12 md:ml-0 md:w-1/2 {i % 2 === 0 ? 'md:pl-10' : 'md:pr-10'}">
							<div class="bg-surface rounded-xl border border-border p-6 hover:border-primary/30 transition-colors">
								<div class="flex items-center gap-3 mb-3">
									<span class="font-mono text-xs font-bold {milestone.status === 'live' ? 'text-accent' : milestone.status === 'building' ? 'text-primary' : 'text-text-muted'} uppercase tracking-widest">{milestone.phase}</span>
									<span class="px-2 py-0.5 rounded text-[10px] font-medium {milestone.status === 'live' ? 'bg-accent/10 text-accent' : milestone.status === 'building' ? 'bg-primary/10 text-primary' : 'bg-border text-text-muted'}">
										{milestone.status === 'live' ? 'Live' : milestone.status === 'building' ? 'Building' : 'Planned'}
									</span>
								</div>
								<h3 class="text-lg font-semibold text-text-primary mb-3">{milestone.title}</h3>
								<ul class="space-y-2">
									{#each milestone.items as item}
										<li class="flex items-center gap-2 text-sm text-text-secondary">
											<span class="w-1 h-1 rounded-full {milestone.status === 'live' ? 'bg-accent' : milestone.status === 'building' ? 'bg-primary' : 'bg-text-muted'} flex-shrink-0"></span>
											{item}
										</li>
									{/each}
								</ul>
							</div>
						</div>
					</div>
				{/each}
			</div>
		</div>
	</section>

	<!-- ===== FINAL CTA ===== -->
	<section id="cta" data-section="cta" class="py-24 px-6 relative">
		<div class="absolute inset-0 overflow-hidden pointer-events-none">
			<div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[600px] bg-primary/5 rounded-full blur-[150px]"></div>
			<div class="absolute bottom-0 right-1/3 w-[400px] h-[400px] bg-accent/5 rounded-full blur-[120px]"></div>
		</div>

		<div class="max-w-3xl mx-auto text-center relative z-10">
			<div class="transition-all duration-700 {ctaVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}">
				<h2 class="text-3xl sm:text-4xl lg:text-5xl font-bold text-text-primary mb-6">
					Stop paying for answers<br />you already have.
				</h2>
				<p class="text-lg text-text-secondary mb-10 max-w-lg mx-auto">
					One line. One import. Up to 82% savings on your LLM costs.
				</p>

				<!-- Install snippet -->
				<div class="inline-flex items-center gap-3 bg-surface rounded-xl border border-border px-6 py-4 mb-10">
					<span class="text-text-muted font-mono text-sm">$</span>
					<code class="font-mono text-sm text-accent">pip install ruleshield-hermes</code>
					<button
						class="text-text-muted hover:text-text-primary transition-colors cursor-pointer"
						onclick={() => { navigator.clipboard.writeText('pip install ruleshield-hermes'); }}
						aria-label="Copy install command"
					>
						<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>
					</button>
				</div>

				<!-- CTAs -->
				<div class="flex flex-col sm:flex-row items-center justify-center gap-4">
					<button class="btn-primary text-base px-8 py-3.5 w-full sm:w-auto cursor-pointer">
						Start Free -- No Credit Card
						<svg class="inline-block ml-2 w-4 h-4" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 8h10M9 4l4 4-4 4"/></svg>
					</button>
					<button class="btn-ghost text-base px-8 py-3.5 w-full sm:w-auto cursor-pointer">
						Book Demo
					</button>
				</div>
			</div>
		</div>
	</section>

	<!-- ===== FOOTER ===== -->
	<footer class="border-t border-border py-12 px-6">
		<div class="max-w-5xl mx-auto">
			<div class="flex flex-col md:flex-row items-center justify-between gap-6">
				<div class="flex items-center gap-2">
					<div class="w-6 h-6 rounded-md bg-gradient-to-br from-primary to-accent flex items-center justify-center text-white font-bold text-[10px]">R</div>
					<span class="text-sm font-semibold text-text-primary">RuleShield</span>
				</div>

				<div class="flex flex-wrap items-center justify-center gap-6 text-sm text-text-muted">
					<a href="https://github.com/ruleshield" class="hover:text-text-primary transition-colors">GitHub</a>
					<a href="#" class="hover:text-text-primary transition-colors">Docs</a>
					<button onclick={() => scrollTo('pricing')} class="hover:text-text-primary transition-colors cursor-pointer">Pricing</button>
					<a href="#" class="hover:text-text-primary transition-colors">Privacy</a>
					<a href="#" class="hover:text-text-primary transition-colors">Terms</a>
				</div>

				<p class="text-xs text-text-muted text-center md:text-right">
					Built for <span class="text-primary">Hermes Agent Hackathon</span> by NousResearch
				</p>
			</div>
		</div>
	</footer>
</main>

<style>
	/* ===== NAV ===== */
	.nav-scrolled {
		background: rgba(10, 10, 15, 0.8);
		backdrop-filter: blur(16px);
		-webkit-backdrop-filter: blur(16px);
		border-bottom: 1px solid rgba(42, 42, 60, 0.5);
	}

	/* ===== BUTTONS ===== */
	.btn-primary {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		padding: 0.625rem 1.5rem;
		background: #6C5CE7;
		color: #fff;
		font-weight: 600;
		border-radius: 0.5rem;
		transition: all 0.2s ease;
		border: none;
		cursor: pointer;
	}

	.btn-primary:hover {
		background: #7D6FF0;
		box-shadow: 0 0 24px rgba(108, 92, 231, 0.4);
		transform: translateY(-1px);
	}

	.btn-primary:active {
		background: #5A4BD4;
		transform: translateY(0);
	}

	.btn-ghost {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		padding: 0.625rem 1.5rem;
		background: transparent;
		color: #F0F0F5;
		font-weight: 600;
		border-radius: 0.5rem;
		border: 1px solid #2A2A3C;
		transition: all 0.2s ease;
		cursor: pointer;
		text-decoration: none;
	}

	.btn-ghost:hover {
		background: #1A1A26;
		border-color: #6C5CE7;
		transform: translateY(-1px);
	}

	/* ===== CARDS ===== */
	.pain-card {
		background: #12121A;
		border: 1px solid #2A2A3C;
		border-radius: 1rem;
		padding: 2rem;
		transition: all 0.3s ease;
	}

	.pain-card:hover {
		border-color: rgba(108, 92, 231, 0.4);
		box-shadow: 0 0 30px rgba(108, 92, 231, 0.08);
		transform: translateY(-2px);
	}

	.layer-card {
		background: #12121A;
		border: 1px solid #2A2A3C;
		border-radius: 1rem;
		padding: 1.5rem;
		transition: all 0.3s ease;
	}

	.layer-card:hover {
		border-color: rgba(108, 92, 231, 0.4);
		box-shadow: 0 0 30px rgba(108, 92, 231, 0.1);
		transform: translateY(-2px);
	}

	.integration-card {
		background: #12121A;
		border: 1px solid #2A2A3C;
		border-radius: 1rem;
		padding: 2rem;
		transition: all 0.3s ease;
	}

	.integration-card:hover {
		border-color: rgba(108, 92, 231, 0.4);
		box-shadow: 0 0 30px rgba(108, 92, 231, 0.08);
		transform: translateY(-2px);
	}

	.result-card {
		background: #12121A;
		border: 1px solid #2A2A3C;
		border-radius: 1rem;
		padding: 1.5rem;
		text-align: center;
		transition: all 0.3s ease;
	}

	.result-card:hover {
		border-color: rgba(0, 212, 170, 0.3);
		box-shadow: 0 0 30px rgba(0, 212, 170, 0.08);
		transform: translateY(-2px);
	}

	/* ===== PRICING CARDS ===== */
	.pricing-card {
		background: #12121A;
		border: 1px solid #2A2A3C;
		border-radius: 1rem;
		padding: 2rem;
		transition: all 0.3s ease;
	}

	.pricing-card:hover {
		border-color: rgba(108, 92, 231, 0.4);
		transform: translateY(-4px);
		box-shadow: 0 0 40px rgba(108, 92, 231, 0.1);
	}

	.pricing-card-featured {
		border-color: #6C5CE7;
		background: linear-gradient(180deg, rgba(108, 92, 231, 0.08) 0%, #12121A 40%);
		box-shadow: 0 0 40px rgba(108, 92, 231, 0.15);
	}

	.pricing-card-featured:hover {
		box-shadow: 0 0 60px rgba(108, 92, 231, 0.25);
	}

	/* ===== RESULTS GLOW ===== */
	.results-glow {
		filter: drop-shadow(0 0 40px rgba(0, 212, 170, 0.2));
	}

	/* ===== SMOOTH SCROLL ===== */
	:global(html) {
		scroll-behavior: smooth;
	}

	/* ===== SELECTION ===== */
	::selection {
		background: rgba(108, 92, 231, 0.3);
		color: #F0F0F5;
	}
</style>
