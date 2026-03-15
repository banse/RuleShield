# Rules: Add multilingual greeting/confirmation patterns

**Labels:** `good first issue`, `help wanted`, `rules`, `i18n`, `enhancement`

## Description

Create a new rule pack file `rules/multilingual.json` containing rules that intercept common greetings, confirmations, acknowledgments, and farewells in multiple languages: French, Spanish, Japanese, Chinese, Korean, and Portuguese. These are the same types of short, predictable messages already handled in English by `rules/default_hermes.json`, but for non-English users.

## Why this is useful

LLM applications serve a global audience. A chatbot used in France, Brazil, or Japan receives the same types of trivial messages (greetings, "yes", "thanks", "goodbye") but in different languages. Without multilingual rules, RuleShield can only intercept English patterns, missing cost savings for non-English traffic. This rule pack makes RuleShield effective for international deployments.

The existing `rules/default_hermes.json` already handles English greetings, acknowledgments, confirmations, and goodbyes. The cache system in `ruleshield/cache.py` also has some German temporal keywords (line ~176: `"jetzt", "gerade", "aktuell", "heute"`), showing that multilingual support is already on the radar.

## Where to look in the codebase

- **English rule reference:** `rules/default_hermes.json` -- The rules to replicate in other languages
- **Rule engine:** `ruleshield/rules.py` -- Pattern matching is case-insensitive (`text.lower()` is called in `_single_pattern_matches()`)
- **Pattern types:** `exact`, `contains`, `regex` -- all work with Unicode strings in Python

### Important note on encoding

The rule engine reads JSON files with `encoding="utf-8"` (see `_load_rules()` in `ruleshield/rules.py`, line ~598), so non-ASCII characters (Japanese, Chinese, Korean, etc.) are fully supported.

## What to build

Create `rules/multilingual.json` with rules for these languages and categories:

### French
- Greetings: "bonjour", "salut", "bonsoir", "coucou"
- Confirmations: "oui", "non", "d'accord", "bien sur"
- Acknowledgments: "merci", "merci beaucoup", "compris", "entendu"
- Goodbyes: "au revoir", "a bientot", "bonne journee"

### Spanish
- Greetings: "hola", "buenos dias", "buenas tardes", "buenas noches"
- Confirmations: "si", "no", "claro", "vale", "de acuerdo"
- Acknowledgments: "gracias", "muchas gracias", "entendido", "perfecto"
- Goodbyes: "adios", "hasta luego", "nos vemos"

### Japanese
- Greetings: "こんにちは", "おはよう", "こんばんは"
- Confirmations: "はい", "いいえ", "了解", "分かりました"
- Acknowledgments: "ありがとう", "ありがとうございます", "承知しました"
- Goodbyes: "さようなら", "お疲れ様", "失礼します"

### Chinese (Simplified)
- Greetings: "你好", "您好", "早上好"
- Confirmations: "是", "好的", "可以", "明白了"
- Acknowledgments: "谢谢", "非常感谢", "收到", "了解"
- Goodbyes: "再见", "拜拜", "下次见"

### Korean
- Greetings: "안녕하세요", "안녕"
- Confirmations: "네", "아니요", "알겠습니다"
- Acknowledgments: "감사합니다", "고마워요", "이해했습니다"
- Goodbyes: "안녕히 계세요", "또 만나요"

### Portuguese
- Greetings: "ola", "bom dia", "boa tarde", "boa noite"
- Confirmations: "sim", "nao", "certo", "pode ser"
- Acknowledgments: "obrigado", "obrigada", "entendi", "valeu"
- Goodbyes: "tchau", "ate logo", "ate mais"

## Rule format example

```json
{
  "id": "ml_greeting_french",
  "name": "French Greeting",
  "description": "Intercepts common French greetings like bonjour, salut, bonsoir.",
  "patterns": [
    {"type": "exact", "value": "bonjour", "field": "last_user_message"},
    {"type": "exact", "value": "salut", "field": "last_user_message"},
    {"type": "exact", "value": "bonsoir", "field": "last_user_message"},
    {"type": "exact", "value": "coucou", "field": "last_user_message"},
    {"type": "contains", "value": "bonjour", "field": "last_user_message"}
  ],
  "conditions": [
    {"type": "max_length", "value": 25, "field": "last_user_message"}
  ],
  "response": {
    "content": "Bonjour ! Comment puis-je vous aider aujourd'hui ?",
    "model": "ruleshield-rule"
  },
  "confidence": 0.90,
  "priority": 8,
  "enabled": true,
  "hit_count": 0
}
```

## Acceptance criteria

- [ ] File `rules/multilingual.json` exists and contains valid JSON (array of rule objects)
- [ ] Contains rules covering at least 4 of the 6 languages listed above
- [ ] Each language has at least 3 rule categories (greetings, confirmations, acknowledgments, or goodbyes)
- [ ] Every rule has a unique `id` prefixed with `ml_` (e.g., `ml_greeting_french`, `ml_confirm_japanese`)
- [ ] All required fields are present: `id`, `name`, `description`, `patterns`, `conditions`, `response`, `confidence`, `priority`, `enabled`, `hit_count`
- [ ] Responses are written in the appropriate language (not in English)
- [ ] The file uses UTF-8 encoding and non-ASCII characters render correctly
- [ ] The file loads without errors in the RuleEngine
- [ ] `max_length` conditions account for the character length differences between languages (CJK characters are shorter strings but same semantic weight)

## Estimated difficulty

**Easy** -- JSON authoring only. No Python changes. Basic knowledge of the target languages (or willingness to research common phrases) is the main requirement. Machine translation tools can help, but ideally have a native speaker review.

## Helpful links and references

- [Default rules file](../../rules/default_hermes.json) -- English rules to replicate
- [Rule engine source](../../ruleshield/rules.py) -- Pattern matching and UTF-8 handling
- [Cache temporal keywords](../../ruleshield/cache.py) -- Existing multilingual awareness (German keywords, line ~176)
