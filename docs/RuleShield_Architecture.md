# RuleShield -- Architecture & Implementation Plan

---

## 1. Tech Stack

| Layer | Technologie | Begruendung |
|-------|------------|------------|
| **SDK/Proxy** | TypeScript / Node.js | Drop-in Replacement fuer OpenAI SDK, maximale Kompatibilitaet |
| **Rule Mining / ML** | Python (scikit-learn, pandas) | Bestes Oekosystem fuer Decision Trees & Pattern Extraction |
| **Datenbank** | PostgreSQL | Rules, Kunden, Metriken, Audit-Logs |
| **Cache** | Redis + pgvector | Semantic Cache (Embedding-Similarity) + Hot Rules |
| **Dashboard** | SvelteKit + Tailwind CSS | Echtzeit-Savings, Team-Leaderboards, Rule Explorer |
| **Auth** | Supabase Auth | Schnell integriert, API-Key-Management |
| **Queue / Workers** | BullMQ (Redis-backed) | Async Rule Mining, Report-Generierung |
| **Deployment** | Docker + Fly.io / Railway | Low-Latency Proxy, global edge |
| **Monitoring** | OpenTelemetry + Grafana | Latenz, Cache Hit Rates, Savings-Tracking |

---

## 2. System Architecture

```
+-----------------------------------------------------+
|                    Client App                        |
|         from ruleshield import OpenAI                |
+------------------------+----------------------------+
                         | HTTP/SDK Call
                         v
+------------------------------------------------------+
|                 RuleShield Proxy                      |
|  +-------------+  +--------------+  +-------------+  |
|  |   Layer 1   |  |   Layer 2    |  |   Layer 3   |  |
|  |  Semantic   |->|  Rule Engine |->| Smart Model |  |
|  |   Cache     |  |  (Decision   |  |   Router    |  |
|  |  (Redis +   |  |   Trees +    |  | (Complexity |  |
|  |  pgvector)  |  |  Confidence) |  |  Scoring)   |  |
|  +-------------+  +--------------+  +-------------+  |
|         |                |                 |          |
|    Cache Hit?       Rule Match?      Route to:        |
|    -> Return        -> Return if     -> Cheap Model   |
|                     confidence>0.95  -> Premium LLM   |
+----------+---------------+-----------+---------------+
           |               |             |
           v               v             v
   +--------------+ +------------+ +--------------+
   |  Metrics DB  | | Rule Mining| |  LLM APIs    |
   | (PostgreSQL) | |  Worker    | | OpenAI/Anth/ |
   |              | |  (Python)  | | Google/Local  |
   +--------------+ +------------+ +--------------+
           |
           v
   +----------------------+
   |  SvelteKit Dashboard |
   |  - Echtzeit Savings  |
   |  - Rule Explorer     |
   |  - Shadow Mode View  |
   |  - Wrapped Reports   |
   +----------------------+
```

### Shadow Mode Flow

```
Request -> Proxy sendet PARALLEL an:
  +-> Rule Engine (Regel-Antwort)
  +-> LLM API (echte Antwort)
       |
  Vergleich: Uebereinstimmung? -> Confidence Update
  Antwort: Immer LLM (Shadow = kein Risiko)
  Dashboard: Zeigt "haette gespart: $X"
```

---

## 3. Datenmodell

```sql
-- Kunden & Auth
CREATE TABLE organizations (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  plan TEXT DEFAULT 'free',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE api_keys (
  id UUID PRIMARY KEY,
  org_id UUID REFERENCES organizations(id),
  key_hash TEXT NOT NULL,
  name TEXT,
  permissions JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Request Tracking
CREATE TABLE requests (
  id UUID PRIMARY KEY,
  org_id UUID REFERENCES organizations(id),
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  input_hash TEXT NOT NULL,
  input_embedding vector(1536),
  output TEXT,
  tokens_in INT,
  tokens_out INT,
  cost_usd DECIMAL(10,6),
  resolution_type TEXT CHECK (resolution_type IN ('cache','rule','routed','llm')),
  latency_ms INT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Rule Engine
CREATE TABLE rules (
  id UUID PRIMARY KEY,
  org_id UUID REFERENCES organizations(id), -- NULL = global/marketplace
  pattern JSONB NOT NULL,                    -- Decision Tree Bedingungen
  response_template TEXT,
  confidence FLOAT NOT NULL DEFAULT 0,
  hit_count INT DEFAULT 0,
  accuracy FLOAT DEFAULT 0,                  -- Shadow Mode verified
  is_active BOOLEAN DEFAULT false,
  source TEXT CHECK (source IN ('auto','manual','marketplace')),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Savings & Metriken
CREATE TABLE daily_savings (
  org_id UUID REFERENCES organizations(id),
  date DATE NOT NULL,
  total_requests INT,
  cached INT,
  ruled INT,
  routed INT,
  llm_passthrough INT,
  cost_without_ruleshield DECIMAL(10,2),
  cost_with_ruleshield DECIMAL(10,2),
  savings_usd DECIMAL(10,2),
  savings_pct FLOAT,
  PRIMARY KEY (org_id, date)
);

-- Marketplace
CREATE TABLE rule_templates (
  id UUID PRIMARY KEY,
  author_org_id UUID REFERENCES organizations(id),
  category TEXT,
  pattern JSONB NOT NULL,
  description TEXT,
  installs INT DEFAULT 0,
  avg_accuracy FLOAT DEFAULT 0,
  is_public BOOLEAN DEFAULT false
);
```

---

## 4. Key Technical Decisions

| Entscheidung | Wahl | Warum |
|---|---|---|
| **SDK-Ansatz** | OpenAI-kompatibles Interface wrappen | 1-Line Drop-in, groesste Adoption |
| **Embedding-Modell** | Lokales Modell (e5-small) fuer Cache | Keine API-Kosten fuer Similarity-Check |
| **Rule Format** | JSONB Decision Trees | Inspectable, serializable, shareable |
| **Shadow vs Active** | Shadow als Default fuer neue Rules | Zero-Risk Onboarding, baut Vertrauen |
| **Multi-Tenancy** | Shared DB, Row-Level Security | Einfach, skaliert bis Enterprise |
| **Rule Mining** | Offline Batch (alle 6h) | Kein Latenz-Impact auf Proxy |

---

## 5. Implementation Phases

### Phase 1: Foundation (Wochen 1-3)

- [ ] TypeScript Proxy-Server mit OpenAI-kompatiblem Interface
- [ ] `from ruleshield import OpenAI` SDK-Wrapper (Python + JS)
- [ ] Request-Logging in PostgreSQL
- [ ] Redis Semantic Cache (exakte + Embedding-basierte Matches)
- [ ] Basis-Metriken: Requests, Cache Hits, Kosten
- [ ] Docker Setup + lokale Dev-Umgebung

### Phase 2: Rule Engine (Wochen 4-6)

- [ ] Python Rule Mining Worker (Decision Tree Extraction aus Request-Logs)
- [ ] Confidence Scoring System
- [ ] Rule Engine im Proxy (Pattern Matching + Response)
- [ ] Shadow Mode: Parallel-Ausfuehrung + Vergleich
- [ ] Shadow Mode Dashboard (SvelteKit)
- [ ] Automatisches Rule-Activation bei Confidence > 0.95

### Phase 3: Smart Router (Wochen 7-8)

- [ ] Request Complexity Classifier (Input-Features -> Schwierigkeits-Score)
- [ ] Multi-Provider Router (OpenAI, Anthropic, Google, lokale Modelle)
- [ ] Routing-Regeln konfigurierbar pro Org
- [ ] Fallback-Logik + Retry bei Provider-Fehler

### Phase 4: Dashboard & Viralitaet (Wochen 9-10)

- [ ] Echtzeit Savings Dashboard
- [ ] Rule Explorer (Regeln inspizieren, aktivieren/deaktivieren)
- [ ] "Wrapped" Report Generator (monatlich)
- [ ] Team-Leaderboards
- [ ] Slack-Integration (Savings-Alerts)
- [ ] CI/CD GitHub Action fuer Cost Reports in PRs

### Phase 5: Marketplace & Launch (Wochen 11-12)

- [ ] Rule Template Marketplace
- [ ] Freemium Billing (Stripe)
- [ ] API-Key Management
- [ ] Dokumentation + Landing Page
- [ ] Open-Source Cache-Layer Release

---

## 6. MVP Getting Started

```bash
# Monorepo Setup
mkdir ruleshield && cd ruleshield
npm init -y

# Struktur
mkdir -p packages/proxy        # TypeScript Proxy Server
mkdir -p packages/sdk-python   # Python SDK Wrapper
mkdir -p packages/sdk-node     # Node SDK Wrapper
mkdir -p packages/dashboard    # SvelteKit Dashboard
mkdir -p services/rule-miner   # Python Rule Mining Worker
mkdir -p infra                 # Docker, Configs

# Proxy starten
cd packages/proxy
npm init -y
npm i express openai redis pg pgvector
npm i -D typescript @types/express tsx

# Dashboard
cd ../dashboard
npx sv create . --template minimal --types ts
npm i tailwindcss @tailwindcss/vite chart.js
```

---

## 7. Kritischer Pfad zum Proof of Concept

Der schnellste Weg zum Demo-faehigen MVP:

1. **Tag 1-3**: Proxy der OpenAI-Requests durchleitet + loggt
2. **Tag 4-7**: Semantic Cache (Redis + Embeddings) -> erste messbare Savings
3. **Tag 8-14**: Einfaches Rule Mining (haeufigste Patterns -> Lookup Table)
4. **Tag 15-21**: Shadow Mode + Mini-Dashboard mit Savings-Anzeige

-> **In 3 Wochen ein Demo-faehiges System** das echte Savings zeigt.

---

## 8. Proxy Architecture Detail

### Request Pipeline

```
Incoming Request
      |
      v
[Auth Middleware] -> API Key validation
      |
      v
[Layer 1: Semantic Cache]
  - Exact hash match? -> Return cached response
  - Embedding similarity > 0.95? -> Return cached response
  - Miss -> Continue
      |
      v
[Layer 2: Rule Engine]
  - Pattern match against active rules
  - Confidence > threshold? -> Return rule response
  - Log shadow comparison if in shadow mode
  - Miss -> Continue
      |
      v
[Layer 3: Smart Router]
  - Classify request complexity (1-10)
  - Low complexity (1-3) -> Route to cheap model (e.g. Haiku, GPT-4o-mini)
  - Medium complexity (4-7) -> Route to mid-tier model
  - High complexity (8-10) -> Route to premium model (e.g. Opus, GPT-4o)
      |
      v
[Response Handler]
  - Log request + response + cost
  - Update cache
  - Feed to Rule Mining queue
  - Return response to client
```

### Latency Budget

| Component | Target Latency |
|---|---|
| Auth | < 1ms (in-memory) |
| Cache lookup | < 5ms |
| Rule matching | < 2ms |
| Complexity classification | < 3ms |
| Total overhead | < 15ms |
| LLM call (if needed) | 200-2000ms |

---

## 9. Rule Mining Worker Detail

### Process

```
Every 6 hours:
  1. Fetch last N requests from PostgreSQL
  2. Group by semantic similarity clusters
  3. For each cluster with >10 samples:
     a. Extract input features (length, keywords, intent)
     b. Train Decision Tree on input -> output mapping
     c. Calculate confidence score
     d. If confidence > 0.90: Create candidate rule
     e. If confidence > 0.95: Auto-activate (or shadow)
  4. Store rules in PostgreSQL
  5. Push hot rules to Redis for fast matching
```

### Rule Schema (JSONB)

```json
{
  "conditions": [
    {"field": "intent", "op": "eq", "value": "greeting"},
    {"field": "input_length", "op": "lt", "value": 50}
  ],
  "response_template": "Hello! How can I help you today?",
  "confidence": 0.97,
  "sample_count": 1432,
  "accuracy": 0.96
}
```
