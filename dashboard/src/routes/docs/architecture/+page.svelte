<script lang="ts">
	// Architecture documentation -- static content, no server dependencies
</script>

<h1 class="docs-h1">Architecture</h1>
<p class="docs-lead">
	RuleShield uses a 5-layer pipeline to intercept LLM requests at the cheapest possible point.
	Every request enters the pipeline and the first layer that can confidently handle it wins.
	Supports 80+ models across OpenAI, Codex, Anthropic, Google, DeepSeek, Nous/Hermes, and Ollama.
</p>

<!-- Pipeline Overview -->
<h2 class="docs-h2">5-Layer Pipeline</h2>

<p class="docs-p">
	The pipeline is ordered by cost: free layers fire first, progressively more expensive layers
	handle what the cheaper ones cannot.
</p>

<div class="docs-pre" style="line-height: 1.8; font-size: 0.8rem;">
<span class="text-text-primary font-semibold">Pipeline Execution Order</span>

  <span class="text-accent">Layer 1: Semantic Cache</span>         <span class="text-text-muted">cost: $0.000    latency: &lt;1ms</span>
  <span class="text-primary">Layer 2: Rule Engine</span>           <span class="text-text-muted">cost: $0.000    latency: &lt;2ms</span>
  <span class="text-accent">Layer 3: Template Optimizer</span>    <span class="text-text-muted">cost: $0.000    latency: &lt;1ms</span>
  <span class="text-warning">Layer 4: Hermes Bridge</span>        <span class="text-text-muted">cost: ~$0.001   latency: ~500ms</span>
  <span class="text-routed">Layer 5: Smart Router</span>         <span class="text-text-muted">cost: varies    latency: varies</span>

  <span class="text-text-muted">Each layer returns a confidence score.</span>
  <span class="text-text-muted">If confidence >= threshold, the response is served.</span>
  <span class="text-text-muted">If not, the request falls through to the next layer.</span>
</div>

<!-- Layer 1: Cache -->
<h2 class="docs-h2">Layer 1: Semantic Cache</h2>

<p class="docs-p">
	Two-tier caching that catches identical and near-identical requests before they ever reach an LLM.
</p>

<h3 class="docs-h3">Exact Match</h3>
<p class="docs-p">
	SHA-256 hash of the full prompt. If the same prompt has been seen before, the cached response
	is returned instantly. This handles repeated system prompts, status checks, and duplicate requests.
</p>

<h3 class="docs-h3">Semantic Match</h3>
<p class="docs-p">
	When exact match misses, RuleShield computes sentence-transformer embeddings and checks cosine
	similarity against cached entries. The default threshold is <code class="docs-code">0.92</code>.
</p>

<div class="docs-note">
	<strong>Example:</strong> "What's the weather?" and "Tell me the weather" have different hashes but
	near-identical semantics. The semantic cache catches both after the first call.
</div>

<h3 class="docs-h3">Configuration</h3>
<table class="docs-table">
	<thead>
		<tr>
			<th>Setting</th>
			<th>Default</th>
			<th>Description</th>
		</tr>
	</thead>
	<tbody>
		<tr>
			<td><code class="docs-code">cache_enabled</code></td>
			<td><code class="docs-code">true</code></td>
			<td>Enable or disable the cache layer entirely</td>
		</tr>
	</tbody>
</table>

<!-- Layer 2: Rules -->
<h2 class="docs-h2" id="rule-engine">Layer 2: SAP-Inspired Rule Engine</h2>

<p class="docs-p">
	A pattern-matching engine inspired by enterprise rule systems. Rules define patterns to match against
	incoming prompts and provide pre-defined responses when confidence is high enough.
</p>

<h3 class="docs-h3">Rule Structure</h3>
<pre class="docs-pre"><span class="comment">// Example rule from default_hermes.json</span>
&#123;
  <span class="string">"id"</span>: <span class="string">"greeting"</span>,
  <span class="string">"name"</span>: <span class="string">"Greeting Handler"</span>,
  <span class="string">"patterns"</span>: [
    &#123;<span class="string">"type"</span>: <span class="string">"contains"</span>, <span class="string">"value"</span>: <span class="string">"hello"</span>, <span class="string">"field"</span>: <span class="string">"last_user_message"</span>&#125;,
    &#123;<span class="string">"type"</span>: <span class="string">"regex"</span>, <span class="string">"value"</span>: <span class="string">"^(hi|hey|greetings)"</span>, <span class="string">"field"</span>: <span class="string">"last_user_message"</span>&#125;
  ],
  <span class="string">"response"</span>: &#123;<span class="string">"content"</span>: <span class="string">"Hello! How can I help you?"</span>&#125;,
  <span class="string">"confidence"</span>: <span class="keyword">0.95</span>,
  <span class="string">"priority"</span>: <span class="keyword">10</span>,
  <span class="string">"enabled"</span>: <span class="keyword">true</span>
&#125;</pre>

<h3 class="docs-h3">Pattern Types</h3>
<table class="docs-table">
	<thead>
		<tr>
			<th>Type</th>
			<th>Behavior</th>
			<th>Example</th>
		</tr>
	</thead>
	<tbody>
		<tr>
			<td><code class="docs-code">exact</code></td>
			<td>Full string equality</td>
			<td><code class="docs-code">"hello"</code></td>
		</tr>
		<tr>
			<td><code class="docs-code">contains</code></td>
			<td>Substring presence</td>
			<td><code class="docs-code">"status"</code></td>
		</tr>
		<tr>
			<td><code class="docs-code">startswith</code></td>
			<td>Prefix match</td>
			<td><code class="docs-code">"hey"</code></td>
		</tr>
		<tr>
			<td><code class="docs-code">regex</code></td>
			<td>Regular expression</td>
			<td><code class="docs-code">"^(hi|hey|greetings)"</code></td>
		</tr>
	</tbody>
</table>

<h3 class="docs-h3">Confidence Levels</h3>
<p class="docs-p">
	Each rule carries a confidence score between 0 and 1. The score determines whether the
	rule's response is served or the request falls through to the next layer.
</p>

<table class="docs-table">
	<thead>
		<tr>
			<th>Level</th>
			<th>Score Range</th>
			<th>Behavior</th>
		</tr>
	</thead>
	<tbody>
		<tr>
			<td><span class="docs-badge bg-accent/20 text-accent">CONFIRMED</span></td>
			<td><code class="docs-code">0.90 - 1.00</code></td>
			<td>Response served immediately</td>
		</tr>
		<tr>
			<td><span class="docs-badge bg-warning/20 text-warning">LIKELY</span></td>
			<td><code class="docs-code">0.70 - 0.89</code></td>
			<td>Response served, flagged for review</td>
		</tr>
		<tr>
			<td><span class="docs-badge bg-text-muted/20 text-text-muted">POSSIBLE</span></td>
			<td><code class="docs-code">0.50 - 0.69</code></td>
			<td>Falls through to next layer</td>
		</tr>
	</tbody>
</table>

<h3 class="docs-h3">Auto-Extraction</h3>
<p class="docs-p">
	RuleShield automatically observes traffic and generates new rule candidates from recurring patterns.
	The extractor identifies prompts that appear frequently, clusters them by similarity, and proposes
	new rules with conservative initial confidence scores.
</p>

<h3 class="docs-h3">Default Rules</h3>
<p class="docs-p">
	RuleShield ships with 75 rules across 4 rule packs: 8 default rules for common Hermes patterns,
	12 advanced rules, 30 customer support rules, and 25 coding assistant rules. Default rules cover
	greetings, confirmations, status checks, acknowledgments, and simple questions. All rules fire in under 2ms.
</p>

<h3 class="docs-h3">Configuration</h3>
<table class="docs-table">
	<thead>
		<tr>
			<th>Setting</th>
			<th>Default</th>
			<th>Description</th>
		</tr>
	</thead>
	<tbody>
		<tr>
			<td><code class="docs-code">rules_enabled</code></td>
			<td><code class="docs-code">true</code></td>
			<td>Enable or disable the rule engine</td>
		</tr>
		<tr>
			<td><code class="docs-code">rules_dir</code></td>
			<td><code class="docs-code">~/.ruleshield/rules/</code></td>
			<td>Directory containing JSON rule files</td>
		</tr>
	</tbody>
</table>

<!-- Layer 3: Template Optimizer -->
<h2 class="docs-h2">Layer 3: Template Optimizer</h2>

<p class="docs-p">
	The Template Optimizer discovers recurring prompt structures and converts them into reusable templates.
	When a request matches a known template, only the variable portions are sent to the LLM, reducing
	token usage without changing output quality.
</p>

<h3 class="docs-h3">How It Works</h3>
<ul class="docs-p list-disc list-inside space-y-1">
	<li><strong>Template Discovery</strong> -- Analyzes traffic to identify prompts with shared structure but varying inputs</li>
	<li><strong>Variable Extraction</strong> -- Splits templates into fixed structure (cached) and dynamic variables (sent to LLM)</li>
	<li><strong>Auto-Activation</strong> -- Templates that consistently match are promoted to active status automatically</li>
</ul>

<h3 class="docs-h3">CLI Commands</h3>
<pre class="docs-pre"><span class="comment"># Discover template candidates from recent traffic</span>
ruleshield discover-templates

<span class="comment"># List active templates and their hit rates</span>
ruleshield templates</pre>

<h3 class="docs-h3">Configuration</h3>
<table class="docs-table">
	<thead>
		<tr>
			<th>Setting</th>
			<th>Default</th>
			<th>Description</th>
		</tr>
	</thead>
	<tbody>
		<tr>
			<td><code class="docs-code">prompt_trimming_enabled</code></td>
			<td><code class="docs-code">true</code></td>
			<td>Enable prompt trimming and template optimization</td>
		</tr>
	</tbody>
</table>

<!-- Layer 4: Bridge -->
<h2 class="docs-h2">Layer 4: Hermes Bridge</h2>

<p class="docs-p">
	An optional layer that runs a local Hermes Agent instance on a cheap model (e.g., Claude Haiku).
	Requests too complex for rules but too simple for premium models get routed here.
</p>

<div class="docs-warning">
	<strong>Optional layer.</strong> The bridge is disabled by default. Enable it when you have a local
	or low-cost model endpoint available for medium-complexity tasks.
</div>

<h3 class="docs-h3">Configuration</h3>
<table class="docs-table">
	<thead>
		<tr>
			<th>Setting</th>
			<th>Default</th>
			<th>Description</th>
		</tr>
	</thead>
	<tbody>
		<tr>
			<td><code class="docs-code">hermes_bridge_enabled</code></td>
			<td><code class="docs-code">false</code></td>
			<td>Enable the Hermes Bridge layer</td>
		</tr>
		<tr>
			<td><code class="docs-code">hermes_bridge_model</code></td>
			<td><code class="docs-code">claude-haiku-4-5</code></td>
			<td>Model to use for bridge requests</td>
		</tr>
	</tbody>
</table>

<!-- Layer 5: Router -->
<h2 class="docs-h2">Layer 5: Smart Model Router</h2>

<p class="docs-p">
	When a request reaches this layer, RuleShield analyzes its complexity and routes it to the cheapest
	model capable of handling it. The complexity classifier scores each request on a 1-10 scale.
</p>

<h3 class="docs-h3">Complexity Scoring</h3>
<p class="docs-p">The classifier uses four signals to score request complexity:</p>
<ul class="docs-p list-disc list-inside space-y-1">
	<li><strong>Prompt length</strong> -- longer prompts tend to be more complex</li>
	<li><strong>Message count</strong> -- multi-turn conversations score higher</li>
	<li><strong>Keyword analysis</strong> -- terms like "analyze", "compare", "explain in depth" increase score</li>
	<li><strong>Question type</strong> -- factual queries score lower than open-ended reasoning</li>
</ul>

<h3 class="docs-h3">Routing Table</h3>
<table class="docs-table">
	<thead>
		<tr>
			<th>Complexity</th>
			<th>Score</th>
			<th>Routing</th>
			<th>Typical Cost</th>
		</tr>
	</thead>
	<tbody>
		<tr>
			<td><span class="docs-badge bg-accent/20 text-accent">Simple</span></td>
			<td>1-3</td>
			<td>Cheap model (e.g., GPT-4o-mini)</td>
			<td><code class="docs-code">~$0.001</code></td>
		</tr>
		<tr>
			<td><span class="docs-badge bg-warning/20 text-warning">Medium</span></td>
			<td>4-7</td>
			<td>Mid-tier model</td>
			<td><code class="docs-code">~$0.005</code></td>
		</tr>
		<tr>
			<td><span class="docs-badge bg-error/20 text-error">Complex</span></td>
			<td>8-10</td>
			<td>Premium model (e.g., Opus)</td>
			<td><code class="docs-code">~$0.015</code></td>
		</tr>
	</tbody>
</table>

<h3 class="docs-h3">Configuration</h3>
<table class="docs-table">
	<thead>
		<tr>
			<th>Setting</th>
			<th>Default</th>
			<th>Description</th>
		</tr>
	</thead>
	<tbody>
		<tr>
			<td><code class="docs-code">router_enabled</code></td>
			<td><code class="docs-code">true</code></td>
			<td>Enable smart model routing</td>
		</tr>
		<tr>
			<td><code class="docs-code">router_config</code></td>
			<td><code class="docs-code">&#123;&#125;</code></td>
			<td>Custom model mappings (optional)</td>
		</tr>
	</tbody>
</table>

<!-- Model-Aware Confidence -->
<h2 class="docs-h2">Model-Aware Confidence Thresholds</h2>

<p class="docs-p">
	Confidence thresholds are not static. RuleShield adjusts them based on the model the request
	would have been routed to. If a request targets a cheap model, the confidence threshold for
	rule interception is lower (rules are more willing to fire). For premium models, thresholds
	are higher, meaning rules only fire when they are very confident.
</p>

<p class="docs-p">
	This prevents rules from accidentally intercepting complex requests where a wrong answer is costly,
	while being aggressive about intercepting cheap requests where the downside of a miss is minimal.
</p>

<!-- Shadow Mode -->
<h2 class="docs-h2">Shadow Mode</h2>

<p class="docs-p">
	Shadow mode lets you test rules without risk. When enabled, RuleShield runs both the rule engine
	and the real LLM in parallel. The rule response is logged but discarded -- only the real LLM
	response is returned to the client.
</p>

<pre class="docs-pre"><span class="comment"># Enable shadow mode in config</span>
shadow_mode: <span class="keyword">true</span>

<span class="comment"># Or via environment variable</span>
<span class="keyword">export</span> RULESHIELD_SHADOW_MODE=<span class="string">true</span></pre>

<h3 class="docs-h3">How Shadow Mode Works</h3>
<ol class="docs-p list-decimal list-inside space-y-2">
	<li>Request arrives at the proxy</li>
	<li>Rules evaluate and produce a candidate response</li>
	<li>The request is also forwarded to the real LLM</li>
	<li>Both responses are logged with a similarity comparison</li>
	<li>Only the real LLM response is returned to the client</li>
</ol>

<h3 class="docs-h3">Reviewing Shadow Results</h3>
<pre class="docs-pre"><span class="comment"># View shadow mode comparison statistics</span>
ruleshield shadow-stats</pre>

<p class="docs-p">
	Rules with similarity above 80% are flagged as <span class="docs-badge bg-accent/20 text-accent">READY</span>
	for activation. Rules below 40% are flagged as <span class="docs-badge bg-error/20 text-error">LOW</span>
	and should be revised or removed.
</p>

<!-- Feedback Loop -->
<h2 class="docs-h2">Feedback Loop</h2>

<p class="docs-p">
	RuleShield learns from your feedback using bandit-style confidence updates. Accept or reject any
	intercepted response, and the system adjusts rule confidence scores accordingly.
</p>

<pre class="docs-pre"><span class="comment"># Review recent interceptions and feedback stats</span>
ruleshield feedback

<span class="comment"># Accept a good interception (boosts rule confidence)</span>
ruleshield feedback <span class="flag">--accept</span> &lt;request-id&gt;

<span class="comment"># Reject a bad one (lowers confidence)</span>
ruleshield feedback <span class="flag">--reject</span> &lt;request-id&gt;</pre>

<h3 class="docs-h3">How Confidence Updates Work</h3>
<ul class="docs-p list-disc list-inside space-y-1">
	<li><strong>Accept</strong> -- Rule confidence increases. The rule fires more often.</li>
	<li><strong>Reject</strong> -- Rule confidence decreases. Below a threshold, the rule auto-disables.</li>
	<li>Updates use a bandit-style algorithm that balances exploration and exploitation</li>
	<li>Rules that consistently get rejected stop firing without manual intervention</li>
</ul>

<h3 class="docs-h3">RL Training Stubs</h3>
<p class="docs-p">
	The feedback loop lays the groundwork for reinforcement learning. Interface stubs are in place for:
</p>
<ul class="docs-p list-disc list-inside space-y-1">
	<li><strong>GRPO/Atropos</strong> -- Group Relative Policy Optimization for rule quality</li>
	<li><strong>DSPy/GEPA</strong> -- Guided Evolution for Prompt-based Agents</li>
</ul>
<p class="docs-p">
	These are not yet active but define the path toward an agent that evolves its own optimization strategy.
</p>

<!-- Prompt Trimming -->
<h2 class="docs-h2">Prompt Trimming</h2>

<p class="docs-p">
	RuleShield splits requests into known and unknown parts. System prompts that repeat every call
	get cached separately. Only the novel user content counts toward API costs.
</p>

<p class="docs-p">
	This is especially effective for agents that include large system prompts with every request --
	a common pattern that can account for 50-70% of token usage.
</p>

<!-- Auto Rule Activation -->
<h2 class="docs-h2">Auto Rule Activation</h2>

<p class="docs-p">
	Rules in shadow mode that consistently match real LLM responses can be promoted to active
	status automatically. The auto-promote system monitors shadow comparison scores and activates
	rules that exceed the similarity threshold.
</p>

<pre class="docs-pre"><span class="comment"># Manually promote a specific rule from shadow to active</span>
ruleshield promote-rule &lt;rule-id&gt;

<span class="comment"># Auto-promote all rules that exceed the similarity threshold</span>
ruleshield auto-promote</pre>

<p class="docs-p">
	This closes the loop between shadow testing and production deployment, allowing rules to
	graduate from observation to interception without manual intervention.
</p>

<!-- Provider Retry -->
<h2 class="docs-h2">Provider Retry with Exponential Backoff</h2>

<p class="docs-p">
	When upstream LLM providers return transient errors (rate limits, timeouts, server errors),
	RuleShield automatically retries with exponential backoff. This prevents cascading failures
	and improves reliability without any client-side retry logic.
</p>

<h3 class="docs-h3">Configuration</h3>
<table class="docs-table">
	<thead>
		<tr>
			<th>Setting</th>
			<th>Default</th>
			<th>Description</th>
		</tr>
	</thead>
	<tbody>
		<tr>
			<td><code class="docs-code">max_retries</code></td>
			<td><code class="docs-code">3</code></td>
			<td>Maximum number of retry attempts on transient failures</td>
		</tr>
	</tbody>
</table>

<!-- Codex Support -->
<h2 class="docs-h2">Codex Responses API Support</h2>

<p class="docs-p">
	RuleShield supports the OpenAI Codex Responses API as a passthrough endpoint. Codex requests
	are forwarded to the upstream provider with all RuleShield optimizations applied, including
	caching, rule matching, and smart routing.
</p>

<pre class="docs-pre"><span class="comment"># Codex endpoints supported:</span>
POST /responses                <span class="text-text-muted">-- Codex Responses API passthrough</span>
POST /chat/completions         <span class="text-text-muted">-- Codex-compatible (without /v1/ prefix)</span></pre>

<p class="docs-p">
	This allows RuleShield to optimize Codex workloads alongside standard chat completions,
	extending cost savings to code generation and analysis tasks.
</p>
