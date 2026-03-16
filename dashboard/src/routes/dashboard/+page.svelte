<script lang="ts">
	import DashboardView from '../+page.svelte';

	let { data } = $props();
</script>

<DashboardView {data} />
