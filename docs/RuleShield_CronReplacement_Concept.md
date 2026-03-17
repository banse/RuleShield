# RuleShield -- Cron/Task Replacement & Prompt Trimming

> Ausbaustufe: Post-Hackathon Feature

---

## Problem

Viele LLM-basierte Agenten laufen als Cron Jobs oder wiederkehrende Tasks:

- Stuendlicher Server-Health-Check
- Taeglicher Report
- Alle 15 Min Log-Analyse
- Wiederkehrende Datenbank-Checks

Diese Prompts sind oft **zu 100% identisch** bei jedem Lauf. Trotzdem wird
jedes Mal ein teurer LLM-Call gemacht.

Noch schlimmer: Komplexe Prompts enthalten oft einen **repetitiven Anteil**
(Kontext, Instruktionen) und einen **variablen Anteil** (aktuelle Daten).
Der gesamte Prompt wird ans LLM geschickt, obwohl nur der variable Teil
eine intelligente Antwort braucht.

---

## Feature 1: Rule-to-API Promotion

### Idee

Wenn RuleShield erkennt, dass ein Prompt:
- mindestens N-mal vorkam (z.B. 10x)
- zu >90% durch Cache/Rules aufgeloest wurde
- immer die gleiche oder sehr aehnliche Antwort liefert

...dann wird dieser Prompt als **API-Replacement-Kandidat** markiert.

### Workflow

```
1. RuleShield beobachtet: "check server status" kommt 50x/Tag
2. 48 von 50 Mal: Cache Hit (96%)
3. RuleShield schlaegt vor:

   "Recurring prompt detected: 'check server status'
    Frequency: 50x/day | Cache rate: 96%

    Suggestion: Replace this cron job with a direct API call:

    curl http://localhost:8337/api/rules/server_status_check

    This returns the cached response without any LLM call.
    Estimated daily savings: $2.40"

4. User aktiviert: Der Prompt wird als feste Rule mit statischer
   Antwort registriert -> 100% ohne LLM
```

### API Endpoint

```
GET /api/rules/{rule_id}/response
```

Gibt die gecachte/regelbasierte Antwort direkt zurueck.
Kein LLM-Call, keine Proxy-Pipeline -- nur Lookup.

### Automatische Detection

```python
class CronAnalyzer:
    async def analyze(self, min_occurrences=10, min_cache_rate=0.9):
        """Find prompts that are candidates for API replacement."""

        # Query request_log for recurring prompts
        # Group by prompt_hash
        # Filter: count >= min_occurrences AND cache_rate >= min_cache_rate
        # Return candidates with suggested rule configs
```

### CLI

```bash
ruleshield analyze-crons
# Output:
# +----+-----------------------------------+-------+--------+----------+
# | #  | Prompt                            | Count | Cached | Savings  |
# +----+-----------------------------------+-------+--------+----------+
# | 1  | check server status               | 50    | 96%    | $2.40/d  |
# | 2  | generate daily report             | 24    | 92%    | $1.80/d  |
# | 3  | send report to team               | 24    | 92%    | $0.60/d  |
# +----+-----------------------------------+-------+--------+----------+
#
# To promote to API: ruleshield promote-rule <prompt_hash>
```

---

## Feature 2: Prompt Trimming

### Idee

Komplexe Prompts bestehen oft aus:
- **Statischem Teil**: System-Prompt, Instruktionen, Kontext
- **Variablem Teil**: Aktuelle Daten, spezifische Frage

RuleShield kann den statischen Teil erkennen und nur den variablen
Teil ans LLM schicken.

### Beispiel

**Vorher (voller Prompt, jedes Mal):**
```
System: You are a DevOps monitoring bot for Acme Corp.
        You have access to the following servers: web-1, web-2, db-1.
        Always respond in JSON format.
        Include severity level (low/medium/high/critical).

User: Check server status, review the last hour of error logs,
      and summarize any new issues.
```

**Nachher (RuleShield trimmt):**
```
Statischer Teil (von RuleShield gehandhabt):
  - "Check server status" -> RULE (immer gleiche Antwort)
  - System-Prompt Kontext -> wird gecacht, nicht jedes Mal tokenisiert

Variabler Teil (ans LLM):
  - "review the last hour of error logs" -> LLM (Logs sind jedes Mal anders)
  - "summarize any new issues" -> LLM (haengt von den Logs ab)
```

### Technische Umsetzung

```python
class PromptTrimmer:
    def __init__(self, rule_engine, cache_manager):
        self.rule_engine = rule_engine
        self.cache_manager = cache_manager

    async def trim(self, messages: list[dict]) -> list[dict]:
        """Analyze a prompt and remove parts that can be handled by rules/cache.

        Strategy:
        1. Split the user message into sub-tasks (sentence-level)
        2. Check each sub-task against rules and cache
        3. Remove sub-tasks that have cached/rule responses
        4. Prepend a summary of the removed parts to the remaining prompt
        5. Return the trimmed messages
        """

    async def reconstruct(self, trimmed_response: str, handled_parts: dict) -> str:
        """Merge the LLM response with the rule/cache responses
        for the parts that were trimmed."""
```

### Prompt Splitting Strategien

1. **Sentence-Level**: Split an Satzgrenzen, check jeden Satz einzeln
2. **Task-Level**: Erkennung von Task-Boundaries ("check X, then Y, and Z")
3. **Section-Level**: System-Prompt vs User-Prompt trennen
4. **Diff-Level**: Bei wiederholten Prompts nur den geaenderten Teil senden

### Risiken & Mitigations

| Risiko | Mitigation |
|--------|-----------|
| Falsches Trimming veraendert die Semantik | Shadow Mode: Trimmed vs Full vergleichen |
| Sub-Tasks haengen voneinander ab | Dependency Detection: Wenn Task B von Task A abhaengt, beide ans LLM |
| System-Prompt wird fuer Kontext gebraucht | System-Prompt nie trimmen, nur User-Prompt |

---

## Feature 3: Prompt Template Optimization

### Idee

Wenn viele aehnliche Prompts mit leicht variierendem Inhalt erkannt werden,
kann RuleShield ein **Template** extrahieren und nur die Variablen ans LLM
schicken.

### Beispiel

```
Beobachtete Prompts:
  "Translate 'hello' to German"
  "Translate 'goodbye' to German"
  "Translate 'thank you' to German"

Extrahiertes Template:
  "Translate '{input}' to German"

Optimierung:
  - Template als Rule registrieren
  - Fuer bekannte inputs: Antwort aus Cache
  - Fuer neue inputs: Nur '{input}' als Variable ans LLM
  - Token-Einsparung: ~60% weniger Input-Tokens pro Call
```

---

## Beziehung zum Hauptplan

Diese Features bauen auf dem bestehenden RuleShield-Kern auf:

```
Phase 1-2 (Hackathon):     Cache + Rules + Proxy     <- DONE
Phase 3 (Post-Hackathon):  Cron Analysis + API Promotion
Phase 4:                   Prompt Trimming (Sentence-Level)
Phase 5:                   Template Optimization
```

Jedes Feature nutzt die vorhandene Infrastruktur:
- request_log fuer Pattern-Erkennung
- Rule Engine fuer promoted Rules
- Cache fuer Antwort-Lookup
- Metrics Dashboard fuer Savings-Anzeige
