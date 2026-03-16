<script lang="ts">
	let current = $state(0);
	let overview = $state(false);
	let direction = $state(1);
	let transitioning = $state(false);
	const totalSlides = 10;
	const AUTO_ADVANCE_MS = 5000;

	function goto(n: number) {
		if (n < 0 || n >= totalSlides || transitioning) return;
		direction = n > current ? 1 : -1;
		transitioning = true;
		current = n;
		setTimeout(() => (transitioning = false), 500);
	}

	function next() {
		if (overview) { overview = false; return; }
		goto(current + 1);
	}
	function prev() {
		if (overview) { overview = false; return; }
		goto(current - 1);
	}

	$effect(() => {
		function onKey(e: KeyboardEvent) {
			if (e.key === 'ArrowRight' || e.key === ' ') { e.preventDefault(); next(); }
			else if (e.key === 'ArrowLeft') { e.preventDefault(); prev(); }
			else if (e.key === 'Escape') { e.preventDefault(); overview = !overview; }
		}
		window.addEventListener('keydown', onKey);
		return () => window.removeEventListener('keydown', onKey);
	});

	$effect(() => {
		if (overview) return;
		const timer = setInterval(() => {
			if (transitioning || overview) return;
			goto(current >= totalSlides - 1 ? 0 : current + 1);
		}, AUTO_ADVANCE_MS);
		return () => clearInterval(timer);
	});

	/* Animated counters */
	let counterVisible: Record<number, boolean> = $state({});

	$effect(() => {
		// trigger animations when arriving at certain slides
		const c = current;
		counterVisible[c] = true;
	});

	function animateNumber(
		node: HTMLElement,
		{
			target,
			duration = 2000,
			prefix = '',
			suffix = '',
			decimals = 0
		}: { target: number; duration?: number; prefix?: string; suffix?: string; decimals?: number }
	) {
		const start = performance.now();
		function tick() {
			const elapsed = performance.now() - start;
			const progress = Math.min(elapsed / duration, 1);
			const eased = 1 - Math.pow(1 - progress, 3);
			const value = target * eased;
			const formatted =
				decimals > 0
					? value.toLocaleString(undefined, {
							minimumFractionDigits: decimals,
							maximumFractionDigits: decimals
						})
					: Math.floor(value).toLocaleString();
			node.textContent = prefix + formatted + suffix;
			if (progress < 1) requestAnimationFrame(tick);
		}
		tick();
		return { destroy() {} };
	}
</script>

<svelte:head>
	<title>RuleShield - Hackathon Presentation</title>
</svelte:head>

<!-- Overview Grid -->
{#if overview}
<div class="overview-backdrop" role="dialog" aria-label="Slide overview">
	<div class="overview-grid">
		{#each Array(totalSlides) as _, i}
			<button
				class="overview-thumb"
				class:active={i === current}
				onclick={() => { current = i; overview = false; }}
			>
				<span class="thumb-number">{i + 1}</span>
			</button>
		{/each}
	</div>
	<p class="overview-hint">Click a slide or press Escape to close</p>
</div>
{/if}

<!-- Slide Container -->
<div class="deck" aria-live="polite">
	{#each Array(totalSlides) as _, i}
		<div
			class="slide"
			class:active={i === current}
			class:past={i < current}
			class:future={i > current}
			aria-hidden={i !== current}
		>
			<!-- SLIDE 1: Title -->
			{#if i === 0}
			<div class="slide-content center-content">
				<div class="title-badge">Hermes Agent Hackathon 2026</div>
				<h1 class="hero-title">
					<span class="gradient-text">RuleShield</span>
				</h1>
				<p class="hero-subtitle">The Agent That Optimizes Itself</p>
				<div class="gradient-line"></div>
				<p class="hero-meta">Built for Hermes Agent &nbsp;|&nbsp; NousResearch</p>
				<div class="hero-particles">
					{#each Array(6) as _, p}
						<div class="particle" style="--i:{p}"></div>
					{/each}
				</div>
			</div>

			<!-- SLIDE 2: The Problem -->
			{:else if i === 1}
			<div class="slide-content">
				<h2 class="slide-heading">The Problem</h2>
				<p class="lead-text">Every agent call costs money.<br><span class="text-accent">60-80% are repetitive patterns.</span></p>

				<div class="big-number-container" class:visible={current === 1}>
					<div class="big-number">
						{#if current === 1}
							<span use:animateNumber={{ target: 420.69, prefix: '$', duration: 2000, decimals: 2 }}>$0</span>
						{:else}
							<span>$420.69</span>
						{/if}
						<span class="big-number-unit">/ month</span>
					</div>
					<p class="big-number-label">wasted on repeat questions</p>
				</div>

				<div class="card-row">
					<div class="problem-card">
						<div class="card-icon">👋</div>
						<h3>Greetings</h3>
						<code>"hello"</code>
						<div class="card-stats">
							<span class="stat-cost">$0.01 each</span>
							<span class="stat-freq">100x/day</span>
						</div>
					</div>
					<div class="problem-card">
						<div class="card-icon">📡</div>
						<h3>Status Checks</h3>
						<code>"are you there?"</code>
						<div class="card-stats">
							<span class="stat-cost">$0.01 each</span>
							<span class="stat-freq">50x/day</span>
						</div>
					</div>
					<div class="problem-card">
						<div class="card-icon">✅</div>
						<h3>Confirmations</h3>
						<code>"yes, proceed"</code>
						<div class="card-stats">
							<span class="stat-cost">$0.01 each</span>
							<span class="stat-freq">80x/day</span>
						</div>
					</div>
				</div>
			</div>

			<!-- SLIDE 3: How RuleShield Saves YOU Money -->
			{:else if i === 2}
			<div class="slide-content">
				<h2 class="slide-heading">How RuleShield Saves YOU Money</h2>
				<p class="lead-text">It removes unnecessary paid LLM calls before they happen.</p>

				<div class="card-row">
					<div class="problem-card">
						<div class="card-icon">⚡</div>
						<h3>Cache Hits</h3>
						<code>same prompt again</code>
						<div class="card-stats">
							<span class="stat-cost">$0.00</span>
							<span class="stat-freq">instant</span>
						</div>
					</div>
					<div class="problem-card">
						<div class="card-icon">🧠</div>
						<h3>Rule Responses</h3>
						<code>known intent pattern</code>
						<div class="card-stats">
							<span class="stat-cost">$0.00</span>
							<span class="stat-freq">predictable</span>
						</div>
					</div>
					<div class="problem-card">
						<div class="card-icon">🛣️</div>
						<h3>Smart Routing</h3>
						<code>easy task -> cheaper model</code>
						<div class="card-stats">
							<span class="stat-cost">lower $/call</span>
							<span class="stat-freq">auto</span>
						</div>
					</div>
				</div>

				<div class="model-insight">
					<p>Less passthrough to expensive models.</p>
					<p>More responses handled at zero or lower cost.</p>
				</div>
			</div>

			<!-- SLIDE 4: The Solution -->
			{:else if i === 3}
			<div class="slide-content">
				<h2 class="slide-heading">RuleShield Intelligence Pipeline</h2>
				<p class="lead-text">Intercept before it hits the LLM.</p>

				<div class="layers-diagram">
					<div class="layer-source">Hermes Agent</div>
					<div class="layer-arrow">
						<svg width="24" height="32" viewBox="0 0 24 32"><path d="M12 0 L12 24 M4 16 L12 24 L20 16" stroke="#6C5CE7" stroke-width="2" fill="none"/></svg>
					</div>
					<div class="layers-stack">
						<div class="layer layer-1" style="--delay:0.1s">
							<span class="layer-num">1</span>
							<span class="layer-name">Semantic Cache</span>
							<span class="layer-cost cost-free">$0</span>
							<span class="layer-desc">Identical requests</span>
						</div>
						<div class="layer layer-2" style="--delay:0.2s">
							<span class="layer-num">2</span>
							<span class="layer-name">Rule Engine</span>
							<span class="layer-cost cost-free">$0</span>
							<span class="layer-desc">75 learned patterns</span>
						</div>
						<div class="layer layer-3" style="--delay:0.3s">
							<span class="layer-num">3</span>
							<span class="layer-name">Hermes Bridge</span>
							<span class="layer-cost cost-cheap">$0.001</span>
							<span class="layer-desc">Local cheap model</span>
						</div>
						<div class="layer layer-4" style="--delay:0.4s">
							<span class="layer-num">4</span>
							<span class="layer-name">Smart Router</span>
							<span class="layer-cost cost-auto">auto</span>
							<span class="layer-desc">Complexity-based routing</span>
						</div>
					</div>
					<div class="layer-arrow">
						<svg width="24" height="32" viewBox="0 0 24 32"><path d="M12 0 L12 24 M4 16 L12 24 L20 16" stroke="#00D4AA" stroke-width="2" fill="none"/></svg>
					</div>
					<div class="layer-dest">LLM API <span class="text-secondary">(only complex tasks)</span></div>
				</div>
			</div>

			<!-- SLIDE 5: Two-Command Setup -->
			{:else if i === 4}
			<div class="slide-content center-content">
				<h2 class="slide-heading">Two-Command Setup</h2>

				<div class="terminal">
					<div class="terminal-bar">
						<span class="terminal-dot red"></span>
						<span class="terminal-dot yellow"></span>
						<span class="terminal-dot green"></span>
						<span class="terminal-title">terminal</span>
					</div>
					<div class="terminal-body">
						<div class="terminal-line">
							<span class="term-prompt">$</span>
							<span class="term-cmd">npm run setup:hermes</span>
						</div>
						<div class="terminal-line dim">
							<span class="term-output">RuleShield setup complete</span>
						</div>
						<div class="terminal-line" style="margin-top: 0.5rem">
							<span class="term-prompt">$</span>
							<span class="term-cmd">npm run start</span>
						</div>
						<div class="terminal-line">
							<span class="term-output rich-green">&#10003; Gateway started on localhost:&lt;PORT&gt;</span>
						</div>
						<div class="terminal-line">
							<span class="term-output rich-green">&#10003; Patched base_url &rarr; localhost:&lt;PORT&gt;</span>
						</div>
						<div class="terminal-line">
							<span class="term-output rich-green">&#10003; Loaded 75 Hermes-specific rules</span>
						</div>
						<div class="terminal-line">
							<span class="term-output rich-green">&#10003; Cache initialized (semantic + exact)</span>
						</div>
						<div class="terminal-line">
							<span class="term-output rich-purple">&#9733; RuleShield proxy running on :PORT</span>
						</div>
					</div>
				</div>

				<div class="setup-arrow">
					<svg width="40" height="40" viewBox="0 0 40 40"><path d="M8 20 H28 M22 14 L28 20 L22 26" stroke="#00D4AA" stroke-width="2.5" fill="none" stroke-linecap="round"/></svg>
					<span class="setup-label">That's it. Hermes now routes through RuleShield.</span>
				</div>
			</div>

			<!-- SLIDE 6: Model-Aware Intelligence -->
			{:else if i === 5}
			<div class="slide-content">
				<h2 class="slide-heading">Model-Aware Intelligence</h2>
				<p class="lead-text">"Not all requests deserve the same model."</p>

				<div class="model-table-wrap">
					<table class="model-table">
						<thead>
							<tr>
								<th></th>
								<th><span class="model-badge cheap">Haiku <span class="model-price">$</span></span></th>
								<th><span class="model-badge mid">Sonnet <span class="model-price">$$</span></span></th>
								<th><span class="model-badge expensive">Opus <span class="model-price">$$$</span></span></th>
							</tr>
						</thead>
						<tbody>
							<tr>
								<td class="row-label">Simple Greeting</td>
								<td><span class="check rule">RULE</span></td>
								<td><span class="check rule">RULE</span></td>
								<td><span class="check rule">RULE</span></td>
							</tr>
							<tr>
								<td class="row-label">Status Check</td>
								<td><span class="check rule">RULE</span></td>
								<td><span class="check rule">RULE</span></td>
								<td><span class="check rule">RULE</span></td>
							</tr>
							<tr>
								<td class="row-label">Confirmation</td>
								<td><span class="check rule">RULE</span></td>
								<td><span class="check rule">RULE</span></td>
								<td><span class="check llm">LLM</span></td>
							</tr>
							<tr>
								<td class="row-label">Simple Math</td>
								<td><span class="check rule">RULE</span></td>
								<td><span class="check llm">LLM</span></td>
								<td><span class="check llm">LLM</span></td>
							</tr>
						</tbody>
					</table>
				</div>

				<div class="model-insight">
					<p>Expensive models get premium treatment.</p>
					<p>Cheap models accept more rules.</p>
				</div>
			</div>

			<!-- SLIDE 7: Deep Hermes Integration -->
			{:else if i === 6}
			<div class="slide-content">
				<h2 class="slide-heading">Deep Hermes Integration</h2>

				<div class="integration-row">
					<div class="integration-card">
						<div class="integration-icon">
							<svg width="48" height="48" viewBox="0 0 48 48" fill="none">
								<rect x="4" y="4" width="40" height="40" rx="8" stroke="#6C5CE7" stroke-width="2"/>
								<path d="M16 20 L24 28 L32 20" stroke="#6C5CE7" stroke-width="2.5" stroke-linecap="round"/>
								<path d="M16 16 L32 16" stroke="#6C5CE7" stroke-width="2" stroke-linecap="round"/>
							</svg>
						</div>
						<h3>Hermes Skill</h3>
						<ul class="integration-list">
							<li><code>"show me my savings"</code></li>
							<li><code>"suggest new rules"</code></li>
							<li><code>"analyze my costs"</code></li>
						</ul>
					</div>

					<div class="integration-card">
						<div class="integration-icon">
							<svg width="48" height="48" viewBox="0 0 48 48" fill="none">
								<circle cx="24" cy="24" r="18" stroke="#00D4AA" stroke-width="2"/>
								<circle cx="24" cy="24" r="6" fill="#00D4AA" opacity="0.3"/>
								<circle cx="24" cy="24" r="3" fill="#00D4AA"/>
								<line x1="24" y1="6" x2="24" y2="12" stroke="#00D4AA" stroke-width="2"/>
								<line x1="24" y1="36" x2="24" y2="42" stroke="#00D4AA" stroke-width="2"/>
								<line x1="6" y1="24" x2="12" y2="24" stroke="#00D4AA" stroke-width="2"/>
								<line x1="36" y1="24" x2="42" y2="24" stroke="#00D4AA" stroke-width="2"/>
							</svg>
						</div>
						<h3>MCP Server</h3>
						<ul class="integration-list">
							<li>4 tools exposed</li>
							<li>Real-time cost estimate</li>
							<li>Cron replacement detect</li>
						</ul>
					</div>

					<div class="integration-card">
						<div class="integration-icon">
							<svg width="48" height="48" viewBox="0 0 48 48" fill="none">
								<path d="M12 36 L12 20 L20 12 L28 20 L28 12 L36 20 L36 36" stroke="#FFB84D" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
								<line x1="8" y1="36" x2="40" y2="36" stroke="#FFB84D" stroke-width="2" stroke-linecap="round"/>
							</svg>
						</div>
						<h3>Feedback Loop</h3>
						<ul class="integration-list">
							<li>Self-improving rules</li>
							<li>Bandit-style learning</li>
							<li>RL / GEPA ready</li>
						</ul>
					</div>
				</div>

				<div class="integration-footer">
					RuleShield doesn't just optimize &mdash; <span class="gradient-text">it evolves.</span>
				</div>
			</div>

			<!-- SLIDE 8: Self-Evolution Path -->
			{:else if i === 7}
			<div class="slide-content">
				<h2 class="slide-heading">Self-Evolution Path</h2>

				<div class="timeline">
					<div class="timeline-line"></div>
					<div class="timeline-node now">
						<div class="node-dot"></div>
						<div class="node-label">NOW</div>
						<div class="node-content">
							<ul>
								<li>Cache + Rules</li>
								<li>Smart Router</li>
								<li>75 Hermes Rules</li>
								<li>MCP Server</li>
							</ul>
						</div>
					</div>
					<div class="timeline-node next">
						<div class="node-dot"></div>
						<div class="node-label">NEXT</div>
						<div class="node-content">
							<ul>
								<li>Shadow Mode</li>
								<li>Feedback Loop</li>
								<li>Cron Replacement</li>
								<li>Web Dashboard</li>
							</ul>
						</div>
					</div>
					<div class="timeline-node future">
						<div class="node-dot"></div>
						<div class="node-label">FUTURE</div>
						<div class="node-content">
							<ul>
								<li>RL Training</li>
								<li>GEPA Evolution</li>
								<li>Auto-Prompt Trimming</li>
								<li>Rule Marketplace</li>
							</ul>
						</div>
					</div>
				</div>

				<p class="timeline-tagline">"From cost optimizer to <span class="gradient-text">intelligence layer</span>."</p>
			</div>

			<!-- SLIDE 9: Architecture -->
			{:else if i === 8}
			<div class="slide-content">
				<h2 class="slide-heading">Architecture</h2>

				<div class="arch-diagram">
					<div class="arch-outer">
						<div class="arch-outer-label">Hermes Agent</div>

						<div class="arch-top-row">
							<div class="arch-box skill">
								<div class="arch-box-title">Skill</div>
								<div class="arch-box-detail">.md file</div>
							</div>
							<div class="arch-box mcp">
								<div class="arch-box-title">MCP</div>
								<div class="arch-box-detail">4 tools</div>
							</div>
							<div class="arch-box config">
								<div class="arch-box-title">Config</div>
								<div class="arch-box-detail">base_url patch</div>
							</div>
						</div>

						<div class="arch-connector">
							<svg width="100%" height="40" preserveAspectRatio="none" viewBox="0 0 400 40">
								<path d="M80 0 L80 15 L200 15 M200 15 L320 15 L320 0 M200 0 L200 15 L200 40" stroke="#2A2A3C" stroke-width="2" fill="none"/>
								<circle cx="200" cy="15" r="3" fill="#6C5CE7"/>
							</svg>
						</div>

						<div class="arch-proxy">
							<div class="arch-proxy-title">RuleShield Proxy <span class="arch-port">:PORT</span></div>
							<div class="arch-pipeline">
								<span class="pipe-step">Cache</span>
								<span class="pipe-arrow">&rarr;</span>
								<span class="pipe-step">Rules</span>
								<span class="pipe-arrow">&rarr;</span>
								<span class="pipe-step">Bridge</span>
								<span class="pipe-arrow">&rarr;</span>
								<span class="pipe-step">Router</span>
								<span class="pipe-arrow">&rarr;</span>
								<span class="pipe-step">LLM</span>
							</div>
							<div class="arch-feedback">Feedback Loop + Shadow Mode</div>
						</div>

						<div class="arch-connector-down">
							<svg width="100%" height="30" preserveAspectRatio="none" viewBox="0 0 400 30">
								<path d="M200 0 L200 30" stroke="#2A2A3C" stroke-width="2" fill="none"/>
								<circle cx="200" cy="15" r="3" fill="#00D4AA"/>
							</svg>
						</div>

						<div class="arch-bottom">
							<div class="arch-dash-left">
								<div class="arch-box-title">Web Dashboard</div>
								<div class="arch-box-detail">:5174</div>
							</div>
							<div class="arch-divider"></div>
							<div class="arch-dash-right">
								<div class="arch-box-title">Terminal Dashboard</div>
								<div class="arch-box-detail">Rich CLI</div>
							</div>
						</div>
					</div>
				</div>
			</div>

			<!-- SLIDE 10: Call to Action -->
			{:else if i === 9}
			<div class="slide-content center-content">
				<h2 class="cta-heading">Try it now.</h2>

				<div class="cta-commands">
					<code>npm run setup:hermes</code>
					<code>npm run start</code>
				</div>

				<a href="https://github.com/banse/RuleShield" class="cta-link" target="_blank" rel="noopener">
					github.com/banse/RuleShield
				</a>

				<div class="cta-brand">
					<span class="gradient-text cta-logo">RuleShield</span>
					<p class="cta-tagline">"The agent that optimizes itself."</p>
				</div>

				<div class="cta-footer">
					Built for <span class="text-accent">#HermesAgentHackathon</span> by <span class="text-primary-brand">@NousResearch</span>
				</div>

				<div class="hero-particles">
					{#each Array(8) as _, p}
						<div class="particle" style="--i:{p}"></div>
					{/each}
				</div>
			</div>
			{/if}
		</div>
	{/each}

	<!-- Navigation Dots -->
	<nav class="slide-dots" aria-label="Slide navigation">
		{#each Array(totalSlides) as _, i}
			<button
				class="dot"
				class:active={i === current}
				onclick={() => goto(i)}
				aria-label="Go to slide {i + 1}"
				aria-current={i === current ? 'step' : undefined}
			></button>
		{/each}
	</nav>

	<!-- Slide Counter -->
	<div class="slide-counter">
		<span class="counter-current">{current + 1}</span>
		<span class="counter-sep">/</span>
		<span class="counter-total">{totalSlides}</span>
	</div>

	<!-- Nav Arrows -->
	<button class="nav-arrow nav-prev" onclick={prev} disabled={current === 0} aria-label="Previous slide">
		<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M15 18L9 12L15 6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
	</button>
	<button class="nav-arrow nav-next" onclick={next} disabled={current === totalSlides - 1} aria-label="Next slide">
		<svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M9 6L15 12L9 18" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
	</button>
</div>

<style>
	/* ═══════════════════════════════════════════
	   DESIGN TOKENS
	   ═══════════════════════════════════════════ */
	:root {
		--bg: #0A0A0F;
		--surface: #12121A;
		--border: #2A2A3C;
		--primary: #6C5CE7;
		--accent: #00D4AA;
		--text: #F0F0F5;
		--text-sec: #A0A0B8;
		--error: #FF6B6B;
		--warning: #FFB84D;
		--grad: linear-gradient(135deg, #6C5CE7, #00D4AA);
		--font: 'Inter', system-ui, -apple-system, sans-serif;
		--mono: 'JetBrains Mono', 'Fira Code', monospace;
	}

	/* ═══════════════════════════════════════════
	   RESET / GLOBAL
	   ═══════════════════════════════════════════ */
	:global(body) {
		margin: 0;
		padding: 0;
		background: var(--bg);
		color: var(--text);
		font-family: var(--font);
	}

	* {
		box-sizing: border-box;
	}

	/* ═══════════════════════════════════════════
	   DECK CONTAINER
	   ═══════════════════════════════════════════ */
	.deck {
		position: relative;
		width: 100vw;
		height: 100vh;
		overflow: hidden;
		background: var(--bg);
	}

	/* ═══════════════════════════════════════════
	   INDIVIDUAL SLIDES
	   ═══════════════════════════════════════════ */
	.slide {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		opacity: 0;
		transform: translateX(60px);
		transition: opacity 0.5s cubic-bezier(0.4, 0, 0.2, 1), transform 0.5s cubic-bezier(0.4, 0, 0.2, 1);
		pointer-events: none;
		padding: 2rem;
	}

	.slide.active {
		opacity: 1;
		transform: translateX(0);
		pointer-events: auto;
		z-index: 2;
	}

	.slide.past {
		opacity: 0;
		transform: translateX(-60px);
	}

	.slide.future {
		opacity: 0;
		transform: translateX(60px);
	}

	.slide-content {
		max-width: 960px;
		width: 100%;
		position: relative;
	}

	.center-content {
		text-align: center;
		display: flex;
		flex-direction: column;
		align-items: center;
	}

	/* ═══════════════════════════════════════════
	   TYPOGRAPHY
	   ═══════════════════════════════════════════ */
	.gradient-text {
		background: var(--grad);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
	}

	.text-accent { color: var(--accent); }
	.text-secondary { color: var(--text-sec); font-weight: 400; }
	.text-primary-brand { color: var(--primary); }

	.slide-heading {
		font-size: 2.5rem;
		font-weight: 700;
		margin: 0 0 0.75rem;
		letter-spacing: -0.02em;
	}

	.lead-text {
		font-size: 1.25rem;
		color: var(--text-sec);
		margin: 0 0 2rem;
		line-height: 1.6;
	}

	h3 {
		font-size: 1rem;
		font-weight: 600;
		margin: 0.5rem 0 0.25rem;
		color: var(--text);
	}

	code {
		font-family: var(--mono);
		font-size: 0.85em;
		background: var(--surface);
		padding: 0.15em 0.5em;
		border-radius: 4px;
		color: var(--text-sec);
	}

	/* ═══════════════════════════════════════════
	   SLIDE 1: TITLE
	   ═══════════════════════════════════════════ */
	.title-badge {
		font-size: 0.8rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.15em;
		color: var(--primary);
		border: 1px solid color-mix(in srgb, var(--primary) 30%, transparent);
		padding: 0.4em 1.2em;
		border-radius: 100px;
		margin-bottom: 2rem;
	}

	.hero-title {
		font-size: 5rem;
		font-weight: 800;
		letter-spacing: -0.04em;
		margin: 0;
		line-height: 1;
	}

	.hero-subtitle {
		font-size: 1.5rem;
		color: var(--text-sec);
		margin: 1rem 0 2rem;
		font-weight: 400;
	}

	.gradient-line {
		width: 200px;
		height: 3px;
		background: var(--grad);
		border-radius: 2px;
		margin: 0 auto 2rem;
		box-shadow: 0 0 20px color-mix(in srgb, var(--primary) 40%, transparent);
	}

	.hero-meta {
		font-size: 1rem;
		color: var(--text-sec);
		margin: 0;
	}

	.hero-particles {
		position: absolute;
		inset: 0;
		pointer-events: none;
		overflow: hidden;
	}

	.particle {
		position: absolute;
		width: 4px;
		height: 4px;
		background: var(--primary);
		border-radius: 50%;
		opacity: 0.3;
		animation: float 6s ease-in-out infinite;
		animation-delay: calc(var(--i) * -0.8s);
		left: calc(10% + var(--i) * 13%);
		top: calc(20% + var(--i) * 8%);
	}

	.particle:nth-child(even) {
		background: var(--accent);
		width: 3px;
		height: 3px;
	}

	@keyframes float {
		0%, 100% { transform: translateY(0) translateX(0); opacity: 0.2; }
		25% { transform: translateY(-30px) translateX(10px); opacity: 0.5; }
		50% { transform: translateY(-15px) translateX(-8px); opacity: 0.3; }
		75% { transform: translateY(-40px) translateX(15px); opacity: 0.4; }
	}

	/* ═══════════════════════════════════════════
	   SLIDE 2: PROBLEM
	   ═══════════════════════════════════════════ */
	.big-number-container {
		text-align: center;
		margin: 1.5rem 0 2rem;
		opacity: 0;
		transform: scale(0.9);
		transition: opacity 0.6s ease, transform 0.6s ease;
	}

	.big-number-container.visible {
		opacity: 1;
		transform: scale(1);
	}

	.big-number {
		font-family: var(--mono);
		font-size: 3.5rem;
		font-weight: 700;
		color: var(--error);
		text-shadow: 0 0 40px color-mix(in srgb, var(--error) 30%, transparent);
	}

	.big-number-unit {
		font-size: 1.5rem;
		color: var(--text-sec);
		font-weight: 400;
	}

	.big-number-label {
		color: var(--text-sec);
		font-size: 1rem;
		margin: 0.25rem 0 0;
	}

	.card-row {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 1rem;
	}

	.problem-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 1.25rem;
		text-align: center;
		transition: border-color 0.3s, box-shadow 0.3s;
	}

	.problem-card:hover {
		border-color: var(--primary);
		box-shadow: 0 0 20px color-mix(in srgb, var(--primary) 15%, transparent);
	}

	.card-icon {
		font-size: 1.5rem;
		margin-bottom: 0.25rem;
	}

	.card-stats {
		display: flex;
		flex-direction: column;
		gap: 0.15rem;
		margin-top: 0.5rem;
		font-family: var(--mono);
		font-size: 0.8rem;
	}

	.stat-cost { color: var(--error); }
	.stat-freq { color: var(--text-sec); }

	/* ═══════════════════════════════════════════
	   SLIDE 3: SOLUTION LAYERS
	   ═══════════════════════════════════════════ */
	.layers-diagram {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.5rem;
	}

	.layer-source, .layer-dest {
		font-family: var(--mono);
		font-size: 1rem;
		font-weight: 600;
		padding: 0.6em 1.5em;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 8px;
	}

	.layer-arrow {
		display: flex;
		justify-content: center;
	}

	.layers-stack {
		width: 100%;
		max-width: 640px;
		display: flex;
		flex-direction: column;
		gap: 0;
		border: 1px solid var(--border);
		border-radius: 12px;
		overflow: hidden;
		background: var(--surface);
	}

	.layer {
		display: grid;
		grid-template-columns: 40px 1fr auto 1fr;
		align-items: center;
		padding: 0.85rem 1.25rem;
		border-bottom: 1px solid var(--border);
		opacity: 0;
		animation: layerIn 0.5s ease forwards;
		animation-delay: var(--delay);
	}

	.slide.active .layer { opacity: 0; animation: layerIn 0.5s ease forwards; animation-delay: var(--delay); }
	.slide:not(.active) .layer { animation: none; opacity: 1; }

	@keyframes layerIn {
		from { opacity: 0; transform: translateX(-20px); }
		to { opacity: 1; transform: translateX(0); }
	}

	.layer:last-child { border-bottom: none; }

	.layer-num {
		width: 28px;
		height: 28px;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 50%;
		background: color-mix(in srgb, var(--primary) 20%, transparent);
		color: var(--primary);
		font-weight: 700;
		font-size: 0.85rem;
		font-family: var(--mono);
	}

	.layer-name {
		font-weight: 600;
		font-size: 1rem;
		padding-left: 0.75rem;
	}

	.layer-cost {
		font-family: var(--mono);
		font-weight: 600;
		font-size: 0.9rem;
		padding: 0.2em 0.7em;
		border-radius: 6px;
	}

	.cost-free {
		color: var(--accent);
		background: color-mix(in srgb, var(--accent) 12%, transparent);
	}

	.cost-cheap {
		color: var(--warning);
		background: color-mix(in srgb, var(--warning) 12%, transparent);
	}

	.cost-auto {
		color: var(--primary);
		background: color-mix(in srgb, var(--primary) 12%, transparent);
	}

	.layer-desc {
		color: var(--text-sec);
		font-size: 0.85rem;
		text-align: right;
	}

	/* ═══════════════════════════════════════════
	   SLIDE 4: TERMINAL
	   ═══════════════════════════════════════════ */
	.terminal {
		width: 100%;
		max-width: 600px;
		background: #0D0D14;
		border: 1px solid var(--border);
		border-radius: 12px;
		overflow: hidden;
		text-align: left;
		box-shadow: 0 20px 60px rgba(0,0,0,0.5);
	}

	.terminal-bar {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 0.7rem 1rem;
		background: #161622;
		border-bottom: 1px solid var(--border);
	}

	.terminal-dot {
		width: 10px;
		height: 10px;
		border-radius: 50%;
	}

	.terminal-dot.red { background: #FF5F57; }
	.terminal-dot.yellow { background: #FEBC2E; }
	.terminal-dot.green { background: #28C840; }

	.terminal-title {
		color: var(--text-sec);
		font-size: 0.75rem;
		margin-left: auto;
		font-family: var(--mono);
	}

	.terminal-body {
		padding: 1rem 1.25rem;
		font-family: var(--mono);
		font-size: 0.85rem;
		line-height: 1.7;
	}

	.terminal-line {
		display: flex;
		gap: 0.5rem;
		align-items: baseline;
	}

	.terminal-line.dim { opacity: 0.5; }

	.term-prompt { color: var(--accent); font-weight: 700; }
	.term-cmd { color: var(--text); }
	.term-output { color: var(--text-sec); }
	.rich-green { color: var(--accent) !important; }
	.rich-purple { color: var(--primary) !important; }

	.setup-arrow {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-top: 2rem;
	}

	.setup-label {
		font-size: 1.15rem;
		color: var(--text);
		font-weight: 500;
	}

	/* ═══════════════════════════════════════════
	   SLIDE 5: MODEL TABLE
	   ═══════════════════════════════════════════ */
	.model-table-wrap {
		overflow-x: auto;
		margin: 1rem 0;
	}

	.model-table {
		width: 100%;
		border-collapse: separate;
		border-spacing: 0;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		overflow: hidden;
	}

	.model-table th, .model-table td {
		padding: 0.85rem 1.25rem;
		text-align: center;
		border-bottom: 1px solid var(--border);
	}

	.model-table thead th {
		background: color-mix(in srgb, var(--surface) 80%, var(--bg));
		font-weight: 600;
		font-size: 0.9rem;
	}

	.model-table tbody tr:last-child td { border-bottom: none; }

	.model-badge {
		font-family: var(--mono);
		font-weight: 600;
		font-size: 0.85rem;
	}

	.model-price { opacity: 0.5; font-weight: 400; }

	.model-badge.cheap { color: var(--accent); }
	.model-badge.mid { color: var(--warning); }
	.model-badge.expensive { color: var(--error); }

	.row-label {
		text-align: left !important;
		color: var(--text-sec);
		font-weight: 500;
	}

	.check {
		font-family: var(--mono);
		font-weight: 700;
		font-size: 0.8rem;
		padding: 0.2em 0.6em;
		border-radius: 4px;
	}

	.check.rule {
		color: var(--accent);
		background: color-mix(in srgb, var(--accent) 12%, transparent);
	}

	.check.llm {
		color: var(--text-sec);
		background: color-mix(in srgb, var(--text-sec) 10%, transparent);
	}

	.model-insight {
		text-align: center;
		margin-top: 1.5rem;
	}

	.model-insight p {
		margin: 0.25rem 0;
		color: var(--text-sec);
		font-size: 1.1rem;
		font-style: italic;
	}

	.model-insight p:first-child { color: var(--text); font-weight: 500; }

	/* ═══════════════════════════════════════════
	   SLIDE 6: RESULTS
	   ═══════════════════════════════════════════ */
	.results-hero {
		text-align: center;
		margin: 1rem 0 2rem;
		opacity: 0;
		transform: scale(0.9);
		transition: opacity 0.6s ease, transform 0.6s ease;
	}

	.results-hero.visible { opacity: 1; transform: scale(1); }

	.results-number {
		font-family: var(--mono);
		font-size: 5rem;
		font-weight: 800;
		background: var(--grad);
		-webkit-background-clip: text;
		-webkit-text-fill-color: transparent;
		background-clip: text;
		text-shadow: none;
		filter: drop-shadow(0 0 30px color-mix(in srgb, var(--primary) 30%, transparent));
	}

	.results-dash {
		font-size: 4rem;
		color: var(--text-sec);
		margin: 0 0.25rem;
	}

	.results-label {
		display: block;
		font-size: 1.25rem;
		color: var(--text-sec);
		margin-top: 0.25rem;
	}

	.results-cards {
		grid-template-columns: repeat(4, 1fr);
	}

	.result-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 1.25rem;
		text-align: center;
		transition: border-color 0.3s, transform 0.3s;
	}

	.result-card:hover {
		border-color: var(--accent);
		transform: translateY(-4px);
	}

	.result-icon { font-size: 1.5rem; }

	.result-percent {
		font-family: var(--mono);
		font-size: 2rem;
		font-weight: 700;
		color: var(--accent);
		margin: 0.5rem 0 0.25rem;
		text-shadow: 0 0 20px color-mix(in srgb, var(--accent) 25%, transparent);
	}

	.result-detail {
		color: var(--text-sec);
		font-size: 0.85rem;
		margin: 0;
	}

	/* ═══════════════════════════════════════════
	   SLIDE 7: INTEGRATION
	   ═══════════════════════════════════════════ */
	.integration-row {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 1.25rem;
		margin: 2rem 0;
	}

	.integration-card {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 12px;
		padding: 1.5rem;
		text-align: center;
		transition: border-color 0.3s, box-shadow 0.3s;
	}

	.integration-card:hover {
		border-color: var(--primary);
		box-shadow: 0 0 30px color-mix(in srgb, var(--primary) 12%, transparent);
	}

	.integration-icon {
		margin-bottom: 0.75rem;
	}

	.integration-list {
		list-style: none;
		padding: 0;
		margin: 0.75rem 0 0;
		text-align: left;
	}

	.integration-list li {
		padding: 0.3rem 0;
		color: var(--text-sec);
		font-size: 0.9rem;
	}

	.integration-list code {
		font-size: 0.8em;
	}

	.integration-footer {
		text-align: center;
		font-size: 1.15rem;
		color: var(--text-sec);
		margin-top: 1rem;
		font-style: italic;
	}

	/* ═══════════════════════════════════════════
	   SLIDE 8: TIMELINE
	   ═══════════════════════════════════════════ */
	.timeline {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		position: relative;
		margin: 3rem 0;
		padding: 0 2rem;
	}

	.timeline-line {
		position: absolute;
		top: 10px;
		left: 2rem;
		right: 2rem;
		height: 3px;
		background: var(--grad);
		border-radius: 2px;
		box-shadow: 0 0 15px color-mix(in srgb, var(--primary) 30%, transparent);
	}

	.timeline-node {
		position: relative;
		flex: 1;
		text-align: center;
		padding-top: 2rem;
	}

	.node-dot {
		position: absolute;
		top: 0;
		left: 50%;
		transform: translateX(-50%);
		width: 20px;
		height: 20px;
		border-radius: 50%;
		background: var(--bg);
		border: 3px solid var(--primary);
		box-shadow: 0 0 15px color-mix(in srgb, var(--primary) 40%, transparent);
	}

	.timeline-node.now .node-dot { border-color: var(--accent); box-shadow: 0 0 15px color-mix(in srgb, var(--accent) 40%, transparent); background: var(--accent); }
	.timeline-node.next .node-dot { border-color: var(--primary); }
	.timeline-node.future .node-dot { border-color: var(--text-sec); }

	.node-label {
		font-family: var(--mono);
		font-weight: 700;
		font-size: 0.85rem;
		letter-spacing: 0.1em;
		margin-bottom: 0.75rem;
	}

	.timeline-node.now .node-label { color: var(--accent); }
	.timeline-node.next .node-label { color: var(--primary); }
	.timeline-node.future .node-label { color: var(--text-sec); }

	.node-content ul {
		list-style: none;
		padding: 0;
		margin: 0;
	}

	.node-content li {
		color: var(--text-sec);
		font-size: 0.9rem;
		padding: 0.2rem 0;
	}

	.timeline-tagline {
		text-align: center;
		font-size: 1.25rem;
		color: var(--text-sec);
		font-style: italic;
		margin-top: 2rem;
	}

	/* ═══════════════════════════════════════════
	   SLIDE 9: ARCHITECTURE
	   ═══════════════════════════════════════════ */
	.arch-diagram {
		display: flex;
		justify-content: center;
		margin-top: 1rem;
	}

	.arch-outer {
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 16px;
		padding: 1.5rem 2rem;
		width: 100%;
		max-width: 700px;
		position: relative;
	}

	.arch-outer-label {
		position: absolute;
		top: -0.7rem;
		left: 1.5rem;
		background: var(--surface);
		padding: 0 0.75rem;
		font-family: var(--mono);
		font-weight: 700;
		font-size: 0.85rem;
		color: var(--primary);
		letter-spacing: 0.05em;
	}

	.arch-top-row {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 0.75rem;
		margin-top: 0.75rem;
	}

	.arch-box {
		background: var(--bg);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 0.75rem;
		text-align: center;
	}

	.arch-box-title {
		font-family: var(--mono);
		font-weight: 600;
		font-size: 0.85rem;
		color: var(--text);
	}

	.arch-box-detail {
		font-size: 0.75rem;
		color: var(--text-sec);
		margin-top: 0.15rem;
	}

	.arch-box.skill { border-color: color-mix(in srgb, var(--primary) 40%, transparent); }
	.arch-box.mcp { border-color: color-mix(in srgb, var(--accent) 40%, transparent); }
	.arch-box.config { border-color: color-mix(in srgb, var(--warning) 40%, transparent); }

	.arch-connector, .arch-connector-down {
		display: flex;
		justify-content: center;
	}

	.arch-proxy {
		background: color-mix(in srgb, var(--primary) 8%, var(--bg));
		border: 1px solid color-mix(in srgb, var(--primary) 30%, transparent);
		border-radius: 10px;
		padding: 1rem;
		text-align: center;
	}

	.arch-proxy-title {
		font-family: var(--mono);
		font-weight: 700;
		font-size: 0.95rem;
		color: var(--text);
		margin-bottom: 0.5rem;
	}

	.arch-port {
		color: var(--accent);
		font-weight: 400;
		font-size: 0.85rem;
	}

	.arch-pipeline {
		display: flex;
		justify-content: center;
		align-items: center;
		gap: 0.3rem;
		flex-wrap: wrap;
	}

	.pipe-step {
		font-family: var(--mono);
		font-size: 0.8rem;
		padding: 0.25em 0.6em;
		background: var(--surface);
		border-radius: 4px;
		color: var(--text);
		font-weight: 500;
	}

	.pipe-arrow {
		color: var(--text-sec);
		font-size: 0.75rem;
	}

	.arch-feedback {
		margin-top: 0.5rem;
		font-size: 0.8rem;
		color: var(--accent);
		font-style: italic;
	}

	.arch-bottom {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 1rem;
		background: var(--bg);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 0.75rem 1.5rem;
	}

	.arch-divider {
		width: 1px;
		height: 30px;
		background: var(--border);
	}

	.arch-dash-left, .arch-dash-right {
		text-align: center;
	}

	/* ═══════════════════════════════════════════
	   SLIDE 10: CTA
	   ═══════════════════════════════════════════ */
	.cta-heading {
		font-size: 3.5rem;
		font-weight: 800;
		margin: 0 0 2rem;
		letter-spacing: -0.03em;
	}

	.cta-commands {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		margin-bottom: 1.5rem;
	}

	.cta-commands code {
		font-size: 1.1rem;
		padding: 0.6em 1.5em;
		border-radius: 8px;
		border: 1px solid var(--border);
		background: var(--surface);
		color: var(--accent);
		font-weight: 500;
	}

	.cta-link {
		font-family: var(--mono);
		font-size: 1rem;
		color: var(--primary);
		text-decoration: none;
		padding: 0.4em 1em;
		border: 1px solid color-mix(in srgb, var(--primary) 30%, transparent);
		border-radius: 8px;
		transition: all 0.3s;
		display: inline-block;
		margin-bottom: 2.5rem;
	}

	.cta-link:hover {
		background: color-mix(in srgb, var(--primary) 12%, transparent);
		border-color: var(--primary);
	}

	.cta-brand {
		margin-bottom: 2rem;
	}

	.cta-logo {
		font-size: 3rem;
		font-weight: 800;
		letter-spacing: -0.03em;
	}

	.cta-tagline {
		font-size: 1.15rem;
		color: var(--text-sec);
		font-style: italic;
		margin: 0.5rem 0 0;
	}

	.cta-footer {
		font-size: 0.9rem;
		color: var(--text-sec);
	}

	/* ═══════════════════════════════════════════
	   NAVIGATION
	   ═══════════════════════════════════════════ */
	.slide-dots {
		position: fixed;
		bottom: 1.5rem;
		left: 50%;
		transform: translateX(-50%);
		display: flex;
		gap: 8px;
		z-index: 100;
	}

	.dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		border: none;
		background: var(--border);
		cursor: pointer;
		padding: 0;
		transition: all 0.3s;
	}

	.dot.active {
		background: var(--primary);
		box-shadow: 0 0 10px color-mix(in srgb, var(--primary) 50%, transparent);
		transform: scale(1.3);
	}

	.dot:hover:not(.active) {
		background: var(--text-sec);
	}

	.slide-counter {
		position: fixed;
		bottom: 1.5rem;
		right: 2rem;
		font-family: var(--mono);
		font-size: 0.8rem;
		color: var(--text-sec);
		z-index: 100;
	}

	.counter-current { color: var(--text); font-weight: 600; }
	.counter-sep { margin: 0 0.15em; }

	.nav-arrow {
		position: fixed;
		top: 50%;
		transform: translateY(-50%);
		background: color-mix(in srgb, var(--surface) 80%, transparent);
		border: 1px solid var(--border);
		border-radius: 50%;
		width: 44px;
		height: 44px;
		display: flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		color: var(--text-sec);
		transition: all 0.3s;
		z-index: 100;
		backdrop-filter: blur(8px);
		-webkit-backdrop-filter: blur(8px);
	}

	.nav-prev { left: 1.5rem; }
	.nav-next { right: 1.5rem; }

	.nav-arrow:hover:not(:disabled) {
		color: var(--text);
		border-color: var(--primary);
		background: color-mix(in srgb, var(--primary) 15%, transparent);
	}

	.nav-arrow:disabled {
		opacity: 0.2;
		cursor: default;
	}

	/* ═══════════════════════════════════════════
	   OVERVIEW
	   ═══════════════════════════════════════════ */
	.overview-backdrop {
		position: fixed;
		inset: 0;
		background: color-mix(in srgb, var(--bg) 95%, transparent);
		z-index: 200;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		backdrop-filter: blur(10px);
		-webkit-backdrop-filter: blur(10px);
	}

	.overview-grid {
		display: grid;
		grid-template-columns: repeat(5, 1fr);
		gap: 1rem;
		max-width: 700px;
		width: 90%;
	}

	.overview-thumb {
		aspect-ratio: 16/10;
		background: var(--surface);
		border: 2px solid var(--border);
		border-radius: 8px;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: all 0.3s;
		color: var(--text-sec);
		font-family: var(--mono);
		font-size: 1.25rem;
		font-weight: 700;
	}

	.overview-thumb.active {
		border-color: var(--primary);
		box-shadow: 0 0 20px color-mix(in srgb, var(--primary) 30%, transparent);
		color: var(--primary);
	}

	.overview-thumb:hover {
		border-color: var(--accent);
		transform: scale(1.05);
	}

	.overview-hint {
		color: var(--text-sec);
		font-size: 0.85rem;
		margin-top: 1.5rem;
	}

	/* ═══════════════════════════════════════════
	   PRINT STYLES
	   ═══════════════════════════════════════════ */
	@media print {
		.deck { overflow: visible; height: auto; }

		.slide {
			position: relative !important;
			opacity: 1 !important;
			transform: none !important;
			pointer-events: auto !important;
			page-break-after: always;
			page-break-inside: avoid;
			height: 100vh;
			break-after: page;
		}

		.slide.past, .slide.future {
			opacity: 1 !important;
			transform: none !important;
		}

		.slide-dots, .slide-counter, .nav-arrow, .overview-backdrop, .hero-particles {
			display: none !important;
		}

		.big-number-container { opacity: 1 !important; transform: none !important; }
		.results-hero { opacity: 1 !important; transform: none !important; }
		.layer { opacity: 1 !important; animation: none !important; }

		* {
			-webkit-print-color-adjust: exact !important;
			print-color-adjust: exact !important;
		}
	}

	/* ═══════════════════════════════════════════
	   RESPONSIVE
	   ═══════════════════════════════════════════ */
	@media (max-width: 768px) {
		.hero-title { font-size: 3rem; }
		.slide-heading { font-size: 1.75rem; }
		.card-row { grid-template-columns: 1fr; }
		.results-cards { grid-template-columns: repeat(2, 1fr); }
		.integration-row { grid-template-columns: 1fr; }
		.results-number { font-size: 3rem; }
		.big-number { font-size: 2.5rem; }
		.timeline { flex-direction: column; gap: 2rem; padding: 0; }
		.timeline-line { display: none; }
		.node-dot { display: none; }
		.timeline-node { padding-top: 0; }
		.arch-top-row { grid-template-columns: 1fr; }
		.slide { padding: 1rem; }
		.nav-arrow { display: none; }
		.overview-grid { grid-template-columns: repeat(3, 1fr); }
		.cta-heading { font-size: 2.5rem; }
		.layer { grid-template-columns: 32px 1fr auto; }
		.layer-desc { display: none; }
	}
</style>
