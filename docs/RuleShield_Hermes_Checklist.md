# RuleShield x Hermes -- Hackathon Checklist

**Deadline**: Sonntag 16. Maerz 2026, End of Day
**Preise**: 1st $7,500 | 2nd $2,000 | 3rd $500
**Bewertung**: Creativity, Usefulness, Presentation

---

## FREITAG 14. MAERZ -- Tag 0: Foundation (DONE)

### Alles in ~4h erledigt

- [x] Repo erstellen: `ruleshield-hermes` (public GitHub)
- [x] Python-Projekt aufsetzen (pyproject.toml, pip installierbar)
- [x] FastAPI Proxy Server: OpenAI-kompatible Endpoints
  - [x] POST /v1/chat/completions
  - [x] POST /v1/completions
  - [x] Streaming Support
- [x] Request-Forwarding an echten Provider
- [x] Exakter Hash-Cache (identische Prompts -> sofortige Antwort)
- [x] Semantic Similarity Cache (sentence-transformers, all-MiniLM-L6-v2)
- [x] SQLite Request-Log (prompt, response, tokens, cost, resolution_type)
- [x] Hermes Integration: cli-config.yaml auf localhost:8337
- [x] Rule Engine: JSON-basiertes Pattern Matching
- [x] 8 vorgefertigte Rules fuer Hermes-typische Patterns
- [x] Auto-Rule-Extraction: haeufigste Request-Cluster erkennen
- [x] Rich Terminal Dashboard (Live-Modus, farbcodiert)
- [x] CLI: init, start, stop, stats, rules
- [x] Hermes Skills: cost_report, show_rules
- [x] Hermes Config Integration (model.base_url patching)
- [x] README, LICENSE, HACKATHON_SUBMISSION.md
- [x] 4 Demo-Szenarien gegen Nous API: 47-82% Savings bestaetigt

---

## SAMSTAG 15. MAERZ -- Tag 1: Advanced Features (DONE)

### Morgen + Nachmittag: Alle erledigt

- [x] Smart Model Router mit Complexity Classifier
- [x] Multi-Model Routing (cheap/mid/premium)
- [x] Feedback Loop mit Bandit-Style Confidence Updates
- [x] CLI: feedback Command
- [x] Hermes Bridge (lokaler Agent mit guenstigem Modell)
- [x] Prompt Trimming (known/unknown Split)
- [x] RL Training Interface Stubs (GRPO/Atropos, DSPy/GEPA)
- [x] Cron Replacement Concept + Test-Szenario

### Abend: Parallele Agents (IN PROGRESS)

- [ ] MCP Server (JSON-RPC stdio, 4 Tools)
  - [ ] get_stats Tool
  - [ ] list_rules Tool
  - [ ] add_rule Tool
  - [ ] get_savings Tool
- [ ] Hermes Skill Packaging (SKILL.md + Scripts in ~/.hermes/skills/)
- [ ] SAP-inspiriertes Weighted Scoring (Keyword + Regex Gewichtung)
- [ ] Confidence Levels (CONFIRMED/LIKELY/POSSIBLE)
- [ ] Per-Component Feedback Tracking
- [ ] Analytics fuer underperformende Rules

---

## SONNTAG 16. MAERZ -- Tag 2: Integration + Ship

### Morgen: Final Integration + Testing (4h)

- [ ] MCP Server + Skill finalisieren
- [ ] MCP Server testen: alle 4 Tools gegen laufenden Proxy
- [ ] Hermes Skill testen: SKILL.md korrekt, Scripts ausfuehrbar
- [ ] Weighted Scoring + Confidence Levels integrieren
- [ ] End-to-End Test: Hermes Agent (echt, nicht curl) ueber RuleShield
  - [ ] Alle 4 Layer greifen (Cache, Rules, Bridge, Router)
  - [ ] Feedback Loop funktioniert im Live-Betrieb
  - [ ] MCP Tools liefern korrekte Daten
- [ ] README + HACKATHON_SUBMISSION.md final aktualisieren
- [ ] **CHECKPOINT**: Alles funktioniert End-to-End

### Nachmittag: Demo-Video + Submission (4h)

- [ ] Demo-Szenario mit ECHTEM Hermes Agent vorbereiten:
  - [ ] Terminal 1: `ruleshield start` (Dashboard)
  - [ ] Terminal 2: Hermes Agent laeuft ueber RuleShield
  - [ ] Echte Tasks zeigen alle 4 Layer in Aktion
  - [ ] MCP Integration: Agent fragt eigene Stats
  - [ ] `ruleshield stats` am Ende -- Savings-Beweis
- [ ] Video aufnehmen (2-3 Minuten):
  - [ ] Intro: Problem (10 Sek)
  - [ ] Setup: 1 Befehl (15 Sek)
  - [ ] Live Demo mit echtem Hermes (90 Sek)
  - [ ] Smart Router + Feedback (20 Sek)
  - [ ] MCP/Skill Integration (15 Sek)
  - [ ] Vision: RL Self-Evolution (10 Sek)
- [ ] GitHub Repo final check:
  - [ ] Code ist sauber
  - [ ] README ist vollstaendig
  - [ ] Keine API Keys / Secrets commited

### Submission (letzte Stunde)

- [ ] Tweet posten:
  - [ ] Video anhaengen
  - [ ] @NousResearch taggen
  - [ ] Writeup als Thread oder in Tweet
  - [ ] GitHub Link
  - [ ] Hashtags: #HermesAgent #NousResearch
- [ ] Tweet-Link in NousResearch Discord Submissions Channel posten
- [ ] **DONE -- EINGEREICHT!**

---

## Kritische Erfolgsfaktoren

### Must-Haves (ohne diese nicht einreichen)

- [x] Funktionierender Proxy der Hermes LLM-Calls abfaengt
- [x] Messbarer Savings-Nachweis (47-82% bestaetigt)
- [x] Terminal Dashboard mit Echtzeit-Anzeige
- [x] 1-Command Setup (`ruleshield init --hermes`)
- [x] Smart Model Router (cheap/mid/premium)
- [x] Feedback Loop (accept/reject -> confidence)
- [ ] Video Demo (2-3 Min) -- Sonntag
- [ ] Writeup finalisiert -- Sonntag
- [ ] Echte Hermes Agent Demo (nicht nur curl) -- Sonntag

### Erreicht (waren Nice-to-Haves, jetzt DONE)

- [x] Hermes Skills (cost_report, show_rules)
- [x] Auto-Rule-Extraction (Cluster-basiert)
- [x] Smart Model Router mit Complexity Classifier
- [x] Feedback Loop mit Bandit-Style Updates
- [x] Hermes Bridge (lokaler Agent)
- [x] Prompt Trimming
- [x] RL/GEPA Stubs

### Noch offen (Samstag Abend / Sonntag)

- [ ] MCP Server (4 Tools) testen und integrieren
- [ ] Hermes Skill Packaging finalisieren
- [ ] SAP-inspiriertes Weighted Scoring integrieren
- [ ] End-to-End Integrationstest aller Komponenten
- [ ] Video aufnehmen und posten

### Nicht anfassen (Zeitfallen!)

- ~~Web Dashboard~~ (Terminal reicht fuer Hackathon)
- ~~Multi-User Support~~ (Single-User PoC)
- ~~PostgreSQL~~ (SQLite reicht)
- ~~Docker~~ (pip install reicht)
- ~~Tests~~ (manuelles Testen reicht fuer Hackathon)
- ~~CI/CD~~ (nicht noetig)

---

## Winning-Narrative

```
"What if your AI agent could learn to optimize -- and eventually
 evolve -- itself?

 RuleShield watches your Hermes Agent, learns its patterns through
 4 layers of intelligence, routes simple tasks to cheap models,
 and improves its own rules through feedback.

 47-82% proven savings. One command. The agent that optimizes itself."
```

---

## Notfall-Plan

| Problem | Loesung |
|---------|---------|
| Semantic Cache zu langsam | Nur exakten Hash-Cache nutzen, Similarity weglassen |
| sentence-transformers zu gross | Kleineres Modell (all-MiniLM-L6-v2 ist nur 80MB) oder nur Hash |
| Hermes Config laesst sich nicht umbiegen | Environment Variable OPENAI_BASE_URL setzen |
| Rules greifen nicht gut | Mehr vorgefertigte Rules, weniger Auto-Extraction |
| Video wird zu lang | Fokus auf Setup + Savings-Zahlen, Rest kuerzen |
| Kein messbarer Saving | Cache aggressiver einstellen, mehr repetitive Tasks im Demo |
