<script lang="ts">
	import '../../app.css';
	import { page } from '$app/state';
	let { children } = $props();

	const currentPath = $derived(page.url.pathname);
	const currentHash = $derived(page.url.hash);

	interface NavItem {
		label: string;
		href: string;
	}

	interface NavSection {
		title: string;
		items: NavItem[];
	}

	const sections: NavSection[] = [
		{
			title: 'Getting Started',
			items: [
				{ label: 'Quick Start', href: '/docs' },
				{ label: 'Installation', href: '/docs#installation' }
			]
		},
		{
			title: 'Features',
			items: [
				{ label: 'Architecture', href: '/docs/architecture' },
				{ label: 'Rules', href: '/docs/architecture#rule-engine' },
				{ label: 'Cron Optimizer', href: '/docs/cron' },
				{ label: 'MCP Server', href: '/docs/mcp' }
			]
		},
		{
			title: 'Integration',
			items: [
				{ label: 'Hermes Agent', href: '/docs/hermes' },
				{ label: 'LangChain', href: '/docs/langchain' },
				{ label: 'CrewAI', href: '/docs/crewai' }
			]
		},
		{
			title: 'Reference',
			items: [
				{ label: 'CLI Commands', href: '/docs/api#cli' },
				{ label: 'API Reference', href: '/docs/api' }
			]
		}
	];

	function isActive(href: string): boolean {
		const [path, hash = ''] = href.split('#');
		const targetPath = path || '/docs';

		if (currentPath !== targetPath) return false;
		if (!hash) return !currentHash;
		return currentHash === `#${hash}`;
	}
</script>

<svelte:head>
	<title>RuleShield Docs</title>
	<meta name="description" content="RuleShield Hermes Documentation" />
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
	<link
		href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
		rel="stylesheet"
	/>
</svelte:head>

<div class="h-screen bg-bg flex overflow-hidden">
	<!-- Sidebar -->
	<aside class="w-[250px] shrink-0 border-r border-border bg-surface sticky top-0 h-screen overflow-y-auto">
		<div class="p-5">
			<!-- Navigation links -->
			<a
				href="/home"
				class="flex items-center gap-2 text-text-muted hover:text-primary transition-colors text-sm mb-3"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<rect x="3" y="3" width="7" height="7" stroke-width="2" /><rect x="14" y="3" width="7" height="7" stroke-width="2" /><rect x="3" y="14" width="7" height="7" stroke-width="2" /><rect x="14" y="14" width="7" height="7" stroke-width="2" />
				</svg>
				Home
			</a>
			<a
				href="/dashboard"
				class="flex items-center gap-2 text-text-muted hover:text-text-primary transition-colors text-sm mb-6"
			>
				<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
				</svg>
				Back to Dashboard
			</a>

			<!-- Logo -->
			<a href="/docs" class="block mb-8">
				<h1 class="text-lg font-bold text-text-primary">RuleShield</h1>
				<span class="text-xs text-text-muted font-mono">Documentation</span>
			</a>

			<!-- Nav sections -->
			<nav class="space-y-6">
				{#each sections as section}
					<div>
						<h2 class="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">
							{section.title}
						</h2>
						<ul class="space-y-1">
							{#each section.items as item}
								<li>
									<a
										href={item.href}
										class="block px-3 py-1.5 rounded-md text-sm transition-colors {isActive(item.href)
											? 'bg-primary/15 text-primary font-medium'
											: 'text-text-secondary hover:text-text-primary hover:bg-surface-elevated'}"
									>
										{item.label}
									</a>
								</li>
							{/each}
						</ul>
					</div>
				{/each}
			</nav>
		</div>
	</aside>

	<!-- Main content -->
	<main class="flex-1 min-w-0 h-screen overflow-y-auto">
		<div class="max-w-3xl mx-auto px-8 py-12">
			{@render children()}
		</div>
	</main>
</div>

<style>
	:global(.docs-h1) {
		font-size: 2rem;
		font-weight: 700;
		color: var(--color-text-primary);
		margin-bottom: 0.5rem;
		line-height: 1.2;
	}

	:global(.docs-h2) {
		font-size: 1.5rem;
		font-weight: 600;
		color: var(--color-text-primary);
		margin-top: 3rem;
		margin-bottom: 1rem;
		padding-bottom: 0.5rem;
		border-bottom: 1px solid var(--color-border);
	}

	:global(.docs-h3) {
		font-size: 1.125rem;
		font-weight: 600;
		color: var(--color-text-primary);
		margin-top: 2rem;
		margin-bottom: 0.75rem;
	}

	:global(.docs-p) {
		color: var(--color-text-secondary);
		line-height: 1.7;
		margin-bottom: 1rem;
	}

	:global(.docs-lead) {
		color: var(--color-text-secondary);
		font-size: 1.125rem;
		line-height: 1.7;
		margin-bottom: 2rem;
	}

	:global(.docs-code) {
		font-family: var(--font-mono);
		font-size: 0.875rem;
		background: var(--color-surface-elevated);
		color: var(--color-accent);
		padding: 0.15rem 0.4rem;
		border-radius: 0.25rem;
	}

	:global(.docs-pre) {
		font-family: var(--font-mono);
		font-size: 0.85rem;
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 0.75rem;
		padding: 1.25rem;
		overflow-x: auto;
		margin-bottom: 1.5rem;
		line-height: 1.6;
		color: var(--color-text-secondary);
	}

	:global(.docs-pre .comment) {
		color: var(--color-text-muted);
	}

	:global(.docs-pre .keyword) {
		color: var(--color-primary);
	}

	:global(.docs-pre .string) {
		color: var(--color-accent);
	}

	:global(.docs-pre .flag) {
		color: var(--color-warning);
	}

	:global(.docs-table) {
		width: 100%;
		border-collapse: collapse;
		margin-bottom: 1.5rem;
		font-size: 0.875rem;
	}

	:global(.docs-table th) {
		text-align: left;
		padding: 0.75rem 1rem;
		background: var(--color-surface);
		color: var(--color-text-primary);
		font-weight: 600;
		border: 1px solid var(--color-border);
		font-size: 0.8rem;
		text-transform: uppercase;
		letter-spacing: 0.03em;
	}

	:global(.docs-table td) {
		padding: 0.75rem 1rem;
		border: 1px solid var(--color-border);
		color: var(--color-text-secondary);
		vertical-align: top;
	}

	:global(.docs-table tr:hover td) {
		background: var(--color-surface);
	}

	:global(.docs-link) {
		color: var(--color-primary);
		text-decoration: none;
		font-weight: 500;
	}

	:global(.docs-link:hover) {
		color: var(--color-primary-hover);
		text-decoration: underline;
	}

	:global(.docs-card) {
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: 0.75rem;
		padding: 1.25rem;
		margin-bottom: 1rem;
		transition: border-color 0.2s;
	}

	:global(.docs-card:hover) {
		border-color: var(--color-primary);
	}

	:global(.docs-badge) {
		display: inline-block;
		font-family: var(--font-mono);
		font-size: 0.75rem;
		padding: 0.15rem 0.5rem;
		border-radius: 9999px;
		font-weight: 500;
	}

	:global(.docs-note) {
		background: var(--color-surface);
		border-left: 3px solid var(--color-primary);
		border-radius: 0 0.5rem 0.5rem 0;
		padding: 1rem 1.25rem;
		margin-bottom: 1.5rem;
		color: var(--color-text-secondary);
		font-size: 0.875rem;
	}

	:global(.docs-note strong) {
		color: var(--color-primary);
	}

	:global(.docs-warning) {
		background: var(--color-surface);
		border-left: 3px solid var(--color-warning);
		border-radius: 0 0.5rem 0.5rem 0;
		padding: 1rem 1.25rem;
		margin-bottom: 1.5rem;
		color: var(--color-text-secondary);
		font-size: 0.875rem;
	}

	:global(.docs-warning strong) {
		color: var(--color-warning);
	}
</style>
