import { h as head, a as ensure_array_like, e as escape_html, b as attr, c as attr_class, s as stringify } from "../../../chunks/index2.js";
function _page($$renderer) {
  let hoveredCard = null;
  const sections = [
    {
      label: "Live Tools",
      items: [
        {
          title: "Dashboard",
          description: "Real-time proxy stats, requests, savings",
          href: "/",
          color: "accent"
        },
        {
          title: "Rule Explorer",
          description: "Browse, toggle, sort all 75 rules",
          href: "/rules",
          color: "primary"
        },
        {
          title: "Wrapped Report",
          description: "Monthly savings report with share feature",
          href: "/wrapped",
          color: "accent"
        }
      ]
    },
    {
      label: "Marketing",
      items: [
        {
          title: "Landing Page",
          description: "Product marketing page with 12 sections",
          href: "/landing",
          color: "primary"
        },
        {
          title: "Presentation",
          description: "10-slide hackathon deck with keyboard navigation",
          href: "/slides",
          color: "primary"
        }
      ]
    },
    {
      label: "Documentation",
      items: [
        {
          title: "Quick Start",
          description: "Installation, setup, architecture overview",
          href: "/docs",
          color: "accent"
        },
        {
          title: "Architecture",
          description: "4-layer pipeline, shadow mode, feedback loop",
          href: "/docs/architecture",
          color: "primary"
        },
        {
          title: "Hermes Guide",
          description: "Skill, MCP server, config patching",
          href: "/docs/hermes",
          color: "accent"
        },
        {
          title: "API Reference",
          description: "15 CLI commands, REST endpoints, config",
          href: "/docs/api",
          color: "primary"
        },
        {
          title: "LangChain",
          description: "Integration guide with code examples",
          href: "/docs/langchain",
          color: "accent"
        },
        {
          title: "CrewAI",
          description: "Multi-agent integration guide",
          href: "/docs/crewai",
          color: "primary"
        }
      ]
    },
    {
      label: "Project",
      items: [
        {
          title: "GitHub",
          description: "Source code, issues, and contributions",
          href: "https://github.com/banse/ruleshield-hermes",
          color: "warning",
          external: true
        },
        {
          title: "PyPI",
          description: "Python package registry listing",
          href: "https://pypi.org/project/ruleshield",
          color: "warning",
          external: true
        },
        {
          title: "Hackathon Submission",
          description: "Submission details and project overview",
          href: "https://github.com/banse/ruleshield-hermes/blob/main/HACKATHON_SUBMISSION.md",
          color: "warning",
          external: true
        }
      ]
    }
  ];
  function colorClasses(color, hovered) {
    if (color === "accent") {
      return hovered ? "border-accent/50 shadow-[0_0_24px_rgba(0,212,170,0.12)]" : "border-border";
    }
    if (color === "primary") {
      return hovered ? "border-primary/50 shadow-[0_0_24px_rgba(108,92,231,0.12)]" : "border-border";
    }
    return hovered ? "border-warning/50 shadow-[0_0_24px_rgba(255,184,77,0.12)]" : "border-border";
  }
  function dotColor(color) {
    if (color === "accent") return "bg-accent";
    if (color === "primary") return "bg-primary";
    return "bg-warning";
  }
  function textColor(color) {
    if (color === "accent") return "text-accent";
    if (color === "primary") return "text-primary";
    return "text-warning";
  }
  head("1j6ictg", $$renderer, ($$renderer2) => {
    $$renderer2.title(($$renderer3) => {
      $$renderer3.push(`<title>RuleShield Hermes - Navigation Hub</title>`);
    });
    $$renderer2.push(`<meta name="description" content="RuleShield Hermes - Open-Source LLM Cost Optimizer. Navigate all pages."/> <link rel="preconnect" href="https://fonts.googleapis.com"/> <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous"/> <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&amp;family=JetBrains+Mono:wght@400;500&amp;display=swap" rel="stylesheet"/>`);
  });
  $$renderer.push(`<div class="min-h-screen bg-[#0A0A0F] relative overflow-hidden"><div class="pointer-events-none absolute inset-0"><div class="absolute left-1/2 top-0 h-[500px] w-[800px] -translate-x-1/2 rounded-full bg-primary/[0.04] blur-[120px]"></div> <div class="absolute bottom-0 right-1/4 h-[400px] w-[500px] rounded-full bg-accent/[0.03] blur-[100px]"></div></div> <div class="relative z-10 mx-auto max-w-5xl px-6 py-16 sm:py-24"><header class="mb-16 text-center"><div class="mb-6 inline-flex items-center gap-3"><div class="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent text-lg font-bold text-white">R</div> <h1 class="text-3xl font-extrabold tracking-tight sm:text-4xl"><span class="text-text-primary">Rule</span><span class="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">Shield</span> <span class="text-text-primary">Hermes</span></h1> <span class="rounded-md border border-border bg-surface px-2 py-0.5 font-mono text-xs font-medium text-text-muted">v0.2.0</span></div> <p class="mx-auto max-w-xl text-base text-text-secondary sm:text-lg">Open-Source LLM Cost Optimizer  |  <span class="font-mono text-text-muted">30 commits, 75 rules, 80+ models</span></p></header> <!--[-->`);
  const each_array = ensure_array_like(sections);
  for (let $$index_1 = 0, $$length = each_array.length; $$index_1 < $$length; $$index_1++) {
    let section = each_array[$$index_1];
    $$renderer.push(`<div class="mb-12"><h2 class="mb-5 text-xs font-semibold uppercase tracking-[0.15em] text-text-muted">${escape_html(section.label)}</h2> <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"><!--[-->`);
    const each_array_1 = ensure_array_like(section.items);
    for (let $$index = 0, $$length2 = each_array_1.length; $$index < $$length2; $$index++) {
      let card = each_array_1[$$index];
      $$renderer.push(`<a${attr("href", card.href)}${attr("target", card.external ? "_blank" : void 0)}${attr("rel", card.external ? "noopener noreferrer" : void 0)}${attr_class(`group block rounded-xl border bg-surface p-5 transition-all duration-200 ${stringify(colorClasses(card.color, hoveredCard === card.title))}`)}><div class="mb-3 flex items-center gap-3"><div${attr_class(`h-2 w-2 rounded-full ${stringify(dotColor(card.color))} transition-shadow duration-200 ${stringify(hoveredCard === card.title ? "shadow-[0_0_8px_currentColor]" : "")}`)}></div> <h3${attr_class(`text-sm font-semibold ${stringify(textColor(card.color))}`)}>${escape_html(card.title)}</h3> `);
      if (card.external) {
        $$renderer.push("<!--[0-->");
        $$renderer.push(`<svg class="ml-auto h-3.5 w-3.5 text-text-muted opacity-0 transition-opacity group-hover:opacity-100" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14L21 3"></path></svg>`);
      } else {
        $$renderer.push("<!--[-1-->");
        $$renderer.push(`<svg class="ml-auto h-3.5 w-3.5 text-text-muted opacity-0 transition-all group-hover:translate-x-0.5 group-hover:opacity-100" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M12 5l7 7-7 7"></path></svg>`);
      }
      $$renderer.push(`<!--]--></div> <p class="text-sm leading-relaxed text-text-secondary">${escape_html(card.description)}</p></a>`);
    }
    $$renderer.push(`<!--]--></div></div>`);
  }
  $$renderer.push(`<!--]--> <footer class="mt-16 border-t border-border/50 pt-8 text-center"><p class="text-xs text-text-muted">Built for <span class="text-primary">Hermes Agent Hackathon</span> by NousResearch</p></footer></div></div>`);
}
export {
  _page as default
};
