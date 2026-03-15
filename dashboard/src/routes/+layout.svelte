<script lang="ts">
	import '../app.css';
	let { children } = $props();
</script>

<svelte:head>
	<title>RuleShield Dashboard</title>
	<meta name="description" content="RuleShield Hermes - LLM Cost Optimizer Dashboard" />
</svelte:head>

<div class="min-h-screen bg-bg">
	{@render children()}
</div>
