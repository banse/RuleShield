<script lang="ts">
	// Quick Start / Overview page -- static content, no server dependencies
</script>

<h1 class="docs-h1">RuleShield Hermes</h1>
<p class="docs-lead">
	An intelligent LLM cost optimizer that sits between your Hermes Agent and any LLM provider.
	It learns your agent's patterns through 5 layers of defense, routes requests across 80+ models
	to the cheapest capable option, and improves its own rules through a feedback loop with
	auto-promotion.
</p>

<div class="docs-note">
	<strong>Proven results:</strong> 47-82% cost savings tested against the Nous Research Inference API.
	Zero code changes required.
</div>

<!-- Quick Start -->
<h2 class="docs-h2">Quick Start</h2>

<p class="docs-p">Get RuleShield running with the npm setup flow.</p>

<h3 class="docs-h3">Step 1: Install</h3>
<pre class="docs-pre"><span class="comment"># Clone and run guided Hermes setup</span>
git clone https://github.com/banse/RuleShield.git
<span class="keyword">cd</span> RuleShield
npm run setup:hermes</pre>

<p class="docs-p">
	This creates <code class="docs-code">~/.ruleshield/</code> with your configuration file and
	default rule set and patches your Hermes Agent config to route through the proxy.
</p>

<h3 class="docs-h3">Step 2: Start</h3>
<pre class="docs-pre"><span class="comment"># Start the proxy server</span>
npm run start</pre>

<p class="docs-p">
	Open <code class="docs-code">http://127.0.0.1:8347/test-monitor</code> (temporary default start page)
	and run your demo/test scripts from a second terminal.
	Costs drop immediately. No code changes needed.
</p>

<!-- Architecture Overview -->
<h2 class="docs-h2">Architecture Overview</h2>

<p class="docs-p">
	Every request passes through five layers. The first layer that can handle it wins, avoiding
	unnecessary LLM calls and reducing cost.
</p>

<div class="docs-pre" style="line-height: 1.8; font-size: 0.8rem;">
<span class="text-text-primary font-semibold">Request Flow (5-Layer Pipeline)</span>

  <span class="text-text-muted">Client</span>
    <span class="text-text-muted">|</span>
    <span class="text-text-muted">v</span>
  <span class="text-accent">[Layer 1: Cache]</span>              <span class="text-text-muted">-- Exact + semantic match ........... $0.000</span>
    <span class="text-text-muted">|  miss</span>
    <span class="text-text-muted">v</span>
  <span class="text-primary">[Layer 2: Rules]</span>              <span class="text-text-muted">-- 75 rules, 4 packs ............... $0.000</span>
    <span class="text-text-muted">|  miss</span>
    <span class="text-text-muted">v</span>
  <span class="text-accent">[Layer 3: Template Optimizer]</span>  <span class="text-text-muted">-- Prompt trimming + templates ..... $0.000</span>
    <span class="text-text-muted">|  miss</span>
    <span class="text-text-muted">v</span>
  <span class="text-warning">[Layer 4: Bridge]</span>             <span class="text-text-muted">-- Local Hermes on cheap model ..... ~$0.001</span>
    <span class="text-text-muted">|  miss</span>
    <span class="text-text-muted">v</span>
  <span class="text-routed">[Layer 5: Router]</span>             <span class="text-text-muted">-- Complexity-based model routing ... varies</span>
    <span class="text-text-muted">|</span>
    <span class="text-text-muted">v</span>
  <span class="text-text-muted">Upstream LLM (80+ models, with provider retry)</span>
    <span class="text-text-muted">|</span>
    <span class="text-text-muted">v</span>
  <span class="text-error">Feedback Loop</span>                 <span class="text-text-muted">-- Accept/reject -> auto-promote rules</span>
</div>

<!-- Installation -->
<h2 class="docs-h2" id="installation">Installation</h2>

<h3 class="docs-h3">Prerequisites</h3>
<ul class="docs-p list-disc list-inside space-y-1">
	<li>Python 3.10 or higher</li>
	<li>pip (or uv, pipx)</li>
	<li>An API key for your LLM provider</li>
</ul>

<h3 class="docs-h3">Install with pip (from source)</h3>
<pre class="docs-pre">git clone https://github.com/banse/RuleShield.git
<span class="keyword">cd</span> RuleShield
pip install <span class="flag">-e</span> .</pre>

<h3 class="docs-h3">Install from source</h3>
<pre class="docs-pre">git clone https://github.com/banse/RuleShield.git
<span class="keyword">cd</span> RuleShield
pip install <span class="flag">-e</span> .</pre>

<h3 class="docs-h3">Set your API key</h3>
<pre class="docs-pre"><span class="comment"># Set via environment variable (recommended)</span>
<span class="keyword">export</span> RULESHIELD_API_KEY=<span class="string">sk-your-key-here</span>

<span class="comment"># Or add to ~/.ruleshield/config.yaml</span>
api_key: <span class="string">sk-your-key-here</span></pre>

<!-- Documentation Sections -->
<h2 class="docs-h2">Documentation</h2>

<div class="grid grid-cols-1 gap-3">
	<a href="/docs/architecture" class="docs-card block no-underline">
		<div class="flex items-start gap-3">
			<div class="text-primary text-xl mt-0.5">
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
						d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
				</svg>
			</div>
			<div>
				<h3 class="text-text-primary font-semibold text-sm">Architecture</h3>
				<p class="text-text-muted text-xs mt-1">5-layer pipeline, template optimizer, smart routing, shadow mode, and the feedback loop explained.</p>
			</div>
		</div>
	</a>

	<a href="/docs/hermes" class="docs-card block no-underline">
		<div class="flex items-start gap-3">
			<div class="text-primary text-xl mt-0.5">
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
						d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
				</svg>
			</div>
			<div>
				<h3 class="text-text-primary font-semibold text-sm">Hermes Agent Integration</h3>
				<p class="text-text-muted text-xs mt-1">Skills, MCP server, config patching, and demo scenarios.</p>
			</div>
		</div>
	</a>

	<a href="/docs/api" class="docs-card block no-underline">
		<div class="flex items-start gap-3">
			<div class="text-primary text-xl mt-0.5">
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
						d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
				</svg>
			</div>
			<div>
				<h3 class="text-text-primary font-semibold text-sm">API & CLI Reference</h3>
				<p class="text-text-muted text-xs mt-1">15 CLI commands, REST endpoints, configuration fields, and environment variables.</p>
			</div>
		</div>
	</a>

	<a href="/docs/cron" class="docs-card block no-underline">
		<div class="flex items-start gap-3">
			<div class="text-primary text-xl mt-0.5">
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
						d="M8 7V3m8 4V3m-9 8h10m-11 9h12a2 2 0 002-2V7a2 2 0 00-2-2H6a2 2 0 00-2 2v11a2 2 0 002 2z" />
				</svg>
			</div>
			<div>
				<h3 class="text-text-primary font-semibold text-sm">Cron Optimizer</h3>
				<p class="text-text-muted text-xs mt-1">Draft, shadow-validate, activate, and execute compact cron profiles.</p>
			</div>
		</div>
	</a>

	<a href="/docs/mcp" class="docs-card block no-underline">
		<div class="flex items-start gap-3">
			<div class="text-primary text-xl mt-0.5">
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
						d="M9 12h6m-9 4h12M7 20h10a2 2 0 002-2V6a2 2 0 00-2-2H7a2 2 0 00-2 2v12a2 2 0 002 2z" />
				</svg>
			</div>
			<div>
				<h3 class="text-text-primary font-semibold text-sm">MCP Server</h3>
				<p class="text-text-muted text-xs mt-1">Tool inventory, JSON-RPC usage, and Hermes MCP configuration.</p>
			</div>
		</div>
	</a>

	<a href="https://github.com/banse/RuleShield/blob/main/docs/rules-engine.md" class="docs-card block no-underline" target="_blank" rel="noopener noreferrer">
		<div class="flex items-start gap-3">
			<div class="text-primary text-xl mt-0.5">
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
						d="M9 12h6m-6 4h6M7 4h10a2 2 0 012 2v12a2 2 0 01-2 2H7a2 2 0 01-2-2V6a2 2 0 012-2z" />
				</svg>
			</div>
			<div>
				<h3 class="text-text-primary font-semibold text-sm">Rules Engine Reference</h3>
				<p class="text-text-muted text-xs mt-1">Weighted scoring, model thresholds, shadow mode, feedback updates, deactivation, and promotion logic.</p>
			</div>
		</div>
	</a>

	<a href="https://github.com/banse/RuleShield/blob/main/docs/rules-engine-operations.md" class="docs-card block no-underline" target="_blank" rel="noopener noreferrer">
		<div class="flex items-start gap-3">
			<div class="text-primary text-xl mt-0.5">
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
						d="M9 17v-6m3 6V7m3 10v-3M5 21h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v14a2 2 0 002 2z" />
				</svg>
			</div>
			<div>
				<h3 class="text-text-primary font-semibold text-sm">Rule Operations Guide</h3>
				<p class="text-text-muted text-xs mt-1">How to run day-in-the-life tests, read shadow results, and decide when to tune, pause, or promote rules.</p>
			</div>
		</div>
	</a>

	<a href="https://github.com/banse/RuleShield/blob/main/docs/cron-optimization-spec.md" class="docs-card block no-underline" target="_blank" rel="noopener noreferrer">
		<div class="flex items-start gap-3">
			<div class="text-primary text-xl mt-0.5">
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
						d="M8 7V3m8 4V3m-9 8h10m-11 9h12a2 2 0 002-2V7a2 2 0 00-2-2H6a2 2 0 00-2 2v11a2 2 0 002 2z" />
				</svg>
			</div>
			<div>
				<h3 class="text-text-primary font-semibold text-sm">Cron Optimization Spec</h3>
				<p class="text-text-muted text-xs mt-1">Hammock design for recurring-task optimization, prompt decomposition, compact Hermes calls, and validation strategy.</p>
			</div>
		</div>
	</a>

	<a href="https://github.com/banse/RuleShield/blob/main/docs/cron-optimizer-quickstart.md" class="docs-card block no-underline" target="_blank" rel="noopener noreferrer">
		<div class="flex items-start gap-3">
			<div class="text-primary text-xl mt-0.5">
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
						d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
				</svg>
			</div>
			<div>
				<h3 class="text-text-primary font-semibold text-sm">Cron Optimizer Quickstart (5 Minutes)</h3>
				<p class="text-text-muted text-xs mt-1">Fastest path: open Cron Lab, run shadow, activate profile, execute with dynamic payload.</p>
			</div>
		</div>
	</a>

	<a href="https://github.com/banse/RuleShield/blob/main/docs/cron-optimizer-user-guide.md" class="docs-card block no-underline" target="_blank" rel="noopener noreferrer">
		<div class="flex items-start gap-3">
			<div class="text-primary text-xl mt-0.5">
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
						d="M12 6v6l4 2m6-2a10 10 0 11-20 0 10 10 0 0120 0z" />
				</svg>
			</div>
			<div>
				<h3 class="text-text-primary font-semibold text-sm">Cron Optimizer User Guide</h3>
				<p class="text-text-muted text-xs mt-1">Practical operator guide: draft, shadow validate, activate, execute, monitor, and lifecycle actions.</p>
			</div>
		</div>
	</a>

	<a href="https://github.com/banse/RuleShield/blob/main/docs/cron-optimization-implementation-plan.md" class="docs-card block no-underline" target="_blank" rel="noopener noreferrer">
		<div class="flex items-start gap-3">
			<div class="text-primary text-xl mt-0.5">
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
						d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
				</svg>
			</div>
			<div>
				<h3 class="text-text-primary font-semibold text-sm">Cron Implementation Plan</h3>
				<p class="text-text-muted text-xs mt-1">Concrete modules, storage, CLI and API shape, phased rollout, and testing strategy for the cron optimizer.</p>
			</div>
		</div>
	</a>

	<a href="https://github.com/banse/RuleShield/blob/main/docs/cron-runtime-guide.md" class="docs-card block no-underline" target="_blank" rel="noopener noreferrer">
		<div class="flex items-start gap-3">
			<div class="text-primary text-xl mt-0.5">
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
						d="M13 10V3L4 14h7v7l9-11h-7z" />
				</svg>
			</div>
			<div>
				<h3 class="text-text-primary font-semibold text-sm">Cron Runtime Guide</h3>
				<p class="text-text-muted text-xs mt-1">How to call active cron profiles from Hermes, Python, and external schedulers with the compact execution endpoint.</p>
			</div>
		</div>
	</a>

	<a href="/docs/langchain" class="docs-card block no-underline">
		<div class="flex items-start gap-3">
			<div class="text-primary text-xl mt-0.5">
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
						d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
				</svg>
			</div>
			<div>
				<h3 class="text-text-primary font-semibold text-sm">LangChain Integration</h3>
				<p class="text-text-muted text-xs mt-1">Use RuleShield as a drop-in proxy for LangChain applications.</p>
			</div>
		</div>
	</a>

	<a href="/docs/crewai" class="docs-card block no-underline">
		<div class="flex items-start gap-3">
			<div class="text-primary text-xl mt-0.5">
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
						d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
				</svg>
			</div>
			<div>
				<h3 class="text-text-primary font-semibold text-sm">CrewAI Integration</h3>
				<p class="text-text-muted text-xs mt-1">Optimize multi-agent CrewAI workflows with RuleShield cost savings.</p>
			</div>
		</div>
	</a>
</div>

<!-- Results -->
<h2 class="docs-h2">Proven Results</h2>

<table class="docs-table">
	<thead>
		<tr>
			<th>Scenario</th>
			<th>Savings</th>
			<th>How</th>
		</tr>
	</thead>
	<tbody>
		<tr>
			<td>Morning Workflow (greetings, status)</td>
			<td><span class="text-accent font-mono font-semibold">82%</span></td>
			<td>Mostly cache + rules</td>
		</tr>
		<tr>
			<td>Code Review (analysis tasks)</td>
			<td><span class="text-accent font-mono font-semibold">47%</span></td>
			<td>Router saves on simple reviews</td>
		</tr>
		<tr>
			<td>Research Session (complex queries)</td>
			<td><span class="text-accent font-mono font-semibold">52%</span></td>
			<td>Bridge + Router split</td>
		</tr>
		<tr>
			<td>Cron-style Recurring Tasks</td>
			<td><span class="text-accent font-mono font-semibold">78%</span></td>
			<td>Cache dominates</td>
		</tr>
	</tbody>
</table>

<table class="docs-table">
	<thead>
		<tr>
			<th>Metric</th>
			<th>Value</th>
		</tr>
	</thead>
	<tbody>
		<tr>
			<td>Cache/rule response time</td>
			<td><code class="docs-code">&lt;5ms</code></td>
		</tr>
		<tr>
			<td>LLM passthrough overhead</td>
			<td>Negligible</td>
		</tr>
		<tr>
			<td>Setup time</td>
			<td>&lt;2 minutes</td>
		</tr>
		<tr>
			<td>Code changes required</td>
			<td>Zero</td>
		</tr>
	</tbody>
</table>
