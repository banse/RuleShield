import { h as head, e as escape_html, a as ensure_array_like, d as attr_style, b as attr, f as derived, s as stringify } from "../../../chunks/index2.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { data } = $$props;
    let totalRequests = derived(() => data.totalRequests);
    let breakdown = derived(() => data.breakdown);
    let costWithout = derived(() => data.costWithout);
    let costWith = derived(() => data.costWith);
    let savedUsd = derived(() => data.savedUsd);
    let savedPct = derived(() => data.savedPct);
    let topRules = derived(() => data.topRules);
    let expensivePrompts = derived(() => data.expensivePrompts);
    let coffees = derived(() => savedUsd() > 0 ? Math.round(savedUsd() / 5 * 10) / 10 : 0);
    const typeColors = {
      cache: "#00D4AA",
      rule: "#6C5CE7",
      routed: "#4A9EFF",
      template: "#FFB84D",
      passthrough: "#3B82F6",
      llm: "#FF6B6B"
    };
    function formatCost(cost) {
      return "$" + cost.toFixed(2);
    }
    function barWidth(count) {
      if (totalRequests() === 0) return 0;
      return count / totalRequests() * 100;
    }
    let tweetText = derived(() => encodeURIComponent(`I saved ${formatCost(savedUsd())} (${savedPct().toFixed(1)}%) on my LLM costs with @RuleShield over the last 30 days. That's ${coffees()} cups of coffee!

#RuleShield #LLM #CostOptimization`));
    let tweetUrl = derived(() => `https://twitter.com/intent/tweet?text=${tweetText()}`);
    head("17izldi", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>RuleShield Wrapped - Savings Report</title>`);
      });
    });
    $$renderer2.push(`<header class="border-b border-border px-8 py-5"><div class="mx-auto flex max-w-[900px] items-center justify-between"><div class="flex items-center gap-3"><a href="/" class="flex items-center gap-3 transition-opacity hover:opacity-80"><div class="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/20"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-primary"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg></div> <span class="text-lg font-semibold tracking-tight text-text-primary">RuleShield</span></a> <span class="rounded-md bg-surface-elevated px-2 py-0.5 text-xs font-medium text-text-muted">Wrapped</span></div> <a href="/" class="flex items-center gap-1.5 rounded-md border border-border bg-surface-elevated px-3 py-1.5 text-xs font-medium text-text-secondary transition-all hover:border-primary/40 hover:text-primary"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"></path></svg> Dashboard</a></div></header> <main class="mx-auto max-w-[900px] px-8 py-12"><section class="mb-16 text-center"><p class="mb-2 text-xs font-semibold uppercase tracking-[3px] text-text-muted">RuleShield Wrapped</p> <h1 class="mb-4 bg-gradient-to-r from-primary to-accent bg-clip-text text-5xl font-extrabold tracking-tight" style="-webkit-background-clip: text; -webkit-text-fill-color: transparent;">30-Day Savings Report</h1> <div class="mt-12 mb-4"><p class="mb-2 text-xs font-semibold uppercase tracking-[2px] text-text-muted">Total Saved</p> <p class="font-mono text-7xl font-extrabold text-accent" style="text-shadow: 0 0 60px rgba(0, 212, 170, 0.3);">${escape_html(formatCost(savedUsd()))}</p> <p class="mt-3 font-mono text-lg text-text-secondary">${escape_html(savedPct().toFixed(1))}% savings rate</p></div> <div class="mt-8 inline-flex items-center gap-3 rounded-full border border-border bg-surface px-6 py-3"><span class="text-2xl">☕</span> <span class="text-base text-text-secondary">That's <span class="font-mono font-bold text-accent">${escape_html(coffees())}</span> cups of coffee</span></div></section> <div class="mx-auto mb-12 h-px w-full" style="background: linear-gradient(90deg, transparent, #2A2A3C, transparent);"></div> <section class="mb-8 grid grid-cols-3 gap-5"><div class="rounded-xl border border-border bg-surface p-6 text-center transition-all hover:border-primary/40"><p class="mb-2 text-xs font-semibold uppercase tracking-wider text-text-muted">Total Requests</p> <p class="font-mono text-4xl font-bold text-text-primary">${escape_html(totalRequests())}</p></div> <div class="rounded-xl border border-border bg-surface p-6 text-center transition-all hover:border-text-muted/40"><p class="mb-2 text-xs font-semibold uppercase tracking-wider text-text-muted">Cost Without</p> <p class="font-mono text-4xl font-bold text-text-secondary">${escape_html(formatCost(costWithout()))}</p></div> <div class="rounded-xl border border-border bg-surface p-6 text-center transition-all hover:border-accent/40"><p class="mb-2 text-xs font-semibold uppercase tracking-wider text-text-muted">Cost With</p> <p class="font-mono text-4xl font-bold text-text-primary">${escape_html(formatCost(costWith()))}</p></div></section> <section class="mb-8 rounded-xl border border-border bg-surface p-8"><h2 class="mb-6 text-sm font-semibold uppercase tracking-wider text-text-muted">Resolution Breakdown</h2> <div class="space-y-4"><!--[-->`);
    const each_array = ensure_array_like(Object.entries(breakdown()));
    for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
      let [type, count] = each_array[$$index];
      const pct = barWidth(count);
      const color = typeColors[type] ?? "#6B6B82";
      $$renderer2.push(`<div class="flex items-center gap-4"><div class="flex w-28 items-center gap-2"><span class="inline-block h-2.5 w-2.5 rounded-full"${attr_style(`background: ${stringify(color)};`)}></span> <span class="text-sm font-medium text-text-secondary">${escape_html(type.toUpperCase())}</span></div> <div class="flex-1"><div class="h-3 overflow-hidden rounded-full bg-surface-elevated"><div class="h-full rounded-full transition-all duration-700"${attr_style(`width: ${stringify(pct)}%; background: ${stringify(color)};`)}></div></div></div> <div class="flex w-24 items-baseline justify-end gap-2"><span class="font-mono text-sm font-bold text-text-primary">${escape_html(count)}</span> <span class="font-mono text-xs text-text-muted">${escape_html(pct.toFixed(1))}%</span></div></div>`);
    }
    $$renderer2.push(`<!--]--></div></section> <section class="mb-8 grid grid-cols-[1.2fr_1fr] gap-6"><div class="rounded-xl border border-border bg-surface"><div class="border-b border-border px-6 py-4"><h2 class="text-sm font-semibold uppercase tracking-wider text-text-muted">Top 5 Rules</h2></div> <div class="overflow-x-auto"><table class="w-full"><thead><tr class="border-b border-border/50 text-left text-xs font-medium uppercase tracking-wider text-text-muted"><th class="w-10 px-6 py-3">#</th><th class="px-4 py-3">Pattern</th><th class="w-16 px-4 py-3 text-right">Hits</th></tr></thead><tbody>`);
    if (topRules().length === 0) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<tr><td colspan="3" class="px-6 py-10 text-center text-sm text-text-muted">No rule hits recorded yet</td></tr>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--><!--[-->`);
    const each_array_1 = ensure_array_like(topRules());
    for (let i = 0, $$length = each_array_1.length; i < $$length; i++) {
      let rule = each_array_1[i];
      $$renderer2.push(`<tr class="border-b border-border/30 transition-colors hover:bg-surface-elevated/50"><td class="px-6 py-3 font-mono text-xs text-text-muted">${escape_html(i + 1)}</td><td class="max-w-[250px] px-4 py-3"><span class="block truncate font-mono text-xs text-text-secondary"${attr("title", rule.prompt)}>${escape_html(rule.prompt.slice(0, 45))}${escape_html(rule.prompt.length > 45 ? "..." : "")}</span></td><td class="px-4 py-3 text-right font-mono text-sm font-bold text-primary">${escape_html(rule.hits)}</td></tr>`);
    }
    $$renderer2.push(`<!--]--></tbody></table></div></div> <div class="rounded-xl border border-border bg-surface"><div class="border-b border-border px-6 py-4"><h2 class="text-sm font-semibold uppercase tracking-wider text-text-muted">Most Expensive</h2></div> <div class="overflow-x-auto"><table class="w-full"><thead><tr class="border-b border-border/50 text-left text-xs font-medium uppercase tracking-wider text-text-muted"><th class="w-10 px-6 py-3">#</th><th class="px-4 py-3">Prompt</th><th class="w-20 px-4 py-3 text-right">Cost</th></tr></thead><tbody>`);
    if (expensivePrompts().length === 0) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<tr><td colspan="3" class="px-6 py-10 text-center text-sm text-text-muted">No cost data yet</td></tr>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--><!--[-->`);
    const each_array_2 = ensure_array_like(expensivePrompts());
    for (let i = 0, $$length = each_array_2.length; i < $$length; i++) {
      let ep = each_array_2[i];
      $$renderer2.push(`<tr class="border-b border-border/30 transition-colors hover:bg-surface-elevated/50"><td class="px-6 py-3 font-mono text-xs text-text-muted">${escape_html(i + 1)}</td><td class="max-w-[200px] px-4 py-3"><span class="block truncate font-mono text-xs text-text-secondary"${attr("title", ep.prompt)}>${escape_html(ep.prompt.slice(0, 35))}${escape_html(ep.prompt.length > 35 ? "..." : "")}</span> <span class="text-[10px] text-text-muted">${escape_html(ep.model)}</span></td><td class="px-4 py-3 text-right font-mono text-sm font-bold text-warning">$${escape_html(ep.cost.toFixed(4))}</td></tr>`);
    }
    $$renderer2.push(`<!--]--></tbody></table></div></div></section> <div class="mx-auto mb-8 h-px w-full" style="background: linear-gradient(90deg, transparent, #2A2A3C, transparent);"></div> <section class="mb-12 rounded-xl border border-primary/30 bg-surface p-8"><div class="mb-6 flex items-center gap-2"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-primary"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"></path><polyline points="16 6 12 2 8 6"></polyline><line x1="12" y1="2" x2="12" y2="15"></line></svg> <h2 class="text-sm font-semibold uppercase tracking-wider text-text-muted">Share Your Savings</h2></div> <div class="mb-6 rounded-lg border border-border bg-surface-elevated p-5"><p class="font-mono text-sm leading-relaxed text-text-secondary">I saved ${escape_html(formatCost(savedUsd()))} (${escape_html(savedPct().toFixed(1))}%) on my LLM costs with
				@RuleShield over the last 30 days. That's ${escape_html(coffees())} cups of coffee! <br/><br/> #RuleShield #LLM #CostOptimization</p></div> <a${attr("href", tweetUrl())} target="_blank" rel="noopener noreferrer" class="inline-flex items-center gap-2 rounded-lg border border-primary/40 bg-primary/10 px-5 py-2.5 text-sm font-semibold text-primary transition-all hover:bg-primary/20 hover:shadow-[0_0_20px_rgba(108,92,231,0.15)]"><svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"></path></svg> Share on X</a></section> <footer class="flex items-center justify-between border-t border-border/50 pt-6 pb-8"><p class="text-xs text-text-muted">RuleShield Hermes -- LLM Cost Optimizer</p> <p class="font-mono text-xs text-text-muted">Generated ${escape_html(new Date(data.loadedAt).toLocaleString())}</p></footer></main>`);
  });
}
export {
  _page as default
};
