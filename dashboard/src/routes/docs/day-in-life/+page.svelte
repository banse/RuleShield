<script lang="ts">
	// Day-in-the-life tester guide (HTML page)
</script>

<h1 class="docs-h1">Day-in-the-Life Shadow Test Guide</h1>
<p class="docs-lead">
	This test plan simulates a realistic Hermes workday and measures how well RuleShield rules behave in
	shadow mode before activation decisions.
</p>

<div class="docs-note">
	<strong>Goal:</strong> collect high-quality comparison data across typical prompt families, then tune
	rules based on confidence movement and feedback outcomes.
</div>

<h2 class="docs-h2">Test Preconditions</h2>
<ul class="docs-p list-disc list-inside space-y-1">
	<li>Proxy running on <code class="docs-code">127.0.0.1:8337</code></li>
	<li><code class="docs-code">shadow_mode: true</code> in <code class="docs-code">~/.ruleshield/config.yaml</code></li>
	<li>Baseline rules enabled (workflow-intents on, overly strict smalltalk rules optional)</li>
	<li>Model fixed for the full session to reduce drift in comparisons</li>
</ul>

<h2 class="docs-h2">Session Structure (3-4 Hours)</h2>
<table class="docs-table">
	<thead>
		<tr><th>Block</th><th>Duration</th><th>Focus</th></tr>
	</thead>
	<tbody>
		<tr><td>Warm-up</td><td>20-30 min</td><td>Short prompts, greetings, confirmations, status checks</td></tr>
		<tr><td>Workload A</td><td>60 min</td><td>Coding and file-operation prompts</td></tr>
		<tr><td>Workload B</td><td>45-60 min</td><td>Research, planning, summarization</td></tr>
		<tr><td>Cron-style Tasks</td><td>30-45 min</td><td>Recurring operational prompts and payload updates</td></tr>
		<tr><td>Review</td><td>15-20 min</td><td>Inspect rule events, feedback, confidence changes</td></tr>
	</tbody>
</table>

<h2 class="docs-h2">Prompt Catalog (Realistic Mix)</h2>
<p class="docs-p">Use natural language variations instead of repeating one exact sentence.</p>

<h3 class="docs-h3">1) Conversational Control (lightweight)</h3>
<pre class="docs-pre">hello
are you there?
ok thanks
repeat that
show me what changed
explain what happened</pre>

<h3 class="docs-h3">2) Coding Assistant</h3>
<pre class="docs-pre">list files in this project
read /path/to/file and summarize risks
fix this test failure and explain the root cause
show the diff and explain each change
retry with a safer approach</pre>

<h3 class="docs-h3">3) Research and Planning</h3>
<pre class="docs-pre">summarize the key risks in this architecture
compare two implementation options for maintainability
create a short implementation plan with milestones
rewrite this text for clarity and technical precision</pre>

<h3 class="docs-h3">4) Cron/Recurring Workflows</h3>
<pre class="docs-pre">check inbox every day at 8am, categorize and summarize
collect daily build results and produce a markdown report
scan support tickets each morning and group by severity</pre>

<h2 class="docs-h2">Operator Checklist (During Test)</h2>
<ol class="docs-p list-decimal list-inside space-y-2">
	<li>Every 20-30 minutes, check <code class="docs-code">/api/shadow</code> totals and per-rule spread</li>
	<li>Open the Rule Event Log dashboard and verify confidence movements are plausible</li>
	<li>Watch for repetitive rejects on one rule family (signal for tuning or temporary pause)</li>
	<li>Keep payload and model stable inside one block; change only one variable at a time</li>
</ol>

<h2 class="docs-h2">Activation Decision Rules</h2>
<table class="docs-table">
	<thead>
		<tr><th>Condition</th><th>Action</th></tr>
	</thead>
	<tbody>
		<tr><td>High comparisons + steadily rising confidence</td><td>Keep running; candidate for promotion</td></tr>
		<tr><td>Low similarity but semantically acceptable</td><td>Tune response style before pausing</td></tr>
		<tr><td>Repeated low similarity + feedback rejects</td><td>Pause rule and retune patterns/response</td></tr>
		<tr><td>Rule impacts user-critical workflows negatively</td><td>Disable immediately, investigate, relaunch in shadow</td></tr>
	</tbody>
</table>

<h2 class="docs-h2">Useful Commands</h2>
<pre class="docs-pre"># shadow summary
curl -s http://127.0.0.1:8337/api/shadow

# live rules
curl -s http://127.0.0.1:8337/api/rules

# minimal rule event log
curl -s "http://127.0.0.1:8337/api/rule-events?limit=100"

# recent feedback
curl -s "http://127.0.0.1:8337/api/feedback?limit=50"</pre>
