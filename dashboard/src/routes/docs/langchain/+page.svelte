<script lang="ts">
	// LangChain integration guide -- static content, no server dependencies
</script>

<h1 class="docs-h1">LangChain Integration</h1>
<p class="docs-lead">
	RuleShield works with LangChain by pointing the <code class="docs-code">base_url</code> at the
	proxy. No monkey-patching, no wrapper classes -- just a URL change.
</p>

<div class="docs-note">
	<strong>Zero code changes to your chains.</strong> LangChain uses the OpenAI client under the hood.
	RuleShield intercepts at the HTTP level, so your existing chains, agents, and tools work unchanged.
</div>

<!-- Quick Setup -->
<h2 class="docs-h2">Quick Setup</h2>

<p class="docs-p">Get RuleShield optimizing your LangChain calls in three steps.</p>

<h3 class="docs-h3">Step 1: Install</h3>
<pre class="docs-pre"><span class="comment"># Install RuleShield and LangChain</span>
pip install ruleshield-hermes langchain-openai</pre>

<h3 class="docs-h3">Step 2: Initialize RuleShield</h3>
<pre class="docs-pre"><span class="comment"># Create config and default rules</span>
ruleshield init

<span class="comment"># Start the proxy</span>
ruleshield start</pre>

<h3 class="docs-h3">Step 3: Configure LangChain</h3>
<pre class="docs-pre"><span class="keyword">from</span> langchain_openai <span class="keyword">import</span> ChatOpenAI

<span class="comment"># Point LangChain at RuleShield proxy</span>
llm = ChatOpenAI(
    model=<span class="string">"gpt-4o"</span>,
    base_url=<span class="string">"http://localhost:&lt;PORT&gt;/v1"</span>,
    api_key=<span class="string">"your-api-key"</span>,
)

<span class="comment"># Use normally -- RuleShield optimizes automatically</span>
response = llm.invoke(<span class="string">"Hello, how are you?"</span>)</pre>

<p class="docs-p">
	That is it. Every call through <code class="docs-code">ChatOpenAI</code> now flows through
	RuleShield's 5-layer pipeline: cache, rules, template optimizer, bridge, and smart router.
</p>

<!-- LangChain Agent Example -->
<h2 class="docs-h2">LangChain Agent Example</h2>

<p class="docs-p">
	Agents make many LLM calls per task -- reasoning steps, tool calls, observation parsing.
	RuleShield caches repetitive patterns (like the system prompt re-sent on every step) and
	routes simple reasoning to cheaper models.
</p>

<pre class="docs-pre"><span class="keyword">from</span> langchain.agents <span class="keyword">import</span> create_react_agent, AgentExecutor
<span class="keyword">from</span> langchain_openai <span class="keyword">import</span> ChatOpenAI

llm = ChatOpenAI(
    model=<span class="string">"gpt-4o"</span>,
    base_url=<span class="string">"http://localhost:&lt;PORT&gt;/v1"</span>,
    api_key=<span class="string">"your-api-key"</span>,
)

<span class="comment"># Agent makes many LLM calls -- RuleShield caches repetitive ones</span>
agent = create_react_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools)
result = executor.invoke(&#123;<span class="string">"input"</span>: <span class="string">"Research Python frameworks"</span>&#125;)</pre>

<div class="docs-note">
	<strong>Why agents benefit most:</strong> A typical ReAct agent sends 5-15 LLM calls per task.
	The system prompt and tool descriptions are identical each time -- RuleShield's cache handles
	those instantly at zero cost.
</div>

<!-- Environment Variable Approach -->
<h2 class="docs-h2">Environment Variable Approach</h2>

<p class="docs-p">
	If you prefer not to change any Python code, set the base URL via environment variable.
	LangChain's OpenAI integration picks this up automatically.
</p>

<pre class="docs-pre"><span class="keyword">export</span> OPENAI_BASE_URL=<span class="string">http://localhost:&lt;PORT&gt;/v1</span>
<span class="comment"># LangChain picks this up automatically</span></pre>

<p class="docs-p">
	This approach works well when you want to toggle RuleShield on and off without touching code.
	Unset the variable to go back to direct OpenAI calls.
</p>

<!-- What to Expect -->
<h2 class="docs-h2">What to Expect</h2>

<p class="docs-p">
	Once RuleShield is running in front of your LangChain application, you will see three types of
	optimization:
</p>

<table class="docs-table">
	<thead>
		<tr>
			<th>Optimization</th>
			<th>How It Works</th>
			<th>Typical Impact</th>
		</tr>
	</thead>
	<tbody>
		<tr>
			<td>Cache hits</td>
			<td>Exact and semantic matching on repeated queries</td>
			<td>Instant response, <span class="text-accent font-mono font-semibold">$0.00</span></td>
		</tr>
		<tr>
			<td>Rule matches</td>
			<td>Pattern matching on simple, predictable prompts</td>
			<td>Instant response, <span class="text-accent font-mono font-semibold">$0.00</span></td>
		</tr>
		<tr>
			<td>Smart routing</td>
			<td>Routes simple tasks to cheaper models automatically</td>
			<td>60-90% cheaper per routed call</td>
		</tr>
	</tbody>
</table>

<!-- Checking Savings -->
<h2 class="docs-h2">Checking Your Savings</h2>

<p class="docs-p">
	After running your LangChain application through RuleShield, check what you saved:
</p>

<pre class="docs-pre"><span class="comment"># View cost savings breakdown</span>
ruleshield stats</pre>

<p class="docs-p">
	This shows total requests, cache hit rate, rule matches, router decisions, and dollars saved.
	You can also view this data in the <a href="/" class="docs-link">RuleShield Dashboard</a>.
</p>
