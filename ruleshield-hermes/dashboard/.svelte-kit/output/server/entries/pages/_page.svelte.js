import { c as attr_class, e as escape_html, d as attr_style, s as stringify, a as ensure_array_like, b as attr, f as derived } from "../../chunks/index2.js";
import "@sveltejs/kit/internal";
import "../../chunks/exports.js";
import "../../chunks/utils.js";
import "@sveltejs/kit/internal/server";
import "../../chunks/root.js";
import "../../chunks/state.svelte.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { data } = $$props;
    let refreshing = false;
    let stats = derived(() => data.stats);
    let connected = derived(() => data.connected);
    let requests = derived(() => data.requests);
    let rules = derived(() => data.rules);
    let shadow = derived(() => data.shadow);
    let cachePct = derived(() => stats().total_requests > 0 ? Math.round(stats().cache_hits / stats().total_requests * 100) : 0);
    let rulePct = derived(() => stats().total_requests > 0 ? Math.round(stats().rule_hits / stats().total_requests * 100) : 0);
    let routedPct = derived(() => stats().total_requests > 0 ? Math.round(stats().routed / stats().total_requests * 100) : 0);
    let passthroughPct = derived(() => stats().total_requests > 0 ? Math.round(stats().passthrough / stats().total_requests * 100) : 0);
    let llmPct = derived(() => stats().total_requests > 0 ? Math.round(stats().llm_calls / stats().total_requests * 100) : 0);
    function formatCost(cost) {
      return "$" + cost.toFixed(2);
    }
    function formatLatency(ms) {
      if (ms < 1e3) return ms.toFixed(0) + "ms";
      return (ms / 1e3).toFixed(1) + "s";
    }
    function truncate(str, len) {
      if (!str) return "";
      return str.length > len ? str.slice(0, len) + "..." : str;
    }
    function typeBadgeClasses(type) {
      switch (type?.toUpperCase()) {
        case "CACHE":
          return "bg-accent/15 text-accent border-accent/30";
        case "RULE":
          return "bg-primary/15 text-primary border-primary/30";
        case "ROUTED":
          return "bg-routed/15 text-routed border-routed/30";
        case "PASSTHROUGH":
          return "bg-[#3B82F6]/15 text-[#3B82F6] border-[#3B82F6]/30";
        case "LLM":
          return "bg-warning/15 text-warning border-warning/30";
        default:
          return "bg-text-muted/15 text-text-muted border-text-muted/30";
      }
    }
    $$renderer2.push(`<header class="border-b border-border px-8 py-5"><div class="mx-auto flex max-w-[1440px] items-center justify-between"><div class="flex items-center gap-3"><div class="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/20"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-primary"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg></div> <h1 class="text-lg font-semibold tracking-tight text-text-primary">RuleShield</h1> <span class="rounded-md bg-surface-elevated px-2 py-0.5 text-xs font-medium text-text-muted">Dashboard</span> <a href="/home" class="ml-2 flex items-center gap-1.5 rounded-md border border-border bg-surface px-2.5 py-1 text-xs font-medium text-text-muted transition-all hover:border-primary/40 hover:text-primary"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect></svg> All Pages</a></div> <div class="flex items-center gap-4"><div class="flex items-center gap-2"><div${attr_class("h-1.5 w-1.5 rounded-full transition-all duration-300", void 0, {
      "bg-accent": connected(),
      "bg-error": !connected(),
      "shadow-[0_0_8px_rgba(0,212,170,0.6)]": connected() && refreshing
    })}></div> <span${attr_class("text-xs font-medium", void 0, { "text-accent": connected(), "text-error": !connected() })}>${escape_html(connected() ? "Live" : "Disconnected")}</span></div> <div class="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5"><div${attr_class("h-2 w-2 rounded-full", void 0, {
      "bg-accent": connected(),
      "bg-error": !connected(),
      "animate-pulse": connected()
    })}></div> <span class="font-mono text-xs text-text-secondary">${escape_html(connected() ? "localhost:8337" : "offline")}</span></div></div></div></header> <main class="mx-auto max-w-[1440px] space-y-6 px-8 py-8"><div class="grid grid-cols-6 gap-4"><div class="group rounded-xl border border-border bg-surface p-6 transition-all duration-200 hover:border-primary/40 hover:shadow-[0_0_20px_rgba(108,92,231,0.08)]"><p class="mb-1 text-xs font-medium uppercase tracking-wider text-text-muted">Total Requests</p> <p class="font-mono text-3xl font-bold text-text-primary">${escape_html(stats().total_requests)}</p></div> <div class="group rounded-xl border border-border bg-surface p-6 transition-all duration-200 hover:border-accent/40 hover:shadow-[0_0_20px_rgba(0,212,170,0.08)]"><p class="mb-1 text-xs font-medium uppercase tracking-wider text-text-muted">Cache Hits</p> <div class="flex items-baseline gap-2"><p class="font-mono text-3xl font-bold text-accent">${escape_html(stats().cache_hits)}</p> <span class="font-mono text-sm text-accent/70">${escape_html(cachePct())}%</span></div></div> <div class="group rounded-xl border border-border bg-surface p-6 transition-all duration-200 hover:border-primary/40 hover:shadow-[0_0_20px_rgba(108,92,231,0.08)]"><p class="mb-1 text-xs font-medium uppercase tracking-wider text-text-muted">Rule Hits</p> <div class="flex items-baseline gap-2"><p class="font-mono text-3xl font-bold text-primary">${escape_html(stats().rule_hits)}</p> <span class="font-mono text-sm text-primary/70">${escape_html(rulePct())}%</span></div></div> <div class="group rounded-xl border border-border bg-surface p-6 transition-all duration-200 hover:border-routed/40 hover:shadow-[0_0_20px_rgba(74,158,255,0.08)]"><p class="mb-1 text-xs font-medium uppercase tracking-wider text-text-muted">Routed</p> <div class="flex items-baseline gap-2"><p class="font-mono text-3xl font-bold text-routed">${escape_html(stats().routed)}</p> <span class="font-mono text-sm text-routed/70">${escape_html(routedPct())}%</span></div></div> <div class="group rounded-xl border border-border bg-surface p-6 transition-all duration-200 hover:border-[#3B82F6]/40 hover:shadow-[0_0_20px_rgba(59,130,246,0.08)]"><p class="mb-1 text-xs font-medium uppercase tracking-wider text-text-muted">Passthrough</p> <div class="flex items-baseline gap-2"><p class="font-mono text-3xl font-bold text-[#3B82F6]">${escape_html(stats().passthrough)}</p> <span class="font-mono text-sm text-[#3B82F6]/70">${escape_html(passthroughPct())}%</span></div></div> <div class="group rounded-xl border border-border bg-surface p-6 transition-all duration-200 hover:border-warning/40 hover:shadow-[0_0_20px_rgba(255,184,77,0.08)]"><p class="mb-1 text-xs font-medium uppercase tracking-wider text-text-muted">LLM Calls</p> <div class="flex items-baseline gap-2"><p class="font-mono text-3xl font-bold text-warning">${escape_html(stats().llm_calls)}</p> <span class="font-mono text-sm text-warning/70">${escape_html(llmPct())}%</span></div></div></div> <div class="rounded-xl border border-border bg-surface p-8"><div class="mb-6 flex items-center gap-2"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-accent"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg> <h2 class="text-sm font-semibold uppercase tracking-wider text-text-muted">Cost Savings</h2></div> <div class="grid grid-cols-[1fr_1fr_auto] items-end gap-12"><div class="space-y-4"><div><p class="mb-1 text-xs text-text-muted">Cost Without RuleShield</p> <p class="font-mono text-2xl font-semibold text-text-secondary">${escape_html(formatCost(stats().cost_without))}</p></div> <div><p class="mb-1 text-xs text-text-muted">Cost With RuleShield</p> <p class="font-mono text-2xl font-semibold text-text-primary">${escape_html(formatCost(stats().cost_with))}</p></div></div> <div class="space-y-3"><div class="flex items-center justify-between"><p class="text-xs text-text-muted">Savings Rate</p> <p class="font-mono text-sm font-semibold text-accent">${escape_html(stats().savings_pct.toFixed(1))}%</p></div> <div class="h-3 overflow-hidden rounded-full bg-surface-elevated"><div class="h-full rounded-full transition-all duration-700 ease-out"${attr_style(`width: ${stringify(Math.min(stats().savings_pct, 100))}%; background: linear-gradient(90deg, #6C5CE7, #00D4AA);`)}></div></div> <div class="flex justify-between font-mono text-xs text-text-muted"><span>0%</span> <span>100%</span></div></div> <div class="text-right"><p class="mb-1 text-xs text-text-muted">Total Saved</p> <p class="font-mono text-5xl font-bold text-accent" style="text-shadow: 0 0 30px rgba(0, 212, 170, 0.3);">${escape_html(formatCost(stats().saved))}</p></div></div></div> <div class="grid grid-cols-[1.5fr_1fr] gap-6"><div class="rounded-xl border border-border bg-surface"><div class="border-b border-border px-6 py-4"><h2 class="text-sm font-semibold uppercase tracking-wider text-text-muted">Recent Requests</h2></div> <div class="overflow-x-auto"><table class="w-full"><thead><tr class="border-b border-border/50 text-left text-xs font-medium uppercase tracking-wider text-text-muted"><th class="px-6 py-3 w-12">#</th><th class="px-4 py-3">Prompt</th><th class="px-4 py-3 w-24">Type</th><th class="px-4 py-3 w-20 text-right">Cost</th><th class="px-4 py-3 w-20 text-right">Time</th></tr></thead><tbody>`);
    if (requests().length === 0) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<tr><td colspan="5" class="px-6 py-12 text-center text-sm text-text-muted">No requests yet. Send a request through RuleShield to see it here.</td></tr>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--><!--[-->`);
    const each_array = ensure_array_like(requests().slice(0, 10));
    for (let i = 0, $$length = each_array.length; i < $$length; i++) {
      let req = each_array[i];
      $$renderer2.push(`<tr class="border-b border-border/30 transition-colors hover:bg-surface-elevated/50"><td class="px-6 py-3 font-mono text-xs text-text-muted">${escape_html(req.id)}</td><td class="max-w-[300px] px-4 py-3"><span class="block truncate font-mono text-xs text-text-secondary"${attr("title", req.prompt)}>"${escape_html(truncate(req.prompt, 45))}"</span></td><td class="px-4 py-3"><span${attr_class(`inline-flex items-center rounded-md border px-2 py-0.5 font-mono text-[10px] font-semibold uppercase ${stringify(typeBadgeClasses(req.type))}`)}>${escape_html(req.type)}</span></td><td class="px-4 py-3 text-right font-mono text-xs text-text-secondary">${escape_html(formatCost(req.cost))}</td><td class="px-4 py-3 text-right font-mono text-xs text-text-muted">${escape_html(formatLatency(req.latency_ms))}</td></tr>`);
    }
    $$renderer2.push(`<!--]--></tbody></table></div></div> <div class="rounded-xl border border-border bg-surface"><div class="flex items-center justify-between border-b border-border px-6 py-4"><h2 class="text-sm font-semibold uppercase tracking-wider text-text-muted">Top Rules</h2> <a href="/rules" class="flex items-center gap-1.5 rounded-md border border-border bg-surface-elevated px-3 py-1.5 text-xs font-medium text-text-secondary transition-all hover:border-primary/40 hover:text-primary">Rule Explorer <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"></path></svg></a></div> <div class="overflow-x-auto"><table class="w-full"><thead><tr class="border-b border-border/50 text-left text-xs font-medium uppercase tracking-wider text-text-muted"><th class="px-6 py-3">Rule</th><th class="px-4 py-3 w-16 text-right">Hits</th><th class="px-4 py-3 w-24 text-right">Confidence</th><th class="px-4 py-3 w-20 text-right">Status</th></tr></thead><tbody>`);
    if (rules().length === 0) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<tr><td colspan="4" class="px-6 py-12 text-center text-sm text-text-muted">No rules defined yet.</td></tr>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--><!--[-->`);
    const each_array_1 = ensure_array_like(rules());
    for (let $$index_1 = 0, $$length = each_array_1.length; $$index_1 < $$length; $$index_1++) {
      let rule = each_array_1[$$index_1];
      $$renderer2.push(`<tr class="border-b border-border/30 transition-colors hover:bg-surface-elevated/50"><td class="px-6 py-3 text-sm text-text-primary">${escape_html(rule.name)}</td><td class="px-4 py-3 text-right font-mono text-sm font-semibold text-primary">${escape_html(rule.hits)}</td><td class="px-4 py-3 text-right"><div class="flex items-center justify-end gap-2"><div class="h-1.5 w-16 overflow-hidden rounded-full bg-surface-elevated"><div class="h-full rounded-full bg-accent"${attr_style(`width: ${stringify(rule.confidence)}%`)}></div></div> <span class="font-mono text-xs text-text-secondary">${escape_html(rule.confidence)}%</span></div></td><td class="px-4 py-3 text-right"><span class="inline-flex items-center gap-1 rounded-full bg-accent/10 px-2 py-0.5 text-[10px] font-semibold uppercase text-accent"><span class="h-1.5 w-1.5 rounded-full bg-accent"></span> ${escape_html(rule.status)}</span></td></tr>`);
    }
    $$renderer2.push(`<!--]--></tbody></table></div></div></div> `);
    if (shadow() && shadow().total_shadows > 0) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<div class="rounded-xl border border-primary/30 bg-surface p-8"><div class="mb-6 flex items-center gap-2"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-primary"><circle cx="12" cy="12" r="10"></circle><path d="M12 16v-4M12 8h.01"></path></svg> <h2 class="text-sm font-semibold uppercase tracking-wider text-text-muted">Shadow Mode</h2> <span class="rounded-full bg-primary/15 px-2 py-0.5 text-[10px] font-semibold uppercase text-primary">Experimental</span></div> <div class="grid grid-cols-3 gap-8"><div><p class="mb-1 text-xs text-text-muted">Average Similarity</p> <div class="flex items-baseline gap-2"><p class="font-mono text-3xl font-bold text-primary">${escape_html(shadow().avg_similarity.toFixed(1))}%</p></div> <div class="mt-2 h-2 overflow-hidden rounded-full bg-surface-elevated"><div class="h-full rounded-full bg-primary transition-all duration-500"${attr_style(`width: ${stringify(shadow().avg_similarity)}%`)}></div></div></div> <div><p class="mb-1 text-xs text-text-muted">Rules Ready for Activation</p> <p class="font-mono text-3xl font-bold text-accent">${escape_html(shadow().rules_ready)}</p> <p class="mt-1 text-xs text-text-muted">of ${escape_html(shadow().total_shadows)} shadow entries</p></div> <div><p class="mb-1 text-xs text-text-muted">Total Shadow Comparisons</p> <p class="font-mono text-3xl font-bold text-text-primary">${escape_html(shadow().total_shadows)}</p></div></div> `);
      if (shadow().entries && shadow().entries.length > 0) {
        $$renderer2.push("<!--[0-->");
        $$renderer2.push(`<div class="mt-6 border-t border-border pt-4"><p class="mb-3 text-xs font-medium uppercase tracking-wider text-text-muted">Recent Shadow Comparisons</p> <div class="space-y-2"><!--[-->`);
        const each_array_2 = ensure_array_like(shadow().entries.slice(0, 5));
        for (let $$index_2 = 0, $$length = each_array_2.length; $$index_2 < $$length; $$index_2++) {
          let entry = each_array_2[$$index_2];
          $$renderer2.push(`<div class="flex items-center justify-between rounded-lg bg-surface-elevated/50 px-4 py-2"><span class="font-mono text-xs text-text-secondary">"${escape_html(truncate(entry.prompt, 50))}"</span> <div class="flex items-center gap-4"><span class="text-xs text-text-muted">${escape_html(entry.rule_name)}</span> <span${attr_class("font-mono text-xs font-semibold", void 0, {
            "text-accent": entry.similarity >= 80,
            "text-warning": entry.similarity < 80 && entry.similarity >= 60,
            "text-error": entry.similarity < 60
          })}>${escape_html(entry.similarity.toFixed(1))}%</span></div></div>`);
        }
        $$renderer2.push(`<!--]--></div></div>`);
      } else {
        $$renderer2.push("<!--[-1-->");
      }
      $$renderer2.push(`<!--]--></div>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--> <footer class="flex items-center justify-between border-t border-border/50 pt-6 pb-8"><p class="text-xs text-text-muted">RuleShield Hermes -- LLM Cost Optimizer</p> <p class="font-mono text-xs text-text-muted">`);
    if (data.loadedAt) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`Last update: ${escape_html(new Date(data.loadedAt).toLocaleTimeString())}`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--></p></footer></main>`);
  });
}
export {
  _page as default
};
