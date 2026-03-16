<script lang="ts">
	// CrewAI integration guide -- static content, no server dependencies
</script>

<h1 class="docs-h1">CrewAI Integration</h1>
<p class="docs-lead">
	CrewAI runs multiple agents that make many LLM calls per crew execution. RuleShield sits
	in front of the OpenAI API and optimizes all of them automatically.
</p>

<div class="docs-note">
	<strong>High-impact integration.</strong> CrewAI crews typically generate 20-50+ LLM calls per run.
	Many of these are repetitive (agent intros, task delegation, status checks) and hit RuleShield's
	cache and rules layers at zero cost.
</div>

<!-- Quick Setup -->
<h2 class="docs-h2">Quick Setup</h2>

<p class="docs-p">Get RuleShield running with CrewAI in three steps.</p>

<h3 class="docs-h3">Step 1: Install</h3>
<pre class="docs-pre"><span class="comment"># Setup RuleShield (Hermes flow) and install CrewAI</span>
npm run setup:hermes
pip install crewai</pre>

<h3 class="docs-h3">Step 2: Initialize RuleShield</h3>
<pre class="docs-pre"><span class="comment"># Start the proxy</span>
npm run start</pre>

<h3 class="docs-h3">Step 3: Configure CrewAI</h3>
<pre class="docs-pre"><span class="keyword">import</span> os
os.environ[<span class="string">"OPENAI_BASE_URL"</span>] = <span class="string">"http://localhost:&lt;PORT&gt;/v1"</span>
os.environ[<span class="string">"OPENAI_API_KEY"</span>] = <span class="string">"your-api-key"</span>

<span class="keyword">from</span> crewai <span class="keyword">import</span> Agent, Task, Crew

researcher = Agent(
    role=<span class="string">"Researcher"</span>,
    goal=<span class="string">"Find information"</span>,
    backstory=<span class="string">"Expert researcher"</span>,
    llm=<span class="string">"gpt-4o"</span>,
)

writer = Agent(
    role=<span class="string">"Writer"</span>,
    goal=<span class="string">"Write content"</span>,
    backstory=<span class="string">"Expert writer"</span>,
    llm=<span class="string">"gpt-4o"</span>,
)

<span class="comment"># CrewAI makes many LLM calls per crew run</span>
<span class="comment"># RuleShield optimizes: cache repeated patterns, route simple tasks</span>
crew = Crew(agents=[researcher, writer], tasks=[...])
result = crew.kickoff()</pre>

<p class="docs-p">
	Set the environment variables <strong>before</strong> importing CrewAI. CrewAI reads
	<code class="docs-code">OPENAI_BASE_URL</code> at import time, so the order matters.
</p>

<!-- Why CrewAI Benefits -->
<h2 class="docs-h2">Why CrewAI Benefits the Most</h2>

<p class="docs-p">
	Multi-agent frameworks like CrewAI generate a high volume of LLM calls with significant
	repetition. Here is where the savings come from:
</p>

<table class="docs-table">
	<thead>
		<tr>
			<th>Pattern</th>
			<th>What Happens</th>
			<th>RuleShield Layer</th>
		</tr>
	</thead>
	<tbody>
		<tr>
			<td>Agent introductions</td>
			<td>Each agent re-sends its role, goal, and backstory on every call</td>
			<td><span class="text-accent font-mono font-semibold">Cache</span></td>
		</tr>
		<tr>
			<td>Task delegation</td>
			<td>Manager agents use similar phrasing to assign tasks</td>
			<td><span class="text-accent font-mono font-semibold">Cache</span></td>
		</tr>
		<tr>
			<td>Status checks</td>
			<td>Agents ask "is this task complete?" in predictable patterns</td>
			<td><span class="text-primary font-mono font-semibold">Rules</span></td>
		</tr>
		<tr>
			<td>Simple reasoning</td>
			<td>Not every agent step needs GPT-4o -- some are straightforward</td>
			<td><span class="text-routed font-mono font-semibold">Router</span></td>
		</tr>
	</tbody>
</table>

<div class="docs-note">
	<strong>Real-world example:</strong> A 3-agent crew doing research and writing typically makes
	30-40 LLM calls. With RuleShield, 40-60% of those hit cache or rules, and another 15-20% get
	routed to cheaper models. Total savings: 50-70%.
</div>

<!-- Advanced Configuration -->
<h2 class="docs-h2">Advanced: Per-Agent Model Routing</h2>

<p class="docs-p">
	You can still assign different models to different agents. RuleShield respects the model field
	and applies its optimization layers per-model:
</p>

<pre class="docs-pre"><span class="keyword">from</span> crewai <span class="keyword">import</span> Agent

<span class="comment"># Complex tasks -- RuleShield still caches repeated system prompts</span>
researcher = Agent(
    role=<span class="string">"Researcher"</span>,
    goal=<span class="string">"Deep analysis"</span>,
    backstory=<span class="string">"Senior researcher"</span>,
    llm=<span class="string">"gpt-4o"</span>,
)

<span class="comment"># Simple tasks -- RuleShield may route to even cheaper models</span>
formatter = Agent(
    role=<span class="string">"Formatter"</span>,
    goal=<span class="string">"Format output as markdown"</span>,
    backstory=<span class="string">"Formatting specialist"</span>,
    llm=<span class="string">"gpt-4o-mini"</span>,
)</pre>

<!-- Checking Savings -->
<h2 class="docs-h2">Checking Your Savings</h2>

<p class="docs-p">
	After a crew run, check what RuleShield saved:
</p>

<pre class="docs-pre"><span class="comment"># View cost savings breakdown</span>
ruleshield stats</pre>

<p class="docs-p">
	This shows total requests, cache hit rate, rule matches, router decisions, and dollars saved.
	You can also view real-time optimization data in the <a href="/" class="docs-link">RuleShield Dashboard</a>.
</p>

<p class="docs-p">
	For crews that run on a schedule (e.g., daily research reports), savings increase over time as
	RuleShield learns the recurring patterns and caches more aggressively.
</p>
