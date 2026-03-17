# RuleShield x Hermes Agent -- Hackathon Sprint Plan (REVISED)

**Hackathon**: Hermes Agent Hackathon by NousResearch
**Deadline**: Sonntag 16. Maerz 2026, End of Day
**Preise**: 1st $7,500 | 2nd $2,000 | 3rd $500
**Bewertung**: Creativity, Usefulness, Presentation
**Einreichung**: Tweet mit Video-Demo + Writeup @NousResearch, Link in Discord

> Dieses Dokument ergaenzt den Hauptplan (RuleShield_Architecture.md).
> REVISED: Angepasst an tatsaechlichen Fortschritt -- Phase 1+2 des
> Hauptplans sind bereits abgeschlossen. Wir koennen deutlich weiter gehen.

---

## Status: Was bereits steht (Samstag 15. Maerz, Abend)

### Erledigt -- Freitag (urspruenglich fuer 2 Tage geplant, in ~4h geschafft)

- [x] FastAPI Proxy Server (OpenAI-kompatibel, Streaming)
- [x] 2-Layer Cache (Hash + Semantic Similarity, sentence-transformers)
- [x] Rule Engine mit 8 Default-Rules + JSON-basiertes Pattern Matching
- [x] Auto-Rule-Extraction (Cluster-basiert)
- [x] Rich Terminal Dashboard (Live-Modus, farbcodiert)
- [x] CLI: init, start, stop, stats, rules, feedback
- [x] Hermes Skills: cost_report, show_rules
- [x] Hermes Config Integration (model.base_url patching)
- [x] Config Management (YAML + Env Vars)
- [x] README, LICENSE, HACKATHON_SUBMISSION.md
- [x] pyproject.toml mit pip install -e .
- [x] 4 Demo-Szenarien (Morning Workflow, Code Review, Research, Cron)
- [x] Live-getestet gegen Nous Inference API: 47-82% Savings bestaetigt
- [x] Kosten-Tracking und Savings-Berechnung funktioniert
- [x] 5 Commits, saubere Git-History

### Erledigt -- Samstag (Advanced Features)

- [x] Smart Model Router mit Complexity Classifier (routes zu cheap/mid/premium)
- [x] Feedback Loop mit Bandit-Style Confidence Updates (accept/reject)
- [x] Hermes Bridge (optionaler lokaler Hermes Agent mit guenstigem Modell)
- [x] Prompt Trimming (Split known/unknown Parts)
- [x] RL Training Interface Stubs (GRPO/Atropos, DSPy/GEPA)
- [x] Cron Replacement Concept + Test-Szenario

### In Arbeit (parallele Agents bauen gerade)

- [ ] Hermes Skill (SKILL.md + Scripts in ~/.hermes/skills/)
- [ ] MCP Server (JSON-RPC stdio, 4 Tools: get_stats, list_rules, add_rule, get_savings)
- [ ] Weighted Scoring (SAP-inspirierte Keyword + Regex Gewichtung)
- [ ] Confidence Levels (CONFIRMED/LIKELY/POSSIBLE)
- [ ] Per-Component Feedback Tracking
- [ ] Analytics fuer underperformende Rules

### Mapping zum Hauptplan

```
Hauptplan Phase 1: Foundation (Wochen 1-3)     -> DONE in 4h (Freitag)
Hauptplan Phase 2: Rule Engine (Wochen 4-6)    -> DONE (Basis) in 4h (Freitag)
Hauptplan Phase 3: Smart Router (Wochen 7-8)   -> DONE (Samstag)
Hauptplan Phase 4: Dashboard (Wochen 9-10)     -> Terminal-Version DONE
Hauptplan Phase 5: Marketplace (Wochen 11-12)  -> Teilweise machbar
```

---

## Revidierter Sprint-Plan: Samstag + Sonntag

Da Phase 1+2 bereits stehen, koennen wir jetzt in die Features von
Phase 3-4 des Hauptplans vordringen UND den Hackathon-Prototyp
gleichzeitig aufwerten.

### Samstag 15. Maerz -- Advanced Features (DONE)

**Morgen: Smart Model Router (Hauptplan Phase 3)** -- ERLEDIGT
- [x] Request Complexity Classifier (Prompt-Laenge, Keywords, Fragetyp)
- [x] Multi-Model Router (cheap/mid/premium, konfigurierbar)
- [x] Routing-Metriken ("Routed to cheap model" Resolution-Type)

**Nachmittag: Erweiterte Features** -- ERLEDIGT
- [x] Feedback Loop mit Bandit-Style Confidence Updates
- [x] Hermes Bridge (lokaler Agent mit guenstigem Modell)
- [x] Prompt Trimming (known/unknown Split)
- [x] RL Training Interface Stubs (GRPO/Atropos, DSPy/GEPA)
- [x] Cron Replacement Concept + Test-Szenario

**Abend: Parallel-Agents** -- IN ARBEIT
- [ ] MCP Server (JSON-RPC stdio, 4 Tools)
- [ ] Hermes Skill Packaging (SKILL.md + Scripts)
- [ ] SAP-inspiriertes Weighted Scoring
- [ ] Confidence Levels (CONFIRMED/LIKELY/POSSIBLE)

### Sonntag 16. Maerz -- Final Integration + Submission

**Morgen (4h): Integration + Testing**
- [ ] MCP Server + Skill finalisieren und testen
- [ ] Weighted Scoring + Confidence Levels integrieren
- [ ] Hermes als echten Agent durchlaufen lassen (nicht nur curl)
  - `hermes` starten mit RuleShield-Config
  - Echte Coding-Tasks ausfuehren
  - RuleShield beobachtet alle Calls, Router routet, Feedback greift
- [ ] End-to-End Integrationstests aller Komponenten zusammen
- [ ] README + HACKATHON_SUBMISSION.md final aktualisieren

**Nachmittag (4h): Demo-Video + Submission**
- [ ] Demo-Szenario mit ECHTEM Hermes Agent
  1. Terminal 1: `ruleshield start` (Dashboard laeuft)
  2. Terminal 2: Hermes Agent startet ueber RuleShield
  3. Echte Tasks: Cache, Rules, Router, Bridge, Feedback -- alles sichtbar
  4. MCP Server Demo: Agent fragt eigene Stats ab
  5. `ruleshield stats` am Ende -- Savings-Beweis
- [ ] Video aufnehmen (2-3 Minuten)
  - Problem: 10 Sek
  - One-command Setup: 15 Sek
  - Live Demo mit echtem Hermes: 90 Sek
  - Smart Router + Feedback in Aktion: 20 Sek
  - MCP/Skill Integration: 15 Sek
  - Vision (RL, Self-Evolution): 10 Sek
- [ ] Tweet + Writeup posten
- [ ] Discord Submission

---

## Erweiterte Feature-Liste (nach Prioritaet)

### P0: Muss fuer Hackathon (bereits DONE)

| Feature | Status |
|---------|--------|
| FastAPI Proxy mit OpenAI-kompatiblem Interface | DONE |
| 2-Layer Cache (Hash + Semantic) | DONE |
| Rule Engine mit Default-Rules | DONE |
| Auto-Rule-Extraction | DONE |
| Rich Terminal Dashboard | DONE |
| CLI (init, start, stats, rules) | DONE |
| Hermes Skills (cost_report, show_rules) | DONE |
| Hermes Config Integration | DONE |
| README + Writeup | DONE |
| Demo-Szenarien | DONE |

### P1: Starke Differenzierung (Samstag) -- ERLEDIGT

| Feature | Status | Impact |
|---------|--------|--------|
| Smart Model Router | DONE | +15-20% Savings |
| Complexity Classifier | DONE | Ermoeglicht Router |
| Feedback Loop (Bandit-Style) | DONE | Self-Improvement |
| Hermes Bridge | DONE | Lokaler Agent-Proxy |
| Prompt Trimming | DONE | Token-Einsparung |
| RL/GEPA Stubs | DONE | Zukunfts-Narrative |
| Cron Replacement Concept | DONE | Unique Feature |

### P1.5: In Arbeit (Samstag Abend, parallele Agents)

| Feature | Status | Impact |
|---------|--------|--------|
| MCP Server (4 Tools) | IN PROGRESS | Deep Hermes Integration |
| Hermes Skill Packaging | IN PROGRESS | Skill-System Anbindung |
| SAP-inspiriertes Weighted Scoring | IN PROGRESS | Enterprise-Grade Rules |
| Confidence Levels | IN PROGRESS | Praezisere Entscheidungen |

### P2: Sonntag morgen

| Feature | Status | Impact |
|---------|--------|--------|
| Echte Hermes Integration Demo | TODO | Authentische Demo |
| End-to-End Integrationstest | TODO | Stabilitaet |
| Video + Submission | TODO | Hackathon-Pflicht |

### P3: Post-Hackathon (Hauptplan Phase 4-5)

| Feature | Status | Impact |
|---------|--------|--------|
| SvelteKit Web Dashboard | TODO | Visueller |
| Rule Marketplace | TODO | Community |
| Multi-Tenancy | TODO | Enterprise |
| Billing (Stripe) | TODO | Revenue |
| PostgreSQL Migration | TODO | Scale |

---

## Aktuelle Architektur (4-Layer + Integrations)

```
Request -> Cache -> Rules -> Hermes Bridge -> Smart Router -> Upstream LLM
           $0       $0      $0.001 (opt.)    auto-routing    premium
                      |
                 Feedback Loop (accept/reject -> confidence)
                      |
                 RL/GEPA Stubs (future: self-evolution)

Plus: Hermes Skill + MCP Server fuer deep Agent-Integration
```

### Layer-Details

```
Hermes Agent / MCP Client
    |
    v
RuleShield Proxy (localhost:8337)
    |
    +-- Layer 1: Semantic Cache
    |     Hash + Embedding-basiert, $0
    |
    +-- Layer 2: Rule Engine (SAP-inspiriert)
    |     Weighted Scoring, Confidence Levels, $0
    |
    +-- Layer 3: Hermes Bridge (optional)
    |     Lokaler Agent mit guenstigem Modell, ~$0.001
    |
    +-- Layer 4: Smart Router
    |     Complexity Classifier -> cheap/mid/premium
    |
    +-- Feedback Loop (Bandit-Style Confidence Updates)
    +-- MCP Server (4 Tools: stats, rules, add_rule, savings)
    +-- Hermes Skill (SKILL.md in ~/.hermes/skills/)
    +-- RL/GEPA Stubs (GRPO/Atropos, DSPy)
```

---

## Revidiertes Kosten-Modell (mit Router)

| Resolution | Anteil | Kosten/Request | Savings |
|------------|--------|----------------|---------|
| Cache Hit | 15-20% | $0.000 | 100% |
| Rule Hit | 30-40% | $0.000 | 100% |
| Routed (guenstig) | 15-20% | $0.001 | 85% |
| LLM (Premium) | 20-30% | $0.010 | 0% |

**Erwartete Gesamtsavings: 70-85%** (vs. 47-50% ohne Router)

---

## Hackathon-Bewertung -> Erweiterte Staerken

| Kriterium | Wie wir punkten |
|---|---|
| **Creativity** | 4-Layer Intelligence + Feedback Loop + RL Stubs + MCP Server = "Agent der sich selbst optimiert und selbst evolved". Einzigartiger Ansatz. |
| **Usefulness** | Sofort einsetzbar: `pip install` + 1 Befehl. 47-82% Savings bewiesen gegen Nous API. MCP-Integration macht es nativ nutzbar. |
| **Presentation** | Live Dashboard + Smart Router + Feedback-Visualisierung + MCP Demo + Zukunftsvision (RL/GEPA Self-Evolution). |

---

## Narrative (erweitert)

> **"What if your AI agent could learn to optimize -- and eventually evolve -- itself?"**
>
> RuleShield observes Hermes Agent's LLM calls and builds a
> 4-layer intelligence: semantic cache, SAP-inspired rule engine,
> local Hermes Bridge, and smart model routing.
>
> It learns from feedback (bandit-style confidence updates),
> integrates natively via MCP Server and Hermes Skills,
> and has RL/GEPA stubs ready for future self-evolution.
>
> One command. 47-82% proven savings. The agent that optimizes itself.

---

## Beziehung zum Hauptplan (revidiert)

```
Hauptplan                              Hackathon PoC
========================================  ============================
Phase 1: Foundation (Wochen 1-3)       -> DONE (Freitag Abend)
  - Python Proxy (FastAPI)                 - DONE
  - SQLite Cache                           - DONE
  - Hermes Config Redirect                 - DONE

Phase 2: Rule Engine (Wochen 4-6)      -> DONE (Freitag Abend)
  - Pattern Extraction                     - DONE
  - Shadow Mode (Basis)                    - DONE
  - Rich Terminal Dashboard                - DONE

Phase 3: Smart Router (Wochen 7-8)     -> DONE (Samstag)
  - Complexity Classifier                  - DONE
  - Multi-Model Router                     - DONE
  - Routing-Metriken                       - DONE
  - Feedback Loop                          - DONE (Bonus)
  - Hermes Bridge                          - DONE (Bonus)

Phase 4: Dashboard (Wochen 9-10)       -> PARTIAL
  - Terminal Dashboard                     - DONE
  - MCP Server                             - IN PROGRESS
  - Wrapped Reports                        - Post-Hackathon

Phase 5: Marketplace (Wochen 11-12)    -> Post-Hackathon
  - Rule Marketplace                       - Post-Hackathon
  - Billing                                - Post-Hackathon
```

Der Hackathon-Prototyp deckt Phase 1-3 des Hauptplans vollstaendig ab
plus Teile von Phase 4 -- das sind 10 von 12 geplanten Wochen Arbeit,
umgesetzt in 2 Tagen. Zusaetzlich: Feedback Loop, Hermes Bridge,
RL Stubs, MCP Server und Prompt Trimming waren im Hauptplan gar nicht
vorgesehen.
