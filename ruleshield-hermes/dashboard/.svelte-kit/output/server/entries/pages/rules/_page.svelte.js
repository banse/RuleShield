import { e as escape_html, a as ensure_array_like, c as attr_class, d as attr_style, s as stringify, b as attr, f as derived } from "../../../chunks/index2.js";
import "@sveltejs/kit/internal";
import "../../../chunks/exports.js";
import "../../../chunks/utils.js";
import "@sveltejs/kit/internal/server";
import "../../../chunks/root.js";
import "../../../chunks/state.svelte.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { data } = $$props;
    let rules = [];
    let total = 0;
    let active = 0;
    let sortKey = "hits";
    let sortedRules = derived(() => {
      const sorted = [...rules];
      sorted.sort((a, b) => {
        const av = a[sortKey];
        const bv = b[sortKey];
        if (typeof av === "number" && typeof bv === "number") {
          return bv - av;
        }
        if (typeof av === "string" && typeof bv === "string") {
          return bv.localeCompare(av);
        }
        if (typeof av === "boolean" && typeof bv === "boolean") {
          return av === bv ? 0 : av ? -1 : 1;
        }
        return 0;
      });
      return sorted;
    });
    let totalHits = derived(() => rules.reduce((sum, r) => sum + r.hits, 0));
    let maxHits = derived(() => Math.max(...rules.map((r) => r.hits), 1));
    function sortIndicator(key) {
      if (sortKey !== key) return "";
      return " ↓";
    }
    function confidenceColor(confidence) {
      if (confidence >= 0.9) return "bg-accent";
      if (confidence >= 0.75) return "bg-warning";
      return "bg-error";
    }
    function confidenceTextColor(confidence) {
      if (confidence >= 0.9) return "text-accent";
      if (confidence >= 0.75) return "text-warning";
      return "text-error";
    }
    function levelBadgeClasses(level) {
      switch (level) {
        case "CONFIRMED":
          return "bg-accent/15 text-accent border-accent/30";
        case "LIKELY":
          return "bg-warning/15 text-warning border-warning/30";
        case "POSSIBLE":
          return "bg-error/15 text-error border-error/30";
        default:
          return "bg-text-muted/15 text-text-muted border-text-muted/30";
      }
    }
    {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--> <header class="border-b border-border px-8 py-5"><div class="mx-auto flex max-w-[1440px] items-center justify-between"><div class="flex items-center gap-3"><a href="/" class="flex items-center gap-2 rounded-lg px-2 py-1 text-text-muted transition-colors hover:bg-surface-elevated hover:text-text-secondary"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"></path></svg> <span class="text-xs font-medium">Dashboard</span></a> <span class="text-text-muted/40">|</span> <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/20"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-primary"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg></div> <h1 class="text-lg font-semibold tracking-tight text-text-primary">Rule Explorer</h1></div> <div class="flex items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5"><span class="font-mono text-xs text-text-secondary">${escape_html(rules.length)} rules loaded</span></div></div></header> <main class="mx-auto max-w-[1440px] space-y-6 px-8 py-8"><div class="grid grid-cols-3 gap-4"><div class="group rounded-xl border border-border bg-surface p-6 transition-all duration-200 hover:border-primary/40 hover:shadow-[0_0_20px_rgba(108,92,231,0.08)]"><p class="mb-1 text-xs font-medium uppercase tracking-wider text-text-muted">Total Rules</p> <p class="font-mono text-3xl font-bold text-text-primary">${escape_html(total)}</p></div> <div class="group rounded-xl border border-border bg-surface p-6 transition-all duration-200 hover:border-accent/40 hover:shadow-[0_0_20px_rgba(0,212,170,0.08)]"><p class="mb-1 text-xs font-medium uppercase tracking-wider text-text-muted">Active Rules</p> <div class="flex items-baseline gap-2"><p class="font-mono text-3xl font-bold text-accent">${escape_html(active)}</p> <span class="font-mono text-sm text-accent/70">/ ${escape_html(total)}</span></div></div> <div class="group rounded-xl border border-border bg-surface p-6 transition-all duration-200 hover:border-primary/40 hover:shadow-[0_0_20px_rgba(108,92,231,0.08)]"><p class="mb-1 text-xs font-medium uppercase tracking-wider text-text-muted">Total Hits</p> <p class="font-mono text-3xl font-bold text-primary">${escape_html(totalHits())}</p></div></div> <div class="rounded-xl border border-border bg-surface"><div class="border-b border-border px-6 py-4"><div class="flex items-center justify-between"><h2 class="text-sm font-semibold uppercase tracking-wider text-text-muted">All Rules</h2> <span class="text-xs text-text-muted">Click column headers to sort</span></div></div> <div class="overflow-x-auto"><table class="w-full"><thead><tr class="border-b border-border/50 text-left text-xs font-medium uppercase tracking-wider text-text-muted"><th class="cursor-pointer px-6 py-3 transition-colors hover:text-text-secondary">Name${escape_html(sortIndicator("name"))}</th><th class="cursor-pointer px-4 py-3 transition-colors hover:text-text-secondary">ID${escape_html(sortIndicator("id"))}</th><th class="w-24 cursor-pointer px-4 py-3 text-right transition-colors hover:text-text-secondary">Patterns${escape_html(sortIndicator("pattern_count"))}</th><th class="w-40 cursor-pointer px-4 py-3 text-right transition-colors hover:text-text-secondary">Hits${escape_html(sortIndicator("hits"))}</th><th class="w-44 cursor-pointer px-4 py-3 text-right transition-colors hover:text-text-secondary">Confidence${escape_html(sortIndicator("confidence"))}</th><th class="w-28 cursor-pointer px-4 py-3 text-center transition-colors hover:text-text-secondary">Level${escape_html(sortIndicator("confidence_level"))}</th><th class="w-24 px-4 py-3 text-center">Status</th></tr></thead><tbody>`);
    if (sortedRules().length === 0) {
      $$renderer2.push("<!--[0-->");
      $$renderer2.push(`<tr><td colspan="7" class="px-6 py-16 text-center text-sm text-text-muted">No rules loaded. Rules will appear here once the proxy is running.</td></tr>`);
    } else {
      $$renderer2.push("<!--[-1-->");
    }
    $$renderer2.push(`<!--]--><!--[-->`);
    const each_array = ensure_array_like(sortedRules());
    for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
      let rule = each_array[$$index];
      $$renderer2.push(`<tr${attr_class("group border-b border-border/30 transition-all duration-200 hover:bg-surface-elevated/50 hover:shadow-[inset_0_0_40px_rgba(108,92,231,0.03)]", void 0, { "opacity-50": !rule.enabled })}><td class="px-6 py-4 text-sm font-medium text-text-primary">${escape_html(rule.name)}</td><td class="px-4 py-4"><span class="font-mono text-xs text-text-muted">${escape_html(rule.id)}</span></td><td class="px-4 py-4 text-right"><span class="inline-flex items-center justify-center rounded-md bg-surface-elevated px-2 py-0.5 font-mono text-xs text-text-secondary">${escape_html(rule.pattern_count)}</span></td><td class="px-4 py-4 text-right"><div class="flex items-center justify-end gap-3"><div class="h-1.5 w-20 overflow-hidden rounded-full bg-surface-elevated"><div class="h-full rounded-full bg-primary transition-all duration-500"${attr_style(`width: ${stringify(rule.hits / maxHits() * 100)}%`)}></div></div> <span class="min-w-[2rem] font-mono text-sm font-semibold text-primary">${escape_html(rule.hits)}</span></div></td><td class="px-4 py-4 text-right"><div class="flex items-center justify-end gap-2"><div class="h-1.5 w-16 overflow-hidden rounded-full bg-surface-elevated"><div${attr_class(`h-full rounded-full transition-all duration-500 ${stringify(confidenceColor(rule.confidence))}`)}${attr_style(`width: ${stringify(rule.confidence * 100)}%`)}></div></div> <span${attr_class(`min-w-[3rem] font-mono text-xs ${stringify(confidenceTextColor(rule.confidence))}`)}>${escape_html((rule.confidence * 100).toFixed(0))}%</span></div></td><td class="px-4 py-4 text-center"><span${attr_class(`inline-flex items-center rounded-md border px-2 py-0.5 font-mono text-[10px] font-semibold uppercase ${stringify(levelBadgeClasses(rule.confidence_level))}`)}>${escape_html(rule.confidence_level)}</span></td><td class="px-4 py-4 text-center"><button${attr_class(`relative inline-flex h-6 w-11 cursor-pointer items-center rounded-full border transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-surface ${stringify(rule.enabled ? "bg-accent border-accent" : "bg-surface-elevated border-border")}`)}${attr("aria-label", `Toggle rule ${stringify(rule.name)}`)}${attr("aria-pressed", rule.enabled)}><span${attr_class("inline-block h-4 w-4 rounded-full transition-all duration-200", void 0, {
        "translate-x-5": rule.enabled,
        "translate-x-1": !rule.enabled,
        "bg-accent": rule.enabled,
        "shadow-[0_0_8px_rgba(0,212,170,0.5)]": rule.enabled,
        "bg-text-muted": !rule.enabled
      })}></span></button></td></tr>`);
    }
    $$renderer2.push(`<!--]--></tbody></table></div></div> <footer class="flex items-center justify-between border-t border-border/50 pb-8 pt-6"><p class="text-xs text-text-muted">RuleShield Hermes -- Rule Explorer</p> <p class="font-mono text-xs text-text-muted">`);
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
