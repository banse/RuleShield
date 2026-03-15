<script lang="ts">
	// API and CLI docs -- static content
</script>

<h1 class="docs-h1">API & CLI Reference</h1>
<p class="docs-lead">
	Current reference for RuleShield runtime operations: CLI commands, REST endpoints, and
	OpenAI-compatible proxy routes.
</p>

<h2 class="docs-h2" id="cli">CLI Commands</h2>

<h3 class="docs-h3">Core</h3>
<pre class="docs-pre">ruleshield init [--hermes]
ruleshield start [--port 8337] [--daemon]
ruleshield stop
ruleshield stats
ruleshield rules
ruleshield feedback
ruleshield shadow-stats [--rule RULE_ID] [--recent N]
ruleshield auto-promote [--yes]
ruleshield promote-rule &lt;prompt-hash-or-text&gt; [--yes]
ruleshield discover-templates [--min-cluster N] [--similarity 0.85]
ruleshield templates
ruleshield analyze-crons [--min-occurrences N] [--structured]
ruleshield wrapped [--days N] [--export-path PATH]
ruleshield test-slack</pre>

<h3 class="docs-h3">Cron Optimizer (project CLI module)</h3>
<pre class="docs-pre">python -m ruleshield.cli suggest-cron-profile &lt;prompt-hash-or-text&gt;
python -m ruleshield.cli list-cron-profiles
python -m ruleshield.cli show-cron-profile &lt;profile-id&gt;
python -m ruleshield.cli run-cron-shadow &lt;profile-id&gt; --payload-text "..."
python -m ruleshield.cli activate-cron-profile &lt;profile-id&gt; --yes
python -m ruleshield.cli run-active-cron-profile &lt;profile-id&gt; --payload-text "..."
python -m ruleshield.cli shadow-reset --yes</pre>

<div class="docs-note">
	<strong>Note:</strong> if a packaged <code class="docs-code">ruleshield</code> command is older than
	the local repository code, use <code class="docs-code">python -m ruleshield.cli</code> for full command coverage.
</div>

<h2 class="docs-h2">REST API</h2>
<p class="docs-p">
	Default base URL is <code class="docs-code">http://127.0.0.1:8337</code>.
</p>

<h3 class="docs-h3">Health and Metrics</h3>
<table class="docs-table">
	<thead>
		<tr><th>Endpoint</th><th>Purpose</th></tr>
	</thead>
	<tbody>
		<tr><td><code class="docs-code">GET /health</code></td><td>Service liveness/version</td></tr>
		<tr><td><code class="docs-code">GET /api/stats</code></td><td>Session totals, routing and savings</td></tr>
		<tr><td><code class="docs-code">GET /api/requests?limit=20</code></td><td>Recent request log</td></tr>
		<tr><td><code class="docs-code">GET /api/shadow</code></td><td>Shadow comparison metrics</td></tr>
	</tbody>
</table>

<pre class="docs-pre">curl -s http://127.0.0.1:8337/api/stats

&#123;
  "total_requests": 417,
  "cache_hits": 0,
  "rule_hits": 35,
  "routed_calls": 382,
  "passthrough_calls": 0,
  "llm_calls": 0,
  "savings_usd": 0.035,
  "savings_pct": 100.0
&#125;</pre>

<h3 class="docs-h3">Rule Management</h3>
<table class="docs-table">
	<thead>
		<tr><th>Endpoint</th><th>Purpose</th></tr>
	</thead>
	<tbody>
		<tr><td><code class="docs-code">GET /api/rules</code></td><td>List rules and metadata</td></tr>
		<tr><td><code class="docs-code">POST /api/rules/&#123;rule_id&#125;/toggle</code></td><td>Enable/disable a rule</td></tr>
		<tr><td><code class="docs-code">GET /api/rules/&#123;rule_id&#125;/response</code></td><td>Get direct response payload for one rule</td></tr>
	</tbody>
</table>

<h3 class="docs-h3">Cron Profile API</h3>
<table class="docs-table">
	<thead>
		<tr><th>Endpoint</th><th>Purpose</th></tr>
	</thead>
	<tbody>
		<tr><td><code class="docs-code">GET /api/cron-profiles</code></td><td>List profiles</td></tr>
		<tr><td><code class="docs-code">GET /api/cron-profiles/&#123;id&#125;</code></td><td>Get profile details</td></tr>
		<tr><td><code class="docs-code">POST /api/cron-profiles/&#123;id&#125;/shadow-run</code></td><td>Run validation in shadow</td></tr>
		<tr><td><code class="docs-code">POST /api/cron-profiles/&#123;id&#125;/activate</code></td><td>Activate draft profile</td></tr>
		<tr><td><code class="docs-code">POST /api/cron-profiles/&#123;id&#125;/execute</code></td><td>Execute active profile</td></tr>
		<tr><td><code class="docs-code">POST /api/cron-profiles/&#123;id&#125;/update</code></td><td>Update profile</td></tr>
		<tr><td><code class="docs-code">POST /api/cron-profiles/&#123;id&#125;/archive</code></td><td>Archive profile</td></tr>
		<tr><td><code class="docs-code">POST /api/cron-profiles/&#123;id&#125;/restore</code></td><td>Restore profile</td></tr>
		<tr><td><code class="docs-code">POST /api/cron-profiles/&#123;id&#125;/duplicate</code></td><td>Duplicate profile</td></tr>
		<tr><td><code class="docs-code">DELETE /api/cron-profiles/&#123;id&#125;</code></td><td>Delete profile</td></tr>
		<tr><td><code class="docs-code">GET /api/cron-profiles/&#123;id&#125;/automation</code></td><td>Generate automation handoff view</td></tr>
	</tbody>
</table>

<h2 class="docs-h2">OpenAI-Compatible Proxy Routes</h2>
<p class="docs-p">
	Use RuleShield as a drop-in OpenAI/Codex-compatible gateway.
</p>
<table class="docs-table">
	<thead>
		<tr><th>Endpoint</th><th>Notes</th></tr>
	</thead>
	<tbody>
		<tr><td><code class="docs-code">GET /v1/models</code></td><td>Upstream model list passthrough</td></tr>
		<tr><td><code class="docs-code">POST /v1/chat/completions</code></td><td>Optimized chat completion path</td></tr>
		<tr><td><code class="docs-code">POST /v1/completions</code></td><td>Legacy completion path</td></tr>
		<tr><td><code class="docs-code">POST /responses</code></td><td>Codex-style responses path (no <code class="docs-code">/v1</code>)</td></tr>
		<tr><td><code class="docs-code">POST /chat/completions</code></td><td>Codex-style chat path (no <code class="docs-code">/v1</code>)</td></tr>
		<tr><td><code class="docs-code">ANY /v1/&#123;path&#125;</code></td><td>Transparent fallback for unsupported explicit endpoints</td></tr>
	</tbody>
</table>

<h2 class="docs-h2">Configuration</h2>
<p class="docs-p">
	Configuration file: <code class="docs-code">~/.ruleshield/config.yaml</code>
</p>

<table class="docs-table">
	<thead>
		<tr><th>Field</th><th>Default</th><th>Description</th></tr>
	</thead>
	<tbody>
		<tr><td><code class="docs-code">provider_url</code></td><td><code class="docs-code">https://api.openai.com</code></td><td>Upstream provider base URL</td></tr>
		<tr><td><code class="docs-code">api_key</code></td><td><code class="docs-code">""</code></td><td>Provider API key (do not commit)</td></tr>
		<tr><td><code class="docs-code">port</code></td><td><code class="docs-code">8337</code></td><td>Proxy listen port</td></tr>
		<tr><td><code class="docs-code">cache_enabled</code></td><td><code class="docs-code">true</code></td><td>Enable semantic cache layer</td></tr>
		<tr><td><code class="docs-code">rules_enabled</code></td><td><code class="docs-code">true</code></td><td>Enable rule engine layer</td></tr>
		<tr><td><code class="docs-code">shadow_mode</code></td><td><code class="docs-code">false</code></td><td>Enable shadow comparisons and feedback logging</td></tr>
		<tr><td><code class="docs-code">rules_dir</code></td><td><code class="docs-code">&lt;repo&gt;/rules</code></td><td>Rule pack location</td></tr>
		<tr><td><code class="docs-code">log_level</code></td><td><code class="docs-code">info</code></td><td>Runtime log verbosity</td></tr>
		<tr><td><code class="docs-code">router_enabled</code></td><td><code class="docs-code">true</code></td><td>Enable model router layer</td></tr>
		<tr><td><code class="docs-code">hermes_bridge_enabled</code></td><td><code class="docs-code">false</code></td><td>Enable bridge layer</td></tr>
		<tr><td><code class="docs-code">hermes_bridge_model</code></td><td><code class="docs-code">claude-haiku-4-5</code></td><td>Bridge target model</td></tr>
		<tr><td><code class="docs-code">prompt_trimming_enabled</code></td><td><code class="docs-code">false</code></td><td>Template/prompt trimming switch</td></tr>
		<tr><td><code class="docs-code">slack_webhook</code></td><td><code class="docs-code">""</code></td><td>Optional notification webhook</td></tr>
		<tr><td><code class="docs-code">max_retries</code></td><td><code class="docs-code">3</code></td><td>Upstream retry budget</td></tr>
	</tbody>
</table>
