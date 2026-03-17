# RuleShield PR Agent -- Product Requirements Document

**PMF Score: 9.1/10** | Self-improving GitHub PR Review Bot

---

## 1. Executive Summary

RuleShield PR Agent ist ein self-improving GitHub PR Review Bot. Er reviewed Pull Requests automatisch per LLM und nutzt RuleShield als Cost-Optimization-Proxy. Von PR zu PR lernt er Patterns, cached wiederkehrende Reviews, und routet einfache PRs an guenstige Modelle.

Das Besondere: Der Bot macht RuleShield's Wert oeffentlich sichtbar. Jeder PR-Kommentar zeigt: "Review cost: $0.12 (saved: $0.38, 76%)". Jeder Developer der den PR sieht, sieht die Savings.

---

## 2. Problem Statement

### Pain Points

| Pain Point | Impact | Betroffene |
|---|---|---|
| PR Reviews dauern zu lang | 50% der PRs warten >24h auf Review | Alle Devs |
| LLM-basierte Reviews sind teuer | $0.30-$1.00 pro PR bei CodeRabbit | Teams mit >50 PRs/Monat |
| Review-Qualitaet inkonsistent | Bot-Reviews oft generisch oder noisy | Maintainer |
| Keine Lernkurve | Jeder PR wird von Null reviewed | Engineering Leads |
| Einfache PRs bekommen gleichen Aufwand | docs-only PR bekommt Deep Code Review | Alle |

### Kosten-Realitaet

| Szenario | PRs/Monat | Ohne RuleShield | Mit RuleShield (nach 3 Mo) |
|---|---|---|---|
| Solo OSS Maintainer | 20 | $10 | $2 |
| Small Team (10 devs) | 100 | $50 | $10 |
| Mid Team (50 devs) | 500 | $250 | $40 |
| Large Team (200 devs) | 2000 | $1000 | $120 |

### Competitive Landscape

| Tool | Preis | Self-Improving | Cost Transparency | Cost Optimization | OSS |
|---|---|---|---|---|---|
| CodeRabbit | $19-29/User/Mo | Nein | Nein | Nein | Nein |
| Copilot Code Review | $19/User/Mo | Nein | Nein | Nein | Nein |
| PR-Agent (Qodo) | Free/Enterprise | Nein | Nein | Nein | Ja |
| **RuleShield PR Agent** | **Free / $19/Mo** | **Ja** | **Ja (Badge)** | **Ja (4 Layers)** | **Ja** |

---

## 3. Target Market

### TAM / SAM / SOM

| Segment | Groesse |
|---|---|
| TAM | $2B+ (alle LLM-Code-Review-Tools) |
| SAM | $200M (Teams mit >50 PRs/Monat) |
| SOM Year 1 | 5,000 Repos, 500 Pro Subs |
| SOM Year 2 | 20,000 Repos, $500k ARR |

### Primary Persona: "Maintainer Max"
- OSS Maintainer, 10-50 PRs/Woche
- Will Bot-Hilfe, findet CodeRabbit zu teuer fuer OSS
- Probiert GitHub Action in 5 Minuten aus

### Secondary Persona: "Team Lead Tina"
- Engineering Lead, 200+ PRs/Monat
- Zahlt fuer CodeRabbit, will Kosten senken
- Braucht Analytics und Konfigurierbarkeit

---

## 4. Solution

### Core Value Proposition
> "The only PR review bot that gets better AND cheaper with every review."

### Self-Improvement Loop

```
PR #1:   All 7 tasks -> LLM           Cost: $0.50
PR #10:  Classification cached         Cost: $0.35
PR #50:  Docs-only fully rule-based    Cost: $0.05
PR #200: 80% rule/cache-based          Cost: $0.05 avg
```

### Review Tasks per PR

1. PR Classification (docs/bugfix/feature/refactor/dependency)
2. Summary (what changed, why)
3. Security scan (secrets, vulnerabilities, unsafe patterns)
4. Style check (conventions, naming, formatting)
5. Test coverage assessment
6. Label suggestions
7. Complexity/risk assessment

---

## 5. Feature Spec

### MVP (Must Have)

| Feature | SP |
|---|---|
| GitHub Action Setup (`uses: ruleshield/pr-agent@v1`) | 5 |
| PR Classification (>85% accuracy) | 8 |
| PR Summary (3-5 sentences from diff) | 3 |
| Security Scan (secrets, .env, unsafe patterns) | 5 |
| Label Suggestions (1-3 labels) | 3 |
| Structured Review Comment | 5 |
| Cost Badge ("Review cost: $X.XX, saved: $Y.YY, Z%") | 2 |
| RuleShield Integration (all calls through proxy) | 3 |
| PR Rule Pack (15+ rules) | 5 |

### Should Have

| Feature | SP |
|---|---|
| Style Check | 5 |
| Test Coverage Assessment | 5 |
| Complexity/Risk Score (1-10) | 3 |
| Maintainer Feedback Loop | 8 |
| Learning Curve Dashboard | 8 |
| Configurable tasks per repo | 3 |

### Could Have

| Feature | SP |
|---|---|
| Inline code comments | 8 |
| Auto-merge for low-risk PRs | 5 |
| Cross-repo learning | 13 |
| Custom review rules (YAML) | 5 |
| Slack notification | 3 |

---

## 6. Technical Architecture

```
GitHub PR Event (webhook)
    |
    v
GitHub Action Runner
    |
    +-- Parse diff (files, additions, deletions)
    +-- Extract metadata (title, description, author)
    |
    v
PR Agent (Python)
    |
    +-- Classify PR type
    |
    +-- For each review task:
    |     |
    |     v
    |   RuleShield Proxy (:8337)
    |     +-- Cache: same diff pattern? -> cached review
    |     +-- Rules: docs-only? -> skip deep review
    |     +-- Router: simple -> Haiku, complex -> Sonnet
    |     +-- Passthrough: forward to LLM
    |
    +-- Assemble structured comment
    +-- Calculate cost + savings
    +-- Post via GitHub API
    +-- Log for learning
```

### Feedback Loop

```
1. Bot posts comment with tag: <!-- ruleshield:pr-123:task-security -->
2. Maintainer EDITS -> record correction -> adjust confidence
3. Maintainer DELETES -> record rejection -> lower confidence
4. Maintainer APPROVES after bot -> implicit accept -> boost confidence
5. Maintainer requests changes despite "looks good" -> learn miss
```

---

## 7. Business Model

### Pricing

| Tier | Preis | Limits |
|---|---|---|
| Free | $0 | Public repos, 100 PRs/Monat |
| Pro | $19/Monat | Private repos, unlimited, analytics |
| Team | $49/Monat | Cross-repo learning, custom rules |
| Enterprise | $99/Monat | SSO, SLA, org analytics |

### Unit Economics

| Metrik | Wert |
|---|---|
| Cost per PR (Month 1) | $0.30 |
| Cost per PR (Month 6) | $0.05 |
| Gross Margin (Month 1) | 68% |
| Gross Margin (Month 6) | 95% |
| CAC | $5 (viral) |
| LTV | $228 (12 Mo x $19) |
| LTV/CAC | 45:1 |

---

## 8. Go-to-Market

### Phase 1: Dogfooding (Week 1)
- Activate on ruleshield-hermes repo
- Screenshot first reviews for marketing

### Phase 2: OSS Launch (Week 2-4)
- GitHub Marketplace
- Product Hunt
- "Show HN: Self-improving PR review bot"
- Tweet Thread with Learning Curve Graph

### Phase 3: Growth (Month 2-6)
- Target top 100 OSS repos with >50 PRs/month
- Blog: "How [Project X] saved $Y on code reviews"
- Conference talks

### Growth Loops

```
Loop 1: Cost Badge -> Contributor sees it -> "What's RuleShield?" -> Install
Loop 2: Learning Curve Dashboard -> Tweet/Blog -> new repos -> more data
Loop 3: Cross-Repo Learning -> Network Effect
Loop 4: Maintainer Word-of-Mouth -> "Our bot costs 90% less now"
```

---

## 9. Success Metrics

### North Star: PRs reviewed per month

### OKRs Month 1-6

O1: Prove Self-Improvement
- KR1: Cost per PR drops 50% within first 100 PRs
- KR2: Rule Cache Hit Rate >40% after 200 PRs

O2: Adoption
- KR1: 500 repos installed
- KR2: 50 Pro subscriptions
- KR3: 10,000 PRs reviewed

O3: Virality
- KR1: 20% of installs via Cost Badge clicks
- KR2: 5 external blog posts

---

## 10. Risks and Mitigations

| Risiko | Mitigation |
|---|---|
| Noisy reviews | Shadow Mode first, gradual activation |
| GitHub API changes | GitLab backup, self-hosted option |
| CodeRabbit price drop | Self-improvement is the feature, not price |
| False positive security | High confidence thresholds |
| Code privacy concerns | Self-hosted option, local models |

---

## 11. Timeline

| Woche | Milestone |
|---|---|
| W1 | MVP: Action + Classification + Summary + Badge |
| W2 | Security + Labels + RuleShield Integration |
| W3 | Dogfooding, first external testers |
| W4 | GitHub Marketplace Launch |
| W6 | Feedback Loop |
| W8 | Learning Curve Dashboard |
| W12 | Pro Tier, 500 repos |
| W24 | Cross-Repo Learning, Enterprise |

---

## 12. Relationship to RuleShield Core

Der PR Agent ist der erste "Flagship Use Case" fuer RuleShield:

| Rolle | Wert |
|---|---|
| Dogfooding | Beweist RuleShield in Production |
| Marketing | Cost Badge = oeffentliche Werbung |
| Data | Generiert Training Data fuer Rule Engine |
| Community | Zieht Developers an die dann RuleShield fuer eigene Projekte nutzen |
| Revenue | Eigenstaendiges Produkt mit Subscription |

Der PR Agent ist sowohl ein Produkt ALS AUCH eine Marketing-Maschine fuer RuleShield.
