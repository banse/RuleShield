<script lang="ts">
	// MCP server docs -- static content
</script>

<h1 class="docs-h1">MCP Server</h1>
<p class="docs-lead">
	RuleShield exposes an MCP stdio server so Hermes and other MCP clients can query savings,
	analyze recurring workflows, and operate cron optimization profiles programmatically.
</p>

<h2 class="docs-h2">Setup</h2>
<pre class="docs-pre"># Hermes MCP config example
mcp_servers:
  ruleshield:
    type: stdio
    command: python
    args: ["-m", "ruleshield.mcp_server"]</pre>

<p class="docs-p">
	The server reads data from <code class="docs-code">~/.ruleshield/cache.db</code> and rule files in
	<code class="docs-code">~/.ruleshield/rules</code>.
</p>

<h2 class="docs-h2">Tool Inventory</h2>
<table class="docs-table">
	<thead>
		<tr><th>Tool</th><th>Purpose</th></tr>
	</thead>
	<tbody>
		<tr><td><code class="docs-code">ruleshield_get_stats</code></td><td>Aggregated request and savings metrics</td></tr>
		<tr><td><code class="docs-code">ruleshield_estimate_cost</code></td><td>Estimate request cost and likely resolution path</td></tr>
		<tr><td><code class="docs-code">ruleshield_suggest_rules</code></td><td>Suggest rule candidates from repeated traffic</td></tr>
		<tr><td><code class="docs-code">ruleshield_analyze_crons</code></td><td>Detect recurring cron-like workflows</td></tr>
		<tr><td><code class="docs-code">ruleshield_suggest_cron_profile</code></td><td>Create draft cron optimization profile</td></tr>
		<tr><td><code class="docs-code">ruleshield_list_cron_profiles</code></td><td>List draft/active profiles</td></tr>
		<tr><td><code class="docs-code">ruleshield_show_cron_profile</code></td><td>Load one profile</td></tr>
		<tr><td><code class="docs-code">ruleshield_run_cron_shadow</code></td><td>Run profile validation in shadow mode</td></tr>
		<tr><td><code class="docs-code">ruleshield_activate_cron_profile</code></td><td>Activate validated profile</td></tr>
		<tr><td><code class="docs-code">ruleshield_run_active_cron_profile</code></td><td>Execute active profile with payload</td></tr>
	</tbody>
</table>

<h2 class="docs-h2">Protocol</h2>
<p class="docs-p">
	MCP requests follow JSON-RPC over stdio. The server supports
	<code class="docs-code">initialize</code>, <code class="docs-code">tools/list</code>, and
	<code class="docs-code">tools/call</code>.
</p>

<pre class="docs-pre">&#123;
  "jsonrpc": "2.0",
  "id": "1",
  "method": "tools/call",
  "params": &#123;
    "name": "ruleshield_get_stats",
    "arguments": &#123;&#125;
  &#125;
&#125;</pre>

<h2 class="docs-h2">When to Use MCP vs REST</h2>
<table class="docs-table">
	<thead>
		<tr><th>Use case</th><th>Best interface</th></tr>
	</thead>
	<tbody>
		<tr><td>Hermes agent tool calls during conversations</td><td>MCP server</td></tr>
		<tr><td>Dashboard and external services</td><td>REST API endpoints</td></tr>
		<tr><td>Scripting and operations from terminal</td><td>CLI and REST</td></tr>
	</tbody>
</table>

<div class="docs-note">
	<strong>KISS recommendation:</strong> use REST for service-to-service calls and MCP only where an
	agent needs structured tool calls in-session.
</div>
