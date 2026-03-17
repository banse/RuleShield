import { h as head, c as attr_class, a as ensure_array_like, e as escape_html, b as attr, d as attr_style, s as stringify } from "../../../chunks/index2.js";
function html(value) {
  var html2 = String(value ?? "");
  var open = "<!---->";
  return open + html2 + "<!---->";
}
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let navScrolled = false;
    let savingsCount = 0;
    let problemVisible = false;
    let layersVisible = false;
    let integrationVisible = false;
    let resultsVisible = false;
    function formatMoney(n) {
      return n.toLocaleString("en-US");
    }
    const navLinks = [
      { label: "Features", id: "features" },
      { label: "Pricing", id: "pricing" },
      { label: "Docs", href: "#" },
      { label: "GitHub", href: "https://github.com/ruleshield" }
    ];
    head("1jq6khg", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>RuleShield Hermes - One Line of Code. 80% Less LLM Cost.</title>`);
      });
      $$renderer3.push(`<meta name="description" content="Drop-in LLM cost optimizer. Semantic caching, auto-learned rules, and smart routing. One import, up to 82% savings." class="svelte-1jq6khg"/> <link rel="preconnect" href="https://fonts.googleapis.com" class="svelte-1jq6khg"/> <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" class="svelte-1jq6khg"/> <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&amp;family=JetBrains+Mono:wght@400;500&amp;display=swap" rel="stylesheet" class="svelte-1jq6khg"/>`);
    });
    $$renderer2.push(`<nav${attr_class("fixed top-0 left-0 right-0 z-50 transition-all duration-300 svelte-1jq6khg", void 0, { "nav-scrolled": navScrolled })}><div class="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between svelte-1jq6khg"><button class="flex items-center gap-2 group cursor-pointer svelte-1jq6khg"><div class="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center text-white font-bold text-sm svelte-1jq6khg">R</div> <span class="text-lg font-bold text-text-primary svelte-1jq6khg">Rule<span class="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent svelte-1jq6khg">Shield</span></span></button> <div class="hidden md:flex items-center gap-8 svelte-1jq6khg"><!--[-->`);
    const each_array = ensure_array_like(navLinks);
    for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
      let link = each_array[$$index];
      if (link.id) {
        $$renderer2.push("<!--[0-->");
        $$renderer2.push(`<button class="text-sm text-text-secondary hover:text-text-primary transition-colors cursor-pointer svelte-1jq6khg">${escape_html(link.label)}</button>`);
      } else {
        $$renderer2.push("<!--[-1-->");
        $$renderer2.push(`<a${attr("href", link.href)} class="text-sm text-text-secondary hover:text-text-primary transition-colors svelte-1jq6khg">${escape_html(link.label)}</a>`);
      }
      $$renderer2.push(`<!--]-->`);
    }
    $$renderer2.push(`<!--]--> <button class="btn-primary text-sm px-5 py-2 svelte-1jq6khg">Get Started</button></div> <button class="md:hidden text-text-primary cursor-pointer svelte-1jq6khg"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="svelte-1jq6khg">`);
    {
      $$renderer2.push("<!--[-1-->");
      $$renderer2.push(`<path d="M3 12h18M3 6h18M3 18h18" class="svelte-1jq6khg"></path>`);
    }
    $$renderer2.push(`<!--]--></svg></button></div> `);
    {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--></nav> <main class="overflow-x-hidden svelte-1jq6khg"><section id="hero" data-section="hero" class="relative pt-32 pb-24 px-6 svelte-1jq6khg"><div class="absolute inset-0 overflow-hidden pointer-events-none svelte-1jq6khg"><div class="absolute top-1/4 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-primary/5 rounded-full blur-[120px] svelte-1jq6khg"></div> <div class="absolute top-1/3 left-1/3 w-[400px] h-[400px] bg-accent/5 rounded-full blur-[100px] svelte-1jq6khg"></div></div> <div class="max-w-5xl mx-auto text-center relative z-10 svelte-1jq6khg"><div${attr_class(
      `transition-all duration-700 ${stringify("opacity-0 translate-y-8")}`,
      "svelte-1jq6khg"
    )}><div class="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-border bg-surface/50 backdrop-blur-sm mb-8 svelte-1jq6khg"><div class="w-2 h-2 rounded-full bg-accent animate-pulse svelte-1jq6khg"></div> <span class="text-xs font-medium tracking-widest text-text-muted uppercase svelte-1jq6khg">Drop-in LLM Cost Optimizer</span></div> <h1 class="text-5xl sm:text-6xl lg:text-7xl font-extrabold leading-tight mb-6 svelte-1jq6khg"><span class="text-text-primary svelte-1jq6khg">One line of code.</span><br class="svelte-1jq6khg"/> <span class="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent svelte-1jq6khg">80% less LLM cost.</span></h1> <p class="text-lg sm:text-xl text-text-secondary max-w-2xl mx-auto mb-10 leading-relaxed svelte-1jq6khg">RuleShield sits between your app and any LLM API.
					Semantic caching, auto-learned rules, and smart routing —
					no code changes beyond the import.</p> <div class="flex flex-col sm:flex-row items-center justify-center gap-4 mb-10 svelte-1jq6khg"><button class="btn-primary text-base px-8 py-3.5 w-full sm:w-auto svelte-1jq6khg">Start Free <svg class="inline-block ml-2 w-4 h-4 svelte-1jq6khg" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 8h10M9 4l4 4-4 4" class="svelte-1jq6khg"></path></svg></button> <a href="/slides" class="btn-ghost text-base px-8 py-3.5 w-full sm:w-auto text-center svelte-1jq6khg">View Demo</a></div> <div class="flex items-center justify-center gap-2 text-sm text-text-muted mb-16 svelte-1jq6khg"><svg class="w-4 h-4 text-accent svelte-1jq6khg" viewBox="0 0 16 16" fill="currentColor"><path d="M8 0l2.09 5.27L16 6.18l-4.18 3.64L13.18 16 8 12.72 2.82 16l1.36-6.18L0 6.18l5.91-.91z" class="svelte-1jq6khg"></path></svg> <span class="svelte-1jq6khg">Proven <strong class="text-accent svelte-1jq6khg">47-82% savings</strong> across 4 test scenarios</span></div></div> <div${attr_class(
      `transition-all duration-700 delay-300 ${stringify("opacity-0 translate-y-12")}`,
      "svelte-1jq6khg"
    )}><div class="max-w-3xl mx-auto bg-surface rounded-2xl border border-border overflow-hidden shadow-2xl shadow-primary/5 svelte-1jq6khg"><div class="grid grid-cols-1 sm:grid-cols-2 divide-y sm:divide-y-0 sm:divide-x divide-border svelte-1jq6khg"><div class="p-6 svelte-1jq6khg"><div class="flex items-center gap-2 mb-4 svelte-1jq6khg"><div class="w-3 h-3 rounded-full bg-error/60 svelte-1jq6khg"></div> <span class="text-xs font-medium text-text-muted uppercase tracking-wider svelte-1jq6khg">Before</span></div> <pre class="font-mono text-sm text-text-secondary leading-relaxed svelte-1jq6khg"><code class="svelte-1jq6khg"><span class="text-text-muted svelte-1jq6khg">from</span> <span class="text-error/80 svelte-1jq6khg">openai</span> <span class="text-text-muted svelte-1jq6khg">import</span> OpenAI

client = OpenAI()
<span class="text-text-muted svelte-1jq6khg"># Every call hits the API</span>
<span class="text-text-muted svelte-1jq6khg"># $$$$ per month</span></code></pre></div> <div class="p-6 bg-accent/[0.02] svelte-1jq6khg"><div class="flex items-center gap-2 mb-4 svelte-1jq6khg"><div class="w-3 h-3 rounded-full bg-accent svelte-1jq6khg"></div> <span class="text-xs font-medium text-accent uppercase tracking-wider svelte-1jq6khg">After</span></div> <pre class="font-mono text-sm text-text-secondary leading-relaxed svelte-1jq6khg"><code class="svelte-1jq6khg"><span class="text-text-muted svelte-1jq6khg">from</span> <span class="text-accent svelte-1jq6khg">ruleshield</span> <span class="text-text-muted svelte-1jq6khg">import</span> OpenAI

client = OpenAI()
<span class="text-text-muted svelte-1jq6khg"># Identical API. Smart routing.</span>
<span class="text-text-muted svelte-1jq6khg"># 80% less cost.</span></code></pre></div></div> <div class="border-t border-border bg-surface-elevated/50 px-6 py-5 flex flex-col sm:flex-row items-center justify-between gap-4 svelte-1jq6khg"><span class="text-sm text-text-muted svelte-1jq6khg">Estimated monthly savings</span> <div class="flex items-center gap-2 svelte-1jq6khg"><span class="text-3xl font-bold text-accent font-mono tabular-nums svelte-1jq6khg">$${escape_html(formatMoney(savingsCount))}</span> <span class="text-xs text-text-muted svelte-1jq6khg">/month</span></div></div></div></div></div></section> <section id="problem" data-section="problem" class="py-24 px-6 relative svelte-1jq6khg"><div class="max-w-5xl mx-auto svelte-1jq6khg"><div${attr_class(
      `text-center mb-16 transition-all duration-700 ${stringify("opacity-0 translate-y-8")}`,
      "svelte-1jq6khg"
    )}><h2 class="text-3xl sm:text-4xl font-bold text-text-primary mb-4 svelte-1jq6khg">You're burning money on repeat questions.</h2> <p class="text-lg text-text-secondary max-w-xl mx-auto svelte-1jq6khg">Most LLM API calls are predictable. But every one costs the same.</p></div> <div class="grid grid-cols-1 md:grid-cols-3 gap-6 svelte-1jq6khg"><!--[-->`);
    const each_array_2 = ensure_array_like([
      {
        icon: "🔄",
        stat: "60-80%",
        title: "Repetitive Requests",
        desc: "Most LLM calls ask questions that have already been answered. You pay full price every time."
      },
      {
        icon: "💸",
        stat: "$$$",
        title: "Every Call Costs the Same",
        desc: "Simple lookups cost as much as complex reasoning. No intelligence in your billing."
      },
      {
        icon: "🔍",
        stat: "0%",
        title: "Zero Visibility",
        desc: "No insight into which requests are repetitive, which could be cached, or which need a cheaper model."
      }
    ]);
    for (let i = 0, $$length = each_array_2.length; i < $$length; i++) {
      let card = each_array_2[i];
      $$renderer2.push(`<div${attr_class("pain-card group transition-all duration-700 svelte-1jq6khg", void 0, {
        "opacity-100": problemVisible,
        "translate-y-0": problemVisible,
        "opacity-0": !problemVisible,
        "translate-y-8": !problemVisible
      })}${attr_style(`transition-delay: ${stringify(i * 150)}ms`)}><div class="text-4xl mb-4 svelte-1jq6khg">${escape_html(card.icon)}</div> <div class="text-2xl font-bold text-accent mb-2 font-mono svelte-1jq6khg">${escape_html(card.stat)}</div> <h3 class="text-lg font-semibold text-text-primary mb-2 svelte-1jq6khg">${escape_html(card.title)}</h3> <p class="text-sm text-text-secondary leading-relaxed svelte-1jq6khg">${escape_html(card.desc)}</p></div>`);
    }
    $$renderer2.push(`<!--]--></div> <p${attr_class(`text-center text-xl font-semibold text-text-primary mt-16 transition-all duration-700 delay-500 ${stringify("opacity-0")}`, "svelte-1jq6khg")}>RuleShield learns what <span class="text-accent svelte-1jq6khg">doesn't need an LLM</span>.</p></div></section> <section id="features" data-section="layers" class="py-24 px-6 relative svelte-1jq6khg"><div class="absolute inset-0 overflow-hidden pointer-events-none svelte-1jq6khg"><div class="absolute top-1/2 left-0 w-[600px] h-[600px] bg-primary/3 rounded-full blur-[150px] svelte-1jq6khg"></div> <div class="absolute bottom-0 right-0 w-[500px] h-[500px] bg-accent/3 rounded-full blur-[120px] svelte-1jq6khg"></div></div> <div class="max-w-5xl mx-auto relative z-10 svelte-1jq6khg"><div${attr_class(
      `text-center mb-16 transition-all duration-700 ${stringify("opacity-0 translate-y-8")}`,
      "svelte-1jq6khg"
    )}><div class="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-primary/30 bg-primary/5 mb-6 svelte-1jq6khg"><span class="text-xs font-medium text-primary svelte-1jq6khg">Core Architecture</span></div> <h2 class="text-3xl sm:text-4xl font-bold text-text-primary mb-4 svelte-1jq6khg">Four layers. One import.</h2> <p class="text-lg text-text-secondary max-w-xl mx-auto svelte-1jq6khg">Each layer catches what the previous one missed. Together, they eliminate up to 82% of LLM costs.</p></div> <div class="grid grid-cols-1 md:grid-cols-2 gap-6 svelte-1jq6khg"><!--[-->`);
    const each_array_3 = ensure_array_like([
      {
        layer: "01",
        title: "Semantic Cache",
        cost: "$0",
        color: "accent",
        desc: "Identical and similar requests answered from cache in <5ms. No LLM call needed.",
        stat: "73%",
        statLabel: "Cache Hit Rate",
        icon: `<svg class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>`
      },
      {
        layer: "02",
        title: "Rule Engine",
        cost: "$0",
        color: "primary",
        desc: "75 auto-learned decision rules handle patterns with SAP-grade accuracy scoring.",
        stat: "97%",
        statLabel: "Rule Accuracy",
        icon: `<svg class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M12 2a10 10 0 100 20 10 10 0 000-20zm0 5v5l3 3"/></svg>`
      },
      {
        layer: "03",
        title: "Hermes Bridge",
        cost: "$0.001",
        color: "accent",
        desc: "Local cheap model handles mid-complexity queries. 100x cheaper than cloud LLMs.",
        stat: "100x",
        statLabel: "Cost Reduction",
        icon: `<svg class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9 3H5a2 2 0 00-2 2v4m6-6h10a2 2 0 012 2v4M9 3v18m0 0h10a2 2 0 002-2V9M9 21H5a2 2 0 01-2-2V9m0 0h18"/></svg>`
      },
      {
        layer: "04",
        title: "Smart Router",
        cost: "auto",
        color: "primary",
        desc: "Complexity-based model routing. Simple queries go to Haiku, complex ones to Opus.",
        stat: "Auto",
        statLabel: "Model Selection",
        icon: `<svg class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M16 3h5v5M4 20L21 3M21 16v5h-5M15 15l6 6M4 4l5 5"/></svg>`
      }
    ]);
    for (let i = 0, $$length = each_array_3.length; i < $$length; i++) {
      let layer = each_array_3[i];
      $$renderer2.push(`<div${attr_class("layer-card group transition-all duration-700 svelte-1jq6khg", void 0, {
        "opacity-100": layersVisible,
        "translate-y-0": layersVisible,
        "opacity-0": !layersVisible,
        "translate-y-8": !layersVisible
      })}${attr_style(`transition-delay: ${stringify(i * 150)}ms`)}><div class="flex items-start justify-between mb-6 svelte-1jq6khg"><div class="flex items-center gap-3 svelte-1jq6khg"><div${attr_class(`w-10 h-10 rounded-xl bg-${stringify(layer.color)}/10 border border-${stringify(layer.color)}/20 flex items-center justify-center text-${stringify(layer.color)}`, "svelte-1jq6khg")}>${html(layer.icon)}</div> <div class="svelte-1jq6khg"><span class="text-[10px] font-mono text-text-muted uppercase tracking-widest svelte-1jq6khg">Layer ${escape_html(layer.layer)}</span> <h3 class="text-lg font-semibold text-text-primary svelte-1jq6khg">${escape_html(layer.title)}</h3></div></div> <span${attr_class(`font-mono text-sm font-bold ${stringify(layer.color === "accent" ? "text-accent" : "text-primary")}`, "svelte-1jq6khg")}>${escape_html(layer.cost)}</span></div> <p class="text-sm text-text-secondary leading-relaxed mb-6 svelte-1jq6khg">${escape_html(layer.desc)}</p> <div class="flex items-center gap-3 pt-4 border-t border-border svelte-1jq6khg"><span${attr_class(`text-2xl font-bold font-mono ${stringify(layer.color === "accent" ? "text-accent" : "text-primary")}`, "svelte-1jq6khg")}>${escape_html(layer.stat)}</span> <span class="text-xs text-text-muted svelte-1jq6khg">${escape_html(layer.statLabel)}</span></div></div>`);
    }
    $$renderer2.push(`<!--]--></div></div></section> <section data-section="matrix" class="py-24 px-6 svelte-1jq6khg"><div class="max-w-5xl mx-auto svelte-1jq6khg"><div${attr_class(
      `text-center mb-16 transition-all duration-700 ${stringify("opacity-0 translate-y-8")}`,
      "svelte-1jq6khg"
    )}><h2 class="text-3xl sm:text-4xl font-bold text-text-primary mb-4 svelte-1jq6khg">Model-Aware Intelligence</h2> <p class="text-lg text-text-secondary max-w-xl mx-auto svelte-1jq6khg">Expensive models get premium treatment. RuleShield knows which rules fire for each tier.</p></div> <div${attr_class(
      `transition-all duration-700 delay-200 ${stringify("opacity-0 translate-y-8")}`,
      "svelte-1jq6khg"
    )}><div class="bg-surface rounded-2xl border border-border overflow-hidden svelte-1jq6khg"><div class="overflow-x-auto svelte-1jq6khg"><table class="w-full text-sm svelte-1jq6khg"><thead class="svelte-1jq6khg"><tr class="border-b border-border svelte-1jq6khg"><th class="text-left px-6 py-4 text-text-muted font-medium svelte-1jq6khg">Layer</th><th class="px-6 py-4 text-center svelte-1jq6khg"><span class="text-text-muted font-medium svelte-1jq6khg">Haiku</span> <span class="block text-[10px] text-text-muted/60 font-mono svelte-1jq6khg">$0.25/M</span></th><th class="px-6 py-4 text-center svelte-1jq6khg"><span class="text-text-muted font-medium svelte-1jq6khg">Sonnet</span> <span class="block text-[10px] text-text-muted/60 font-mono svelte-1jq6khg">$3/M</span></th><th class="px-6 py-4 text-center svelte-1jq6khg"><span class="text-text-muted font-medium svelte-1jq6khg">Opus</span> <span class="block text-[10px] text-text-muted/60 font-mono svelte-1jq6khg">$15/M</span></th></tr></thead><tbody class="svelte-1jq6khg"><!--[-->`);
    const each_array_4 = ensure_array_like([
      {
        layer: "Semantic Cache",
        haiku: true,
        sonnet: true,
        opus: true
      },
      { layer: "Rule Engine", haiku: true, sonnet: true, opus: false },
      {
        layer: "Hermes Bridge",
        haiku: false,
        sonnet: true,
        opus: true
      },
      {
        layer: "Smart Router",
        haiku: false,
        sonnet: false,
        opus: true
      }
    ]);
    for (let i = 0, $$length = each_array_4.length; i < $$length; i++) {
      let row = each_array_4[i];
      $$renderer2.push(`<tr class="border-b border-border/50 last:border-0 hover:bg-surface-elevated/50 transition-colors svelte-1jq6khg"><td class="px-6 py-4 font-medium text-text-primary svelte-1jq6khg">${escape_html(row.layer)}</td><td class="px-6 py-4 text-center svelte-1jq6khg">`);
      if (row.haiku) {
        $$renderer2.push("<!--[0-->");
        $$renderer2.push(`<span class="text-accent text-lg svelte-1jq6khg">✓</span>`);
      } else {
        $$renderer2.push("<!--[-1-->");
        $$renderer2.push(`<span class="text-text-muted/30 svelte-1jq6khg">--</span>`);
      }
      $$renderer2.push(`<!--]--></td><td class="px-6 py-4 text-center svelte-1jq6khg">`);
      if (row.sonnet) {
        $$renderer2.push("<!--[0-->");
        $$renderer2.push(`<span class="text-accent text-lg svelte-1jq6khg">✓</span>`);
      } else {
        $$renderer2.push("<!--[-1-->");
        $$renderer2.push(`<span class="text-text-muted/30 svelte-1jq6khg">--</span>`);
      }
      $$renderer2.push(`<!--]--></td><td class="px-6 py-4 text-center svelte-1jq6khg">`);
      if (row.opus) {
        $$renderer2.push("<!--[0-->");
        $$renderer2.push(`<span class="text-accent text-lg svelte-1jq6khg">✓</span>`);
      } else {
        $$renderer2.push("<!--[-1-->");
        $$renderer2.push(`<span class="text-text-muted/30 svelte-1jq6khg">--</span>`);
      }
      $$renderer2.push(`<!--]--></td></tr>`);
    }
    $$renderer2.push(`<!--]--></tbody></table></div></div></div></div></section> <section data-section="shadow" class="py-24 px-6 relative svelte-1jq6khg"><div class="absolute inset-0 overflow-hidden pointer-events-none svelte-1jq6khg"><div class="absolute top-1/2 right-0 w-[500px] h-[500px] bg-accent/3 rounded-full blur-[150px] svelte-1jq6khg"></div></div> <div class="max-w-5xl mx-auto relative z-10 svelte-1jq6khg"><div class="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center svelte-1jq6khg"><div${attr_class(
      `transition-all duration-700 ${stringify("opacity-0 translate-y-8")}`,
      "svelte-1jq6khg"
    )}><div class="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-accent/30 bg-accent/5 mb-6 svelte-1jq6khg"><span class="text-xs font-medium text-accent svelte-1jq6khg">Zero Risk</span></div> <h2 class="text-3xl sm:text-4xl font-bold text-text-primary mb-4 svelte-1jq6khg">Prove savings before you commit.</h2> <p class="text-lg text-text-secondary mb-8 leading-relaxed svelte-1jq6khg">Shadow Mode runs parallel to your LLM. Same responses go to your users.
						You see what RuleShield <em class="svelte-1jq6khg">would have saved</em> — with zero risk.</p> <div class="flex flex-wrap gap-6 svelte-1jq6khg"><div class="svelte-1jq6khg"><div class="text-2xl font-bold text-accent font-mono svelte-1jq6khg">14 days</div> <div class="text-xs text-text-muted mt-1 svelte-1jq6khg">Average trial</div></div> <div class="svelte-1jq6khg"><div class="text-2xl font-bold text-accent font-mono svelte-1jq6khg">94.7%</div> <div class="text-xs text-text-muted mt-1 svelte-1jq6khg">Shadow accuracy</div></div> <div class="svelte-1jq6khg"><div class="text-2xl font-bold text-accent font-mono svelte-1jq6khg">142</div> <div class="text-xs text-text-muted mt-1 svelte-1jq6khg">Auto-learned rules</div></div></div></div> <div${attr_class(
      `transition-all duration-700 delay-300 ${stringify("opacity-0 translate-y-12")}`,
      "svelte-1jq6khg"
    )}><div class="bg-surface rounded-2xl border border-border p-6 shadow-2xl shadow-accent/5 svelte-1jq6khg"><div class="flex items-center justify-between mb-6 svelte-1jq6khg"><div class="flex items-center gap-2 svelte-1jq6khg"><div class="w-2 h-2 rounded-full bg-accent animate-pulse svelte-1jq6khg"></div> <span class="text-sm font-medium text-text-primary svelte-1jq6khg">Shadow Mode Active</span></div> <span class="text-xs text-text-muted font-mono svelte-1jq6khg">14 days running</span></div> <div class="grid grid-cols-3 gap-4 mb-6 svelte-1jq6khg"><div class="bg-bg rounded-xl p-4 text-center svelte-1jq6khg"><div class="text-xl font-bold text-accent font-mono svelte-1jq6khg">$4,291</div> <div class="text-[10px] text-text-muted mt-1 uppercase tracking-wider svelte-1jq6khg">Saved</div></div> <div class="bg-bg rounded-xl p-4 text-center svelte-1jq6khg"><div class="text-xl font-bold text-primary font-mono svelte-1jq6khg">142</div> <div class="text-[10px] text-text-muted mt-1 uppercase tracking-wider svelte-1jq6khg">Rules</div></div> <div class="bg-bg rounded-xl p-4 text-center svelte-1jq6khg"><div class="text-xl font-bold text-accent font-mono svelte-1jq6khg">94.7%</div> <div class="text-[10px] text-text-muted mt-1 uppercase tracking-wider svelte-1jq6khg">Accuracy</div></div></div> <div class="bg-bg rounded-xl p-4 mb-4 svelte-1jq6khg"><div class="flex items-end justify-between h-16 gap-1 svelte-1jq6khg"><!--[-->`);
    const each_array_5 = ensure_array_like([30, 45, 38, 55, 62, 48, 70, 65, 78, 72, 85, 80, 88, 92]);
    for (let $$index_5 = 0, $$length = each_array_5.length; $$index_5 < $$length; $$index_5++) {
      let height = each_array_5[$$index_5];
      $$renderer2.push(`<div class="flex-1 bg-gradient-to-t from-accent/20 to-accent/60 rounded-sm svelte-1jq6khg"${attr_style(`height: ${stringify(height)}%`)}></div>`);
    }
    $$renderer2.push(`<!--]--></div> <div class="flex justify-between mt-2 svelte-1jq6khg"><span class="text-[10px] text-text-muted svelte-1jq6khg">Day 1</span> <span class="text-[10px] text-text-muted svelte-1jq6khg">Day 14</span></div></div> <button class="w-full py-2.5 rounded-lg bg-accent/10 border border-accent/20 text-accent text-sm font-medium hover:bg-accent/20 transition-colors cursor-pointer svelte-1jq6khg">Activate Rules</button></div></div></div></div></section> <section data-section="integration" class="py-24 px-6 svelte-1jq6khg"><div class="max-w-5xl mx-auto svelte-1jq6khg"><div${attr_class(
      `text-center mb-16 transition-all duration-700 ${stringify("opacity-0 translate-y-8")}`,
      "svelte-1jq6khg"
    )}><h2 class="text-3xl sm:text-4xl font-bold text-text-primary mb-4 svelte-1jq6khg">The agent that optimizes itself.</h2> <p class="text-lg text-text-secondary max-w-xl mx-auto svelte-1jq6khg">Deep integration with the Hermes ecosystem for autonomous cost optimization.</p></div> <div class="grid grid-cols-1 md:grid-cols-3 gap-6 svelte-1jq6khg"><!--[-->`);
    const each_array_6 = ensure_array_like([
      {
        title: "Hermes Skill",
        desc: "Native Hermes agent skill. RuleShield runs as part of your agent reasoning loop, not just a proxy.",
        tag: "Agent Native",
        iconPath: '<circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/>'
      },
      {
        title: "MCP Server",
        desc: "Model Context Protocol server for real-time rule inspection, cache stats, and configuration from any MCP client.",
        tag: "Protocol",
        iconPath: '<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/>'
      },
      {
        title: "Feedback Loop",
        desc: "User corrections feed back into rule refinement. The system gets smarter with every interaction.",
        tag: "Self-Learning",
        iconPath: '<path d="M21 12a9 9 0 11-6.219-8.56"/><polyline points="22 2 22 8 16 8"/>'
      }
    ]);
    for (let i = 0, $$length = each_array_6.length; i < $$length; i++) {
      let card = each_array_6[i];
      $$renderer2.push(`<div${attr_class("integration-card group transition-all duration-700 svelte-1jq6khg", void 0, {
        "opacity-100": integrationVisible,
        "translate-y-0": integrationVisible,
        "opacity-0": !integrationVisible,
        "translate-y-8": !integrationVisible
      })}${attr_style(`transition-delay: ${stringify(i * 150)}ms`)}><div class="w-12 h-12 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary mb-5 svelte-1jq6khg"><svg class="w-6 h-6 svelte-1jq6khg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">${html(card.iconPath)}</svg></div> <div class="inline-flex px-2 py-0.5 rounded text-[10px] font-medium text-primary bg-primary/10 mb-3 svelte-1jq6khg">${escape_html(card.tag)}</div> <h3 class="text-lg font-semibold text-text-primary mb-2 svelte-1jq6khg">${escape_html(card.title)}</h3> <p class="text-sm text-text-secondary leading-relaxed svelte-1jq6khg">${escape_html(card.desc)}</p></div>`);
    }
    $$renderer2.push(`<!--]--></div></div></section> <section data-section="results" class="py-24 px-6 relative svelte-1jq6khg"><div class="absolute inset-0 overflow-hidden pointer-events-none svelte-1jq6khg"><div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-accent/5 rounded-full blur-[150px] svelte-1jq6khg"></div></div> <div class="max-w-5xl mx-auto relative z-10 svelte-1jq6khg"><div${attr_class(
      `text-center mb-16 transition-all duration-700 ${stringify("opacity-0 translate-y-8")}`,
      "svelte-1jq6khg"
    )}><div class="text-7xl sm:text-8xl font-extrabold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent mb-4 results-glow svelte-1jq6khg">47-82%</div> <h2 class="text-3xl sm:text-4xl font-bold text-text-primary mb-4 svelte-1jq6khg">Proven Cost Reduction</h2> <p class="text-lg text-text-secondary max-w-xl mx-auto svelte-1jq6khg">Tested across four real-world scenarios with different query patterns.</p></div> <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 svelte-1jq6khg"><!--[-->`);
    const each_array_7 = ensure_array_like([
      {
        scenario: "Customer Support",
        savings: "82%",
        queries: "10K",
        desc: "FAQ-heavy with high repetition"
      },
      {
        scenario: "Code Review",
        savings: "61%",
        queries: "5K",
        desc: "Pattern-rich code analysis"
      },
      {
        scenario: "Data Analysis",
        savings: "47%",
        queries: "8K",
        desc: "Mixed complexity queries"
      },
      {
        scenario: "Content Gen",
        savings: "73%",
        queries: "12K",
        desc: "Template-based generation"
      }
    ]);
    for (let i = 0, $$length = each_array_7.length; i < $$length; i++) {
      let result = each_array_7[i];
      $$renderer2.push(`<div${attr_class("result-card transition-all duration-700 svelte-1jq6khg", void 0, {
        "opacity-100": resultsVisible,
        "translate-y-0": resultsVisible,
        "opacity-0": !resultsVisible,
        "translate-y-8": !resultsVisible
      })}${attr_style(`transition-delay: ${stringify(i * 100)}ms`)}><div class="text-3xl font-bold text-accent font-mono mb-1 svelte-1jq6khg">${escape_html(result.savings)}</div> <h3 class="text-sm font-semibold text-text-primary mb-1 svelte-1jq6khg">${escape_html(result.scenario)}</h3> <p class="text-xs text-text-muted mb-3 svelte-1jq6khg">${escape_html(result.desc)}</p> <div class="text-[10px] text-text-muted font-mono svelte-1jq6khg">${escape_html(result.queries)} queries tested</div></div>`);
    }
    $$renderer2.push(`<!--]--></div></div></section> <section id="pricing" data-section="pricing" class="py-24 px-6 svelte-1jq6khg"><div class="max-w-5xl mx-auto svelte-1jq6khg"><div${attr_class(
      `text-center mb-16 transition-all duration-700 ${stringify("opacity-0 translate-y-8")}`,
      "svelte-1jq6khg"
    )}><h2 class="text-3xl sm:text-4xl font-bold text-text-primary mb-4 svelte-1jq6khg">Simple, savings-aligned pricing.</h2> <p class="text-lg text-text-secondary max-w-xl mx-auto svelte-1jq6khg">We only make money when you save money.</p></div> <div${attr_class(
      `grid grid-cols-1 md:grid-cols-3 gap-6 transition-all duration-700 delay-200 ${stringify("opacity-0 translate-y-8")}`,
      "svelte-1jq6khg"
    )}><div class="pricing-card svelte-1jq6khg"><div class="mb-6 svelte-1jq6khg"><h3 class="text-lg font-semibold text-text-primary mb-1 svelte-1jq6khg">Free</h3> <div class="text-4xl font-bold text-text-primary font-mono svelte-1jq6khg">$0</div> <p class="text-sm text-text-muted mt-2 svelte-1jq6khg">For individual developers</p></div> <ul class="space-y-3 mb-8 text-sm text-text-secondary svelte-1jq6khg"><li class="flex items-center gap-2 svelte-1jq6khg"><span class="text-accent svelte-1jq6khg">✓</span> Up to $500/mo savings</li> <li class="flex items-center gap-2 svelte-1jq6khg"><span class="text-accent svelte-1jq6khg">✓</span> 1 project</li> <li class="flex items-center gap-2 svelte-1jq6khg"><span class="text-accent svelte-1jq6khg">✓</span> Semantic cache</li> <li class="flex items-center gap-2 svelte-1jq6khg"><span class="text-accent svelte-1jq6khg">✓</span> Basic rules</li> <li class="flex items-center gap-2 svelte-1jq6khg"><span class="text-accent svelte-1jq6khg">✓</span> Community support</li></ul> <button class="btn-ghost w-full py-2.5 text-sm cursor-pointer svelte-1jq6khg">Start Free</button></div> <div class="pricing-card pricing-card-featured relative svelte-1jq6khg"><div class="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-gradient-to-r from-primary to-accent text-white text-xs font-semibold svelte-1jq6khg">Most Popular</div> <div class="mb-6 svelte-1jq6khg"><h3 class="text-lg font-semibold text-text-primary mb-1 svelte-1jq6khg">Pro</h3> <div class="text-4xl font-bold text-text-primary font-mono svelte-1jq6khg">15%</div> <p class="text-sm text-text-muted mt-2 svelte-1jq6khg">of verified savings</p></div> <ul class="space-y-3 mb-8 text-sm text-text-secondary svelte-1jq6khg"><li class="flex items-center gap-2 svelte-1jq6khg"><span class="text-accent svelte-1jq6khg">✓</span> Unlimited savings</li> <li class="flex items-center gap-2 svelte-1jq6khg"><span class="text-accent svelte-1jq6khg">✓</span> 10 projects</li> <li class="flex items-center gap-2 svelte-1jq6khg"><span class="text-accent svelte-1jq6khg">✓</span> Shadow Mode</li> <li class="flex items-center gap-2 svelte-1jq6khg"><span class="text-accent svelte-1jq6khg">✓</span> Smart Router</li> <li class="flex items-center gap-2 svelte-1jq6khg"><span class="text-accent svelte-1jq6khg">✓</span> Hermes Bridge</li> <li class="flex items-center gap-2 svelte-1jq6khg"><span class="text-accent svelte-1jq6khg">✓</span> Priority support</li></ul> <button class="btn-primary w-full py-2.5 text-sm cursor-pointer svelte-1jq6khg">Start Free Trial</button></div> <div class="pricing-card svelte-1jq6khg"><div class="mb-6 svelte-1jq6khg"><h3 class="text-lg font-semibold text-text-primary mb-1 svelte-1jq6khg">Enterprise</h3> <div class="text-4xl font-bold text-text-primary font-mono svelte-1jq6khg">Custom</div> <p class="text-sm text-text-muted mt-2 svelte-1jq6khg">For large teams</p></div> <ul class="space-y-3 mb-8 text-sm text-text-secondary svelte-1jq6khg"><li class="flex items-center gap-2 svelte-1jq6khg"><span class="text-accent svelte-1jq6khg">✓</span> Volume discounts</li> <li class="flex items-center gap-2 svelte-1jq6khg"><span class="text-accent svelte-1jq6khg">✓</span> Unlimited projects</li> <li class="flex items-center gap-2 svelte-1jq6khg"><span class="text-accent svelte-1jq6khg">✓</span> SSO &amp; SAML</li> <li class="flex items-center gap-2 svelte-1jq6khg"><span class="text-accent svelte-1jq6khg">✓</span> Custom rules</li> <li class="flex items-center gap-2 svelte-1jq6khg"><span class="text-accent svelte-1jq6khg">✓</span> SLA guarantee</li> <li class="flex items-center gap-2 svelte-1jq6khg"><span class="text-accent svelte-1jq6khg">✓</span> Dedicated support</li></ul> <button class="btn-ghost w-full py-2.5 text-sm cursor-pointer svelte-1jq6khg">Contact Sales</button></div></div> <p${attr_class(`text-center text-sm text-text-muted mt-8 transition-all duration-700 delay-500 ${stringify("opacity-0")}`, "svelte-1jq6khg")}><span class="text-accent font-semibold svelte-1jq6khg">3x ROI guaranteed</span> or your money back. No credit card required to start.</p></div></section> <section data-section="roadmap" class="py-24 px-6 svelte-1jq6khg"><div class="max-w-4xl mx-auto svelte-1jq6khg"><div${attr_class(
      `text-center mb-16 transition-all duration-700 ${stringify("opacity-0 translate-y-8")}`,
      "svelte-1jq6khg"
    )}><h2 class="text-3xl sm:text-4xl font-bold text-text-primary mb-4 svelte-1jq6khg">Self-Evolution Roadmap</h2> <p class="text-lg text-text-secondary max-w-xl mx-auto svelte-1jq6khg">RuleShield doesn't just save you money -- it gets smarter over time.</p></div> <div${attr_class(
      `relative transition-all duration-700 delay-200 ${stringify("opacity-0 translate-y-8")}`,
      "svelte-1jq6khg"
    )}><div class="absolute left-6 md:left-1/2 top-0 bottom-0 w-px bg-gradient-to-b from-primary via-accent to-primary/20 svelte-1jq6khg"></div> <!--[-->`);
    const each_array_8 = ensure_array_like([
      {
        phase: "NOW",
        title: "Cache + Rules + Router",
        items: [
          "Semantic caching with embedding similarity",
          "Auto-extracted decision rules",
          "Complexity-based model routing",
          "Hermes Bridge for local inference"
        ],
        status: "live"
      },
      {
        phase: "NEXT",
        title: "Shadow + Feedback + Cron",
        items: [
          "Shadow Mode validation",
          "User feedback integration",
          "Scheduled rule retraining",
          "A/B testing framework"
        ],
        status: "building"
      },
      {
        phase: "FUTURE",
        title: "RL + GEPA + Marketplace",
        items: [
          "Reinforcement learning optimization",
          "GEPA evolutionary patterns",
          "Community rule marketplace",
          "Multi-tenant cost sharing"
        ],
        status: "planned"
      }
    ]);
    for (let i = 0, $$length = each_array_8.length; i < $$length; i++) {
      let milestone = each_array_8[i];
      $$renderer2.push(`<div${attr_class(`relative flex items-start gap-6 mb-12 last:mb-0 ${stringify(i % 2 === 0 ? "md:flex-row" : "md:flex-row-reverse")} flex-row`, "svelte-1jq6khg")}><div class="hidden md:block md:w-1/2 svelte-1jq6khg"></div> <div${attr_class(
        `absolute left-6 md:left-1/2 -translate-x-1/2 w-3 h-3 rounded-full ${stringify(milestone.status === "live" ? "bg-accent shadow-[0_0_12px_rgba(0,212,170,0.5)]" : milestone.status === "building" ? "bg-primary shadow-[0_0_12px_rgba(108,92,231,0.5)]" : "bg-border")} z-10 mt-6`,
        "svelte-1jq6khg"
      )}></div> <div${attr_class(`ml-12 md:ml-0 md:w-1/2 ${stringify(i % 2 === 0 ? "md:pl-10" : "md:pr-10")}`, "svelte-1jq6khg")}><div class="bg-surface rounded-xl border border-border p-6 hover:border-primary/30 transition-colors svelte-1jq6khg"><div class="flex items-center gap-3 mb-3 svelte-1jq6khg"><span${attr_class(
        `font-mono text-xs font-bold ${stringify(milestone.status === "live" ? "text-accent" : milestone.status === "building" ? "text-primary" : "text-text-muted")} uppercase tracking-widest`,
        "svelte-1jq6khg"
      )}>${escape_html(milestone.phase)}</span> <span${attr_class(
        `px-2 py-0.5 rounded text-[10px] font-medium ${stringify(milestone.status === "live" ? "bg-accent/10 text-accent" : milestone.status === "building" ? "bg-primary/10 text-primary" : "bg-border text-text-muted")}`,
        "svelte-1jq6khg"
      )}>${escape_html(milestone.status === "live" ? "Live" : milestone.status === "building" ? "Building" : "Planned")}</span></div> <h3 class="text-lg font-semibold text-text-primary mb-3 svelte-1jq6khg">${escape_html(milestone.title)}</h3> <ul class="space-y-2 svelte-1jq6khg"><!--[-->`);
      const each_array_9 = ensure_array_like(milestone.items);
      for (let $$index_8 = 0, $$length2 = each_array_9.length; $$index_8 < $$length2; $$index_8++) {
        let item = each_array_9[$$index_8];
        $$renderer2.push(`<li class="flex items-center gap-2 text-sm text-text-secondary svelte-1jq6khg"><span${attr_class(
          `w-1 h-1 rounded-full ${stringify(milestone.status === "live" ? "bg-accent" : milestone.status === "building" ? "bg-primary" : "bg-text-muted")} flex-shrink-0`,
          "svelte-1jq6khg"
        )}></span> ${escape_html(item)}</li>`);
      }
      $$renderer2.push(`<!--]--></ul></div></div></div>`);
    }
    $$renderer2.push(`<!--]--></div></div></section> <section id="cta" data-section="cta" class="py-24 px-6 relative svelte-1jq6khg"><div class="absolute inset-0 overflow-hidden pointer-events-none svelte-1jq6khg"><div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[600px] bg-primary/5 rounded-full blur-[150px] svelte-1jq6khg"></div> <div class="absolute bottom-0 right-1/3 w-[400px] h-[400px] bg-accent/5 rounded-full blur-[120px] svelte-1jq6khg"></div></div> <div class="max-w-3xl mx-auto text-center relative z-10 svelte-1jq6khg"><div${attr_class(
      `transition-all duration-700 ${stringify("opacity-0 translate-y-8")}`,
      "svelte-1jq6khg"
    )}><h2 class="text-3xl sm:text-4xl lg:text-5xl font-bold text-text-primary mb-6 svelte-1jq6khg">Stop paying for answers<br class="svelte-1jq6khg"/>you already have.</h2> <p class="text-lg text-text-secondary mb-10 max-w-lg mx-auto svelte-1jq6khg">One line. One import. Up to 82% savings on your LLM costs.</p> <div class="inline-flex items-center gap-3 bg-surface rounded-xl border border-border px-6 py-4 mb-10 svelte-1jq6khg"><span class="text-text-muted font-mono text-sm svelte-1jq6khg">$</span> <code class="font-mono text-sm text-accent svelte-1jq6khg">pip install ruleshield-hermes</code> <button class="text-text-muted hover:text-text-primary transition-colors cursor-pointer svelte-1jq6khg" aria-label="Copy install command"><svg class="w-4 h-4 svelte-1jq6khg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" class="svelte-1jq6khg"></rect><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" class="svelte-1jq6khg"></path></svg></button></div> <div class="flex flex-col sm:flex-row items-center justify-center gap-4 svelte-1jq6khg"><button class="btn-primary text-base px-8 py-3.5 w-full sm:w-auto cursor-pointer svelte-1jq6khg">Start Free -- No Credit Card <svg class="inline-block ml-2 w-4 h-4 svelte-1jq6khg" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 8h10M9 4l4 4-4 4" class="svelte-1jq6khg"></path></svg></button> <button class="btn-ghost text-base px-8 py-3.5 w-full sm:w-auto cursor-pointer svelte-1jq6khg">Book Demo</button></div></div></div></section> <footer class="border-t border-border py-12 px-6 svelte-1jq6khg"><div class="max-w-5xl mx-auto svelte-1jq6khg"><div class="flex flex-col md:flex-row items-center justify-between gap-6 svelte-1jq6khg"><div class="flex items-center gap-2 svelte-1jq6khg"><div class="w-6 h-6 rounded-md bg-gradient-to-br from-primary to-accent flex items-center justify-center text-white font-bold text-[10px] svelte-1jq6khg">R</div> <span class="text-sm font-semibold text-text-primary svelte-1jq6khg">RuleShield</span></div> <div class="flex flex-wrap items-center justify-center gap-6 text-sm text-text-muted svelte-1jq6khg"><a href="https://github.com/ruleshield" class="hover:text-text-primary transition-colors svelte-1jq6khg">GitHub</a> <a href="#" class="hover:text-text-primary transition-colors svelte-1jq6khg">Docs</a> <button class="hover:text-text-primary transition-colors cursor-pointer svelte-1jq6khg">Pricing</button> <a href="#" class="hover:text-text-primary transition-colors svelte-1jq6khg">Privacy</a> <a href="#" class="hover:text-text-primary transition-colors svelte-1jq6khg">Terms</a></div> <p class="text-xs text-text-muted text-center md:text-right svelte-1jq6khg">Built for <span class="text-primary svelte-1jq6khg">Hermes Agent Hackathon</span> by NousResearch</p></div></div></footer></main>`);
  });
}
export {
  _page as default
};
