<script lang="ts">
	// Hermes Agent integration guide -- static content, no server dependencies
</script>

<h1 class="docs-h1">Hermes Agent Integration</h1>
<p class="docs-lead">
	RuleShield integrates with the Hermes Agent ecosystem at three levels: config patching,
	Skills for in-agent reporting, and an MCP server for deep programmatic access.
</p>

<!-- Setup -->
<h2 class="docs-h2">Setup</h2>

<p class="docs-p">
	Initialize RuleShield with Hermes integration enabled. This automatically patches your Hermes
	Agent configuration to route all LLM requests through the RuleShield proxy.
</p>

<pre class="docs-pre">ruleshield init <span class="flag">--hermes</span></pre>

<p class="docs-p">This command performs four steps:</p>

<ol class="docs-p list-decimal list-inside space-y-2">
	<li>Creates <code class="docs-code">~/.ruleshield/</code> directory</li>
	<li>Writes default <code class="docs-code">config.yaml</code></li>
	<li>Installs 8 default rules for common Hermes patterns</li>
	<li>Patches <code class="docs-code">~/.hermes/config.yaml</code> to point <code class="docs-code">model.base_url</code> at the proxy, or creates a minimal starter config if none exists</li>
</ol>

<div class="docs-note">
	<strong>Non-destructive.</strong> RuleShield saves your original Hermes <code class="docs-code">base_url</code>
	before patching when one already exists. Use <code class="docs-code">ruleshield restore-hermes</code> to restore it later.
</div>

<!-- How Config Patching Works -->
<h2 class="docs-h2">How Config Patching Works</h2>

<p class="docs-p">
	When you run <code class="docs-code">ruleshield init --hermes</code>, RuleShield reads your
	Hermes config at <code class="docs-code">~/.hermes/config.yaml</code> and updates the
	<code class="docs-code">model.base_url</code> field to point to the proxy. If the file does not
	exist yet, RuleShield creates a minimal starter config for a normal local Hermes setup.
</p>

<h3 class="docs-h3">Before</h3>
<!-- nosec - documentation placeholder, not a real API key -->
<pre class="docs-pre"><span class="comment"># ~/.hermes/config.yaml</span>
model:
  base_url: <span class="string">https://api.openai.com/v1</span>
  model_name: gpt-4o
  api_key: sk-...</pre>

<h3 class="docs-h3">After</h3>
<!-- nosec - documentation placeholder, not a real API key -->
<pre class="docs-pre"><span class="comment"># ~/.hermes/config.yaml (patched by RuleShield)</span>
model:
  base_url: <span class="string">http://127.0.0.1:8347/v1</span>
  model_name: gpt-4o
  api_key: sk-...</pre>

<p class="docs-p">
	The original <code class="docs-code">base_url</code> is saved to
	<code class="docs-code">~/.ruleshield/hermes_original_url.txt</code> so it can be restored later.
</p>

<h3 class="docs-h3">Blank Start</h3>
<p class="docs-p">
	If you are starting from a fresh Hermes install with no existing config, RuleShield creates a
	minimal starter config with a local proxy <code class="docs-code">base_url</code> and default
	Codex-style model settings. You can change provider or model later in Hermes as needed.
</p>

<h3 class="docs-h3">Restore</h3>
<pre class="docs-pre">ruleshield restore-hermes</pre>

<h2 class="docs-h2">Auth Expectations</h2>

<p class="docs-p">
	RuleShield does not store provider secrets in the repository. A normal local Hermes setup should keep
	auth in your local Hermes or Codex home, for example:
</p>

<ul class="docs-p list-disc list-inside space-y-2">
	<li><code class="docs-code">~/.codex/auth.json</code> for OpenAI OAuth / Codex-style local auth</li>
	<li><code class="docs-code">~/.hermes/.env</code> for local provider API keys such as OpenRouter</li>
	<li>environment variables in your local shell if you prefer that flow</li>
</ul>

<h2 class="docs-h2">Verify It Works</h2>

<ol class="docs-p list-decimal list-inside space-y-2">
	<li>Run <code class="docs-code">ruleshield start</code></li>
	<li>Start Hermes normally</li>
	<li>Send a simple prompt like <code class="docs-code">hello</code></li>
	<li>Confirm RuleShield saw traffic via <code class="docs-code">ruleshield stats</code> or the dashboard</li>
</ol>

<h3 class="docs-h3">Manual Configuration</h3>
<p class="docs-p">
	If your Hermes config is not at the default path, set the <code class="docs-code">base_url</code>
	manually:
</p>
<pre class="docs-pre"><span class="comment"># Point any OpenAI-compatible client at the proxy</span>
base_url: <span class="string">http://127.0.0.1:&lt;PORT&gt;/v1</span></pre>

<!-- Hermes Skill -->
<h2 class="docs-h2">Hermes Skill</h2>

<p class="docs-p">
	RuleShield ships with a Hermes Skill called <code class="docs-code">ruleshield-optimizer</code>
	that lets your agent query its own cost-saving performance during conversations.
</p>

<h3 class="docs-h3">Skill Structure</h3>
<pre class="docs-pre">skills/ruleshield-optimizer/
  SKILL.md              <span class="comment"># Skill definition and trigger words</span>
  MEMORY.md             <span class="comment"># Self-optimization memory (auto-updated)</span>
  scripts/
    analyze_costs.py    <span class="comment"># Current session cost analysis</span>
    suggest_rules.py    <span class="comment"># Rule suggestions from traffic patterns</span>
    estimate_cost.py    <span class="comment"># Cost estimation for a prompt</span></pre>

<h3 class="docs-h3">What the Agent Can Do</h3>

<p class="docs-p">
	Once the skill is installed, your Hermes Agent responds to natural language queries about costs:
</p>

<table class="docs-table">
	<thead>
		<tr>
			<th>You Say</th>
			<th>Agent Does</th>
		</tr>
	</thead>
	<tbody>
		<tr>
			<td>"Show me my cost savings"</td>
			<td>Runs <code class="docs-code">analyze_costs.py</code> -- full breakdown of requests, cache hits, rule hits, router decisions, dollars saved</td>
		</tr>
		<tr>
			<td>"What rules have you learned?"</td>
			<td>Runs <code class="docs-code">suggest_rules.py</code> -- lists active rules with hit counts, confidence scores, and new candidates</td>
		</tr>
		<tr>
			<td>"How much would this cost?"</td>
			<td>Runs <code class="docs-code">estimate_cost.py</code> -- estimates tokens, cost, and whether cache/rules would handle it</td>
		</tr>
	</tbody>
</table>

<h3 class="docs-h3">Installing the Skill</h3>
<pre class="docs-pre"><span class="comment"># Copy the skill to your Hermes skills directory</span>
cp <span class="flag">-r</span> skills/ruleshield-optimizer ~/.hermes/skills/</pre>

<p class="docs-p">
	The skill triggers automatically when the user mentions keywords like "costs", "expensive",
	"optimize", "savings", or "ruleshield".
</p>

<!-- MCP Server -->
<h2 class="docs-h2">MCP Server</h2>

<p class="docs-p">
	RuleShield provides a dedicated MCP server via JSON-RPC stdio for deep agent integration. Add the MCP server
	to your Hermes config to give your agent programmatic access to cost data.
</p>

<h3 class="docs-h3">Configuration</h3>
<pre class="docs-pre"><span class="comment"># Add to your Hermes MCP config</span>
mcp_servers:
  ruleshield:
    type: stdio
    command: python
    args: ["-m", "ruleshield.mcp_server"]</pre>

<h3 class="docs-h3">Available Tools</h3>
<table class="docs-table">
	<thead>
		<tr>
			<th>Tool</th>
			<th>Description</th>
			<th>Returns</th>
		</tr>
	</thead>
	<tbody>
		<tr>
			<td><code class="docs-code">ruleshield_get_stats</code></td>
			<td>Current session statistics and savings</td>
			<td>Total requests, cache hits, rule hits, routed/llm calls, cost breakdown</td>
		</tr>
		<tr>
			<td><code class="docs-code">ruleshield_estimate_cost</code></td>
			<td>Estimate cost and likely resolution before execution</td>
			<td>Token estimate, predicted cost, cache/rule match prediction</td>
		</tr>
		<tr>
			<td><code class="docs-code">ruleshield_suggest_rules</code></td>
			<td>Suggest new rules from recurring traffic</td>
			<td>Candidate rules with confidence hints</td>
		</tr>
		<tr>
			<td><code class="docs-code">ruleshield_analyze_crons</code></td>
			<td>Detect recurring cron-like workflows</td>
			<td>Workflow clusters and optimization candidates</td>
		</tr>
		<tr>
			<td><code class="docs-code">ruleshield_*_cron_profile</code></td>
			<td>Create, inspect, validate, activate, and run cron profiles</td>
			<td>Draft/active profile objects and execution results</td>
		</tr>
	</tbody>
</table>

<h3 class="docs-h3">Using Tools from Your Agent</h3>
<p class="docs-p">
	Once the MCP server is configured, your agent can call these tools directly in conversation:
</p>

<pre class="docs-pre"><span class="comment">// Agent calls get_stats via MCP</span>
&#123;
  <span class="string">"method"</span>: <span class="string">"tools/call"</span>,
  <span class="string">"params"</span>: &#123;
    <span class="string">"name"</span>: <span class="string">"ruleshield_get_stats"</span>,
    <span class="string">"arguments"</span>: &#123;&#125;
  &#125;
&#125;

<span class="comment">// Response</span>
&#123;
  <span class="string">"total_requests"</span>: <span class="keyword">147</span>,
  <span class="string">"cache_hits"</span>: <span class="keyword">63</span>,
  <span class="string">"rule_hits"</span>: <span class="keyword">31</span>,
  <span class="string">"llm_calls"</span>: <span class="keyword">41</span>,
  <span class="string">"cost_without"</span>: <span class="keyword">4.20</span>,
  <span class="string">"cost_with"</span>: <span class="keyword">0.76</span>,
  <span class="string">"savings_pct"</span>: <span class="keyword">82</span>
&#125;</pre>

<!-- Demo Scenarios -->
<h2 class="docs-h2">Demo Scenarios</h2>

<p class="docs-p">
	RuleShield ships with 4 tested demo scenarios in <code class="docs-code">demo/scenarios/</code>.
	Each scenario simulates a real-world Hermes Agent workload.
</p>

<div class="space-y-3">
	<div class="docs-card">
		<div class="flex items-center gap-2 mb-2">
			<span class="docs-badge bg-accent/20 text-accent">82% savings</span>
			<h3 class="text-text-primary font-semibold text-sm">Morning Workflow</h3>
		</div>
		<p class="text-text-muted text-sm">
			Greetings, status checks, and routine queries. Cache and rules handle the majority.
		</p>
	</div>

	<div class="docs-card">
		<div class="flex items-center gap-2 mb-2">
			<span class="docs-badge bg-warning/20 text-warning">47% savings</span>
			<h3 class="text-text-primary font-semibold text-sm">Code Review</h3>
		</div>
		<p class="text-text-muted text-sm">
			Code analysis tasks. Smart router saves on simple reviews by routing to cheaper models.
		</p>
	</div>

	<div class="docs-card">
		<div class="flex items-center gap-2 mb-2">
			<span class="docs-badge bg-warning/20 text-warning">52% savings</span>
			<h3 class="text-text-primary font-semibold text-sm">Research Session</h3>
		</div>
		<p class="text-text-muted text-sm">
			Complex queries and reasoning tasks. Bridge and Router split the workload by complexity.
		</p>
	</div>

	<div class="docs-card">
		<div class="flex items-center gap-2 mb-2">
			<span class="docs-badge bg-accent/20 text-accent">78% savings</span>
			<h3 class="text-text-primary font-semibold text-sm">Cron-style Recurring Tasks</h3>
		</div>
		<p class="text-text-muted text-sm">
			Scheduled, repeating prompts. Cache dominates since the same prompts recur predictably.
		</p>
	</div>
</div>

<!-- Self-Optimization -->
<h2 class="docs-h2">Self-Optimization</h2>

<p class="docs-p">
	The Hermes Skill includes a <code class="docs-code">MEMORY.md</code> file that the agent updates
	after each session. This creates a self-improvement loop:
</p>

<ol class="docs-p list-decimal list-inside space-y-2">
	<li>Agent handles requests through RuleShield</li>
	<li>At session end, the skill runs <code class="docs-code">analyze_costs.py</code></li>
	<li>Agent writes discoveries to <code class="docs-code">MEMORY.md</code>: which rules worked, which failed, new patterns</li>
	<li>Next session, the agent reads <code class="docs-code">MEMORY.md</code> and applies learnings</li>
</ol>

<div class="docs-note">
	<strong>Key insight:</strong> The agent does not get dumber. It learns when it needs the LLM and when it
	does not. RuleShield makes the agent self-aware about its own cost patterns.
</div>
