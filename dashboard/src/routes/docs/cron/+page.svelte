<script lang="ts">
	// Cron Optimizer docs -- static content
</script>

<h1 class="docs-h1">Cron Optimizer</h1>
<p class="docs-lead">
	The Cron Optimizer converts repeated long prompts into compact runtime executions. It keeps
	quality guardrails by validating optimized output in shadow mode before activation.
</p>

<div class="docs-note">
	<strong>Main benefit:</strong> recurring workflows can move from expensive full prompts to a compact
	"payload only" call via an active profile.
</div>

<h2 class="docs-h2">Lifecycle</h2>
<ol class="docs-p list-decimal list-inside space-y-2">
	<li>Discover recurring workflow prompts from request history</li>
	<li>Create a draft optimization profile</li>
	<li>Run shadow validation with real payloads</li>
	<li>Activate only when confidence and similarity are good enough</li>
	<li>Execute active profiles at runtime with dynamic payload input</li>
</ol>

<h2 class="docs-h2">Core Endpoints</h2>
<table class="docs-table">
	<thead>
		<tr><th>Endpoint</th><th>Purpose</th></tr>
	</thead>
	<tbody>
		<tr><td><code class="docs-code">GET /api/cron-profiles</code></td><td>List draft and active profiles</td></tr>
		<tr><td><code class="docs-code">GET /api/cron-profiles/&#123;id&#125;</code></td><td>Inspect one profile in detail</td></tr>
		<tr><td><code class="docs-code">POST /api/cron-profiles/&#123;id&#125;/shadow-run</code></td><td>Validate optimized response against baseline runs</td></tr>
		<tr><td><code class="docs-code">POST /api/cron-profiles/&#123;id&#125;/activate</code></td><td>Promote a validated draft to active</td></tr>
		<tr><td><code class="docs-code">POST /api/cron-profiles/&#123;id&#125;/execute</code></td><td>Run active profile with compact payload</td></tr>
		<tr><td><code class="docs-code">POST /api/cron-profiles/&#123;id&#125;/update</code></td><td>Update profile metadata and optimization fields</td></tr>
		<tr><td><code class="docs-code">POST /api/cron-profiles/&#123;id&#125;/archive</code></td><td>Archive profile</td></tr>
		<tr><td><code class="docs-code">POST /api/cron-profiles/&#123;id&#125;/restore</code></td><td>Restore archived profile</td></tr>
		<tr><td><code class="docs-code">POST /api/cron-profiles/&#123;id&#125;/duplicate</code></td><td>Create a copy for safe iteration</td></tr>
		<tr><td><code class="docs-code">DELETE /api/cron-profiles/&#123;id&#125;</code></td><td>Permanently delete profile</td></tr>
		<tr><td><code class="docs-code">GET /api/cron-profiles/&#123;id&#125;/automation</code></td><td>Render automation handoff payload</td></tr>
	</tbody>
</table>

<h2 class="docs-h2">Runtime Pattern</h2>
<p class="docs-p">
	At runtime, your scheduler or agent sends only the fresh payload, not the original long prompt.
	The active profile injects deterministic pre/post structure and calls a compact model path.
</p>

<pre class="docs-pre">curl -X POST http://127.0.0.1:&lt;PORT&gt;/api/cron-profiles/profile_123/execute \
  -H "Content-Type: application/json" \
  -d &#123;
    "payload_text": "Email batch for 2026-03-15",
    "model": "gpt-5.1-codex-mini"
  &#125;</pre>

<h2 class="docs-h2">Validation Signals</h2>
<table class="docs-table">
	<thead>
		<tr><th>Signal</th><th>How to use it</th></tr>
	</thead>
	<tbody>
		<tr><td>Similarity</td><td>Compare optimized output to baseline LLM output in shadow runs</td></tr>
		<tr><td>Confidence</td><td>Activation guardrail; low confidence stays in draft state</td></tr>
		<tr><td>Sample coverage</td><td>Use multiple payload examples before activating</td></tr>
		<tr><td>Runtime quality</td><td>Track post-activation regressions and roll back quickly</td></tr>
	</tbody>
</table>

<h2 class="docs-h2">CLI Workflow</h2>
<pre class="docs-pre"># Discover recurring workflows
python -m ruleshield.cli analyze-crons --structured --min-occurrences 3

# Draft profile from prompt hash/text
python -m ruleshield.cli suggest-cron-profile "&lt;prompt-hash-or-text&gt;"

# Run shadow validation
python -m ruleshield.cli run-cron-shadow &lt;profile-id&gt; --payload-text "..."

# Activate when confidence is acceptable
python -m ruleshield.cli activate-cron-profile &lt;profile-id&gt; --yes

# Execute active profile
python -m ruleshield.cli run-active-cron-profile &lt;profile-id&gt; --payload-text "..."</pre>

<div class="docs-warning">
	<strong>Recommended:</strong> keep new profiles in draft until they pass multiple realistic payload
	tests, then activate.
</div>
