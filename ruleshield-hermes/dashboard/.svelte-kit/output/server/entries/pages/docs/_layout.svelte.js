import { h as head, a as ensure_array_like, e as escape_html, b as attr, c as attr_class, s as stringify } from "../../../chunks/index2.js";
/* empty css                  */
function _layout($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { children } = $$props;
    let currentPath = "";
    const sections = [
      {
        title: "Getting Started",
        items: [
          { label: "Quick Start", href: "/docs" },
          { label: "Installation", href: "/docs#installation" }
        ]
      },
      {
        title: "Features",
        items: [
          { label: "Architecture", href: "/docs/architecture" },
          { label: "Rules", href: "/docs/architecture#rule-engine" }
        ]
      },
      {
        title: "Integration",
        items: [
          { label: "Hermes Agent", href: "/docs/hermes" },
          { label: "LangChain", href: "/docs/langchain" },
          { label: "CrewAI", href: "/docs/crewai" }
        ]
      },
      {
        title: "Reference",
        items: [
          { label: "CLI Commands", href: "/docs/api#cli" },
          { label: "API Reference", href: "/docs/api" }
        ]
      }
    ];
    function isActive(href) {
      if (href !== "/docs" && currentPath.startsWith(href.split("#")[0]) && href.split("#")[0] !== "/docs") return true;
      return false;
    }
    head("1bpnej", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>RuleShield Docs</title>`);
      });
      $$renderer3.push(`<meta name="description" content="RuleShield Hermes Documentation"/> <link rel="preconnect" href="https://fonts.googleapis.com"/> <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous"/> <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;family=JetBrains+Mono:wght@400;500&amp;display=swap" rel="stylesheet"/>`);
    });
    $$renderer2.push(`<div class="min-h-screen bg-bg flex"><aside class="w-[250px] shrink-0 border-r border-border bg-surface sticky top-0 h-screen overflow-y-auto"><div class="p-5"><a href="/home" class="flex items-center gap-2 text-text-muted hover:text-primary transition-colors text-sm mb-3"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" stroke-width="2"></rect><rect x="14" y="3" width="7" height="7" stroke-width="2"></rect><rect x="3" y="14" width="7" height="7" stroke-width="2"></rect><rect x="14" y="14" width="7" height="7" stroke-width="2"></rect></svg> Home</a> <a href="/" class="flex items-center gap-2 text-text-muted hover:text-text-primary transition-colors text-sm mb-6"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"></path></svg> Back to Dashboard</a> <a href="/docs" class="block mb-8"><h1 class="text-lg font-bold text-text-primary">RuleShield</h1> <span class="text-xs text-text-muted font-mono">Documentation</span></a> <nav class="space-y-6"><!--[-->`);
    const each_array = ensure_array_like(sections);
    for (let $$index_1 = 0, $$length = each_array.length; $$index_1 < $$length; $$index_1++) {
      let section = each_array[$$index_1];
      $$renderer2.push(`<div><h2 class="text-xs font-semibold text-text-muted uppercase tracking-wider mb-2">${escape_html(section.title)}</h2> <ul class="space-y-1"><!--[-->`);
      const each_array_1 = ensure_array_like(section.items);
      for (let $$index = 0, $$length2 = each_array_1.length; $$index < $$length2; $$index++) {
        let item = each_array_1[$$index];
        $$renderer2.push(`<li><a${attr("href", item.href)}${attr_class(`block px-3 py-1.5 rounded-md text-sm transition-colors ${stringify(isActive(item.href) ? "bg-primary/15 text-primary font-medium" : "text-text-secondary hover:text-text-primary hover:bg-surface-elevated")}`)}>${escape_html(item.label)}</a></li>`);
      }
      $$renderer2.push(`<!--]--></ul></div>`);
    }
    $$renderer2.push(`<!--]--></nav></div></aside> <main class="flex-1 min-w-0"><div class="max-w-3xl mx-auto px-8 py-12">`);
    children($$renderer2);
    $$renderer2.push(`<!----></div></main></div>`);
  });
}
export {
  _layout as default
};
