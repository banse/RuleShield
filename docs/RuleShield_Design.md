# RuleShield Design Spec -- Dark Vibe

---

## Target Audience

> Developer und Platform Engineers (DevOps Dana, AI Agent Andy) die taeglich in Terminals und Dark-Mode-IDEs arbeiten. Tech-savvy, schaetzen Effizienz, Klarheit und "no bullshit" Kommunikation. Sekundaer: Engineering Leadership (Enterprise Eva) die Dashboards und ROI-Zahlen braucht.

---

## Design Inspiration

| Site | Warum diese Audience es liebt | Was wir uebernehmen |
|------|-------------------------------|---------------------|
| **linear.app** | Schnell, keyboard-first, perfekter Dark Mode | Card-Layout, subtile Borders, Glow-Effekte |
| **vercel.com** | Developer-Vertrauen, clean Dark Aesthetic | Hero mit Code-Snippet, Gradient Accents |
| **raycast.com** | Tool-fuer-Entwickler Vibe, Spotlight-Effekt | Glassmorphism-Cards, Neon-Akzente |
| **stripe.com/docs** | Trusted by Devs, Daten-heavy aber klar | Dashboard-Previews, Metriken-Darstellung |
| **warp.dev** | Terminal-nahe Aesthetic, modern-dark | Monospace-Code-Blocks, Glow-on-hover |

---

## Color Palette

```
Background:       #0A0A0F  (Deep Dark -- fast schwarz, leichter Blau-Stich)
Surface:          #12121A  (Card Background)
Surface Elevated: #1A1A26  (Hover States, Dropdowns)
Border:           #2A2A3C  (Subtile Dividers -- 3:1 Kontrast)

Primary:          #6C5CE7  (Electric Purple -- Brand Color)
Primary Hover:    #7D6FF0  (Heller fuer Hover)
Primary Active:   #5A4BD4  (Dunkler fuer Active)

Accent:           #00D4AA  (Mint Green -- Savings/Success Farbe)
Accent Glow:      #00D4AA33 (fuer Glow-Effekte)

Text Primary:     #F0F0F5  (Headings -- 15.3:1 Kontrast auf BG)
Text Secondary:   #A0A0B8  (Body Text -- 7.2:1 Kontrast auf BG)
Text Muted:       #6B6B82  (Labels, Hints -- 4.5:1 Kontrast)

Success:          #00D4AA  (Savings, positive Zahlen)
Error:            #FF6B6B  (Fehler, Alerts)
Warning:          #FFB84D  (Warnungen)

Gradient Hero:    linear-gradient(135deg, #6C5CE7 0%, #00D4AA 100%)
```

---

## Typography

```
Font Family:  "Inter" (Headings + Body), "JetBrains Mono" (Code)

Hero:         56px / 60px / 700 weight  -- Landing Page Headline
H1:           40px / 44px / 600 weight  -- Page Titles
H2:           32px / 36px / 600 weight  -- Section Headers
H3:           24px / 28px / 600 weight  -- Card Titles
Body Large:   18px / 28px / 400 weight  -- Feature Descriptions
Body:         16px / 24px / 400 weight  -- Standard Text
Small:        14px / 20px / 400 weight  -- Captions, Meta
Label:        12px / 16px / 500 weight  -- Tags, Badges, Overlines
Code:         14px / 20px / 400 weight  -- JetBrains Mono
```

---

## Spacing (8pt Grid)

```
xs:   4px    (0.25rem)  -- Tight internal padding
sm:   8px    (0.5rem)   -- Icon gaps, badge padding
md:   16px   (1rem)     -- Between related elements
lg:   24px   (1.5rem)   -- Card padding, component groups
xl:   32px   (2rem)     -- Section padding horizontal
2xl:  48px   (3rem)     -- Between sections
3xl:  64px   (4rem)     -- Major section divisions
4xl:  96px   (6rem)     -- Hero vertical padding
```

---

## Landing Page Wireframe

### Hero Section (Above the Fold)

```
[Nav: Logo | Features | Pricing | Docs | GitHub Star Count | "Get Started" Button]

                    [Overline: "DROP-IN LLM COST OPTIMIZER"]

              One line of code.
              80% less LLM cost.

    [Subheadline: "RuleShield sits between your app and any LLM API.
     Semantic caching, auto-learned rules, and smart routing --
     no code changes beyond the import."]

    [CTA: "Start Free" (Primary)]  [CTA: "See Demo" (Ghost)]

    [Trust Bar: "Saving $2.4M/month across 340+ teams"]

    +----------------------------------------------+
    |  # Before                    # After         |
    |  from openai import OpenAI   from ruleshield |
    |                              import OpenAI   |
    |                                              |
    |  [Animated savings counter: $0 -> $12,847]   |
    +----------------------------------------------+
```

### Section 2: Problem -- Agitate -- Solve

```
    "You're burning money on repeat questions."

    [3 Pain Cards mit Icons:]
    +------------+ +------------+ +------------+
    | 60-80% der | | Jeder Call | | Kein Ein-  |
    | Requests   | | kostet     | | blick was  |
    | sind       | | gleich     | | repetitiv  |
    | repetitiv  | | viel       | | ist        |
    +------------+ +------------+ +------------+

    "RuleShield learns what doesn't need an LLM."
```

### Section 3: 3-Layer Intelligence (Feature Showcase)

```
    "Three layers. One import."

    [Layer 1: Semantic Cache]
    +--------------------------------------+
    |  Icon: Lightning                      |
    |  "Identical and similar requests      |
    |   answered from cache in <5ms"        |
    |  [Animated: Cache Hit Rate 73%]       |
    +--------------------------------------+

    [Layer 2: Rule Engine]
    +--------------------------------------+
    |  Icon: Brain/Tree                     |
    |  "Auto-extracted decision rules       |
    |   handle patterns with 97% accuracy"  |
    |  [Animated: Rule Tree Visualization]  |
    +--------------------------------------+

    [Layer 3: Smart Router]
    +--------------------------------------+
    |  Icon: Route/Split                    |
    |  "Complex requests go to GPT-4o.      |
    |   Simple ones to Haiku. Automatically."|
    |  [Animated: Request Flow Diagram]     |
    +--------------------------------------+
```

### Section 4: Shadow Mode (Trust Builder)

```
    "Prove savings before you commit."

    +--------------------------------------------+
    |  [Dashboard Preview -- Dark Theme]         |
    |                                            |
    |  Shadow Mode: Active     14 days running   |
    |  +------+ +------+ +------+               |
    |  |$4,291| | 142  | |94.7% |               |
    |  |saved | |rules | |accur.|               |
    |  +------+ +------+ +------+               |
    |                                            |
    |  [Button: "Activate Rules"]                |
    +--------------------------------------------+

    "Shadow Mode runs parallel to your LLM.
     Same responses go to your users.
     You see what RuleShield would have saved."
```

### Section 5: Social Proof

```
    "Teams saving millions."

    [3 Testimonial Cards mit Glow-Border:]
    "We cut our OpenAI bill from $47k to $12k/month."
    -- CTO, Series B Startup

    [Logo Bar: Company Logos]
    [Stats: "340+ Teams | $2.4M saved/month | 94% avg accuracy"]
```

### Section 6: Pricing

```
    +---------+  +----------+  +------------+
    |  Free   |  |   Pro    |  | Enterprise |
    |  $0     |  | 15% of   |  |  Custom    |
    |         |  | savings  |  |            |
    | < $500  |  | Unlim.   |  | SSO, SLA   |
    | savings |  | Shadow   |  | Custom     |
    | 1 proj  |  | 10 proj  |  | Rules      |
    |         |  |          |  |            |
    |[Start]  |  |[Start]   |  |[Contact]   |
    +---------+  +----------+  +------------+

    "3x ROI guaranteed or your money back."
```

### Section 7: Final CTA

```
    "Stop paying for answers you already have."

    [CTA: "Start Free -- No Credit Card"] [CTA: "Book Demo"]

    [Code Snippet: pip install ruleshield]
```

---

## Key Components

| Component | States | Specs |
|-----------|--------|-------|
| **Button Primary** | default (#6C5CE7), hover (#7D6FF0 + glow), focus (2px #6C5CE7 outline), active (#5A4BD4), disabled (40% opacity), loading (spinner) | h-12, px-6, rounded-lg, font-semibold |
| **Button Ghost** | default (transparent, border #2A2A3C), hover (bg #1A1A26), focus, active, disabled | Same height, border-1 |
| **Nav** | default (transparent), scrolled (bg #0A0A0F/80 + backdrop-blur), mobile (hamburger slide-in) | h-16, sticky top-0, z-50 |
| **Card** | default (bg #12121A, border #2A2A3C), hover (border #6C5CE7/50 + subtle glow) | p-6, rounded-xl |
| **Metric Card** | default, animated (count-up on scroll-in) | Zahl in 32px/700, Label in 14px/500 |
| **Code Block** | default (bg #12121A), with copy button | JetBrains Mono, p-4, rounded-lg |
| **Input** | empty, filled, focus (border #6C5CE7), error (border #FF6B6B + message), disabled | h-12, rounded-lg, bg #12121A |
| **Badge/Tag** | default, active | px-3 py-1, rounded-full, text-xs |
| **Savings Counter** | animated count-up, idle | Accent color #00D4AA, tabular-nums |

---

## Tailwind Config

```javascript
// tailwind.config.js
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      colors: {
        bg: '#0A0A0F',
        surface: {
          DEFAULT: '#12121A',
          elevated: '#1A1A26',
        },
        border: '#2A2A3C',
        primary: {
          DEFAULT: '#6C5CE7',
          hover: '#7D6FF0',
          active: '#5A4BD4',
        },
        accent: {
          DEFAULT: '#00D4AA',
          glow: 'rgba(0, 212, 170, 0.2)',
        },
        text: {
          primary: '#F0F0F5',
          secondary: '#A0A0B8',
          muted: '#6B6B82',
        },
        success: '#00D4AA',
        error: '#FF6B6B',
        warning: '#FFB84D',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      borderRadius: {
        button: '8px',
        card: '12px',
        input: '8px',
      },
      boxShadow: {
        glow: '0 0 20px rgba(108, 92, 231, 0.3)',
        'glow-accent': '0 0 20px rgba(0, 212, 170, 0.3)',
      },
      animation: {
        'count-up': 'countUp 2s ease-out forwards',
        'fade-in': 'fadeIn 0.6s ease-out forwards',
        'slide-up': 'slideUp 0.6s ease-out forwards',
      },
    },
  },
}
```
