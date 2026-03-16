<script lang="ts">
	import { page } from '$app/state';

	type CardId =
		| 'opening-0'
		| 'opening-1'
		| 'opening-2'
		| 'opening-3'
		| 'problem'
		| 'shadow'
		| 'feedback'
		| 'monitor'
		| 'closing'
		| 'end';

	type Card = {
		id: CardId;
		kicker: string;
		title: string;
		subtitle?: string;
		accentGradient?: string;
		lines?: string[];
	};

	const openingCards = new Set<CardId>(['opening-0', 'opening-1', 'opening-2', 'opening-3']);

	const cards: Card[] = [
		{
			id: 'opening-0',
			kicker: 'Hackathon Demo',
			title: '',
			accentGradient: 'linear-gradient(135deg, #00D7C3 0%, #54F3C3 46%, #F7C66A 100%)'
		},
		{
			id: 'opening-1',
			kicker: 'Hackathon Demo',
			title: '',
			subtitle: 'When LLM usage scales, small costs stop being small.',
			accentGradient: 'linear-gradient(135deg, #00D7C3 0%, #54F3C3 46%, #F7C66A 100%)'
		},
		{
			id: 'opening-2',
			kicker: 'Hackathon Demo',
			title: '',
			subtitle: 'When LLM usage scales, small costs stop being small.',
			lines: ['Cut repetitive LLM spend', 'Validate safely in shadow mode', 'Reduce unnecessary upstream calls'],
			accentGradient: 'linear-gradient(135deg, #00D7C3 0%, #54F3C3 46%, #F7C66A 100%)'
		},
		{
			id: 'opening-3',
			kicker: 'Hackathon Demo',
			title: 'RuleShield',
			subtitle: 'When LLM usage scales, small costs stop being small.',
			lines: ['Cut repetitive LLM spend', 'Validate safely in shadow mode', 'Reduce unnecessary upstream calls'],
			accentGradient: 'linear-gradient(135deg, #00D7C3 0%, #54F3C3 46%, #F7C66A 100%)'
		},
		{
			id: 'problem',
			kicker: 'Why It Matters',
			title: 'Not every prompt needs a premium model call.',
			lines: ['Greetings', 'Acknowledgments', 'Repeated interaction patterns'],
			accentGradient: 'linear-gradient(135deg, #4AC0B2 0%, #6FA7FF 52%, #B5E46D 100%)'
		},
		{
			id: 'shadow',
			kicker: 'Shadow Mode',
			title: 'Validate first. Promote later.',
			lines: ['Rule response in the background', 'Compare against the real LLM', 'Go live only when it looks safe'],
			accentGradient: 'linear-gradient(135deg, #85A8FF 0%, #9DD6FF 42%, #8EF5D5 100%)'
		},
		{
			id: 'feedback',
			kicker: 'Feedback Loop',
			title: 'Good rules strengthen. Bad rules weaken.',
			lines: ['Confidence moves over time', 'Safer optimization than static shortcuts', 'Hermes gets more efficient without blind automation'],
			accentGradient: 'linear-gradient(135deg, #F7C66A 0%, #FF9D7A 45%, #FFA2CF 100%)'
		},
		{
			id: 'monitor',
			kicker: 'Optional Overlay',
			title: 'What the user sees vs. what RuleShield sees',
			accentGradient: 'linear-gradient(135deg, #85A8FF 0%, #C7B4FF 48%, #8EF5D5 100%)'
		},
		{
			id: 'closing',
			kicker: 'Final Thesis',
			title: 'Optimize safely. Spend less. Learn over time.',
			lines: ['Repetitive prompts do not always need a full model call', 'Shadow mode makes rollout safer', 'Feedback helps Hermes get more efficient over time'],
			accentGradient: 'linear-gradient(135deg, #F7C66A 0%, #FF9D7A 52%, #FF6AB3 100%)'
		},
		{
			id: 'end',
			kicker: 'Source',
			title: 'RuleShield',
			lines: ['github.com/banse/RuleShield'],
			accentGradient: 'linear-gradient(135deg, #9AD0FF 0%, #82F2E1 50%, #E8F07A 100%)'
		}
	];

	let selectedId = $state<CardId>('opening-1');
	let selectedCard = $derived(currentCard());
	let isRecordMode = $derived(page.url.searchParams.get('mode') === 'record');

	$effect(() => {
		const cardParam = page.url.searchParams.get('card') as CardId | null;
		if (cardParam && cards.some((card) => card.id === cardParam)) {
			selectedId = cardParam;
		}
	});

	function selectCard(cardId: CardId) {
		selectedId = cardId;
	}

	function currentCard(): Card {
		return cards.find((card) => card.id === selectedId) ?? cards[0];
	}
</script>

<svelte:head>
	<title>Recording Cards</title>
</svelte:head>

<div class="h-screen overflow-hidden bg-[#07090E] text-white">
	{#if isRecordMode}
		<div class="relative h-full w-full overflow-hidden bg-[#090C13]">
			<div
				class="absolute inset-0 opacity-35 blur-3xl"
				style={`background: ${selectedCard.accentGradient ?? 'linear-gradient(135deg, #00D7C3 0%, #7E8BFF 46%, #F7C66A 100%)'};`}
			></div>
			<div class="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.12),transparent_28%),radial-gradient(circle_at_bottom_right,rgba(255,255,255,0.08),transparent_30%)]"></div>
			<div class="absolute inset-0 opacity-[0.07] [background-image:linear-gradient(rgba(255,255,255,0.7)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.7)_1px,transparent_1px)] [background-size:72px_72px]"></div>
			<div class="relative flex h-full w-full flex-col justify-between px-10 py-10 md:px-16 md:py-16">
				<div>
					<div class="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.04] px-4 py-2 backdrop-blur">
						<span class="h-2.5 w-2.5 rounded-full bg-white/80"></span>
						<p class="text-[11px] uppercase tracking-[0.28em] text-white/55">{selectedCard.kicker}</p>
					</div>
					<h1
						class={`mt-8 max-w-5xl text-5xl font-semibold leading-[0.98] md:text-7xl xl:text-[5.75rem] ${
							selectedCard.title ? 'text-white' : openingCards.has(selectedCard.id) ? 'pointer-events-none select-none text-transparent' : 'hidden'
						}`}
						aria-hidden={!selectedCard.title}
					>
						{selectedCard.title || 'RuleShield'}
					</h1>
					{#if selectedCard.subtitle}
						<p class="mt-8 max-w-4xl text-xl leading-relaxed text-white/76 md:text-3xl xl:text-[2rem]">
							{selectedCard.subtitle}
						</p>
					{/if}
					{#if selectedCard.lines}
						<div class="mt-10 space-y-4">
							{#each selectedCard.lines as line}
								<p class="text-xl text-white/78 md:text-3xl xl:text-[2.35rem]">{line}</p>
							{/each}
						</div>
					{/if}
				</div>

				<div class="flex items-end justify-between gap-6">
					<div>
						<div class="h-px w-32 bg-white/15 md:w-48"></div>
						<p class="mt-4 text-xs uppercase tracking-[0.32em] text-white/30">RuleShield</p>
					</div>
					<div class="rounded-full border border-white/10 bg-white/[0.03] px-4 py-2 text-xs uppercase tracking-[0.26em] text-white/40">
						Hermes Hackathon
					</div>
				</div>
			</div>
		</div>
	{:else}
	<div class="mx-auto flex h-full max-w-7xl flex-col gap-4 px-6 py-5">
		<header class="flex items-end justify-between border-b border-white/10 pb-4">
			<div>
				<p class="text-xs uppercase tracking-[0.24em] text-white/45">Recording Utility</p>
				<h1 class="mt-2 text-3xl font-semibold">Title Cards</h1>
				<p class="mt-2 text-sm text-white/60">
					Choose a card and record it fullscreen in the browser.
				</p>
			</div>
			<a
				href="/home"
				class="rounded-md border border-white/10 bg-white/5 px-3 py-2 text-xs text-white/70 transition hover:border-white/25 hover:text-white"
			>
				All Pages
			</a>
		</header>

		<div class="grid min-h-0 flex-1 gap-4 lg:grid-cols-[240px_1fr]">
			<aside class="min-h-0 rounded-2xl border border-white/10 bg-white/[0.03] p-4">
				<p class="mb-3 text-xs uppercase tracking-[0.2em] text-white/45">Cards</p>
				<div class="space-y-2">
					{#each cards as card}
						<button
							class={`w-full rounded-xl border px-4 py-3 text-left transition ${
								selectedId === card.id
									? 'border-white/30 bg-white/10 text-white'
									: 'border-white/10 bg-transparent text-white/70 hover:border-white/20 hover:text-white'
							}`}
							onclick={() => selectCard(card.id)}
						>
							<p class="text-[11px] uppercase tracking-[0.22em] text-white/40">{card.kicker}</p>
							<p class="mt-1 text-sm font-medium">{card.id}</p>
						</button>
					{/each}
				</div>
				<div class="mt-4 rounded-xl border border-white/10 bg-black/20 p-3 text-xs text-white/55">
					<p>Tip:</p>
					<p class="mt-1">For clean output use <code class="font-mono">?mode=record&amp;card=opening-1</code>.</p>
				</div>
			</aside>

			<section class="min-h-0 min-w-0 rounded-[32px] border border-white/10 bg-[#0C1018] p-3">
				<div class="relative flex h-full min-h-0 overflow-hidden rounded-[28px] border border-white/10 bg-[#090C13]">
					<div
						class="absolute inset-0 opacity-30 blur-3xl"
						style={`background: ${selectedCard.accentGradient ?? 'linear-gradient(135deg, #00D7C3 0%, #7E8BFF 46%, #F7C66A 100%)'};`}
					></div>
					<div class="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.12),transparent_28%),radial-gradient(circle_at_bottom_right,rgba(255,255,255,0.08),transparent_30%)]"></div>
					<div class="absolute inset-0 opacity-[0.06] [background-image:linear-gradient(rgba(255,255,255,0.7)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.7)_1px,transparent_1px)] [background-size:72px_72px]"></div>
					<div class="relative flex w-full flex-col justify-between px-8 py-8 md:px-14 md:py-12">
						<div>
							<div class="inline-flex items-center gap-2 rounded-full border border-white/12 bg-white/[0.04] px-3 py-1.5 backdrop-blur">
								<span
									class="h-2 w-2 rounded-full"
									style={`background: ${selectedCard.accentGradient ? selectedCard.accentGradient.split(',')[0].replace('linear-gradient(135deg', '').trim().replace('0%)', '').replace('0%', '').replace('(', '') : '#ffffff'};`}
								></span>
								<p class="text-[11px] uppercase tracking-[0.28em] text-white/50">{selectedCard.kicker}</p>
							</div>
							<h2
								class={`mt-6 max-w-4xl text-4xl font-semibold leading-[1.02] md:text-6xl xl:text-7xl ${
									selectedCard.title ? 'text-white' : openingCards.has(selectedCard.id) ? 'pointer-events-none select-none text-transparent' : 'hidden'
								}`}
								aria-hidden={!selectedCard.title}
							>
								{selectedCard.title || 'RuleShield'}
							</h2>
							{#if selectedCard.subtitle}
								<p class="mt-6 max-w-3xl text-lg leading-relaxed text-white/72 md:text-2xl xl:text-[1.7rem]">
									{selectedCard.subtitle}
								</p>
							{/if}
							{#if selectedCard.lines}
								<div class="mt-8 space-y-3">
									{#each selectedCard.lines as line}
										<p class="text-lg text-white/72 md:text-2xl xl:text-[1.7rem]">{line}</p>
									{/each}
								</div>
							{/if}
						</div>

						<div class="flex items-end justify-between gap-4">
							<div>
								<div class="h-px w-24 bg-white/15 md:w-40"></div>
								<p class="mt-3 text-[11px] uppercase tracking-[0.28em] text-white/28">RuleShield</p>
							</div>
							<div class="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 text-[11px] uppercase tracking-[0.24em] text-white/38">
								Hermes Hackathon
							</div>
						</div>
					</div>
				</div>
			</section>
		</div>
	</div>
	{/if}
</div>
