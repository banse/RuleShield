# Add Provider Adapter: Groq

**Labels:** `good first issue`, `help wanted`, `providers`, `enhancement`

## Description

Add Groq as a supported provider in RuleShield's smart router and rule engine. Groq offers extremely fast inference on open-source models via their cloud API, and their endpoint is OpenAI-compatible, making integration straightforward.

## Why this is useful

Groq is popular for its low-latency inference (often under 500ms for small models). Developers using Groq through RuleShield can benefit from rule interception on trivial prompts, reducing even the small per-token costs Groq charges. Since Groq's API is OpenAI-compatible, RuleShield's proxy should already forward requests correctly -- this issue is about adding explicit provider detection and model mappings so the smart router knows which Groq models are cheap vs. premium.

## Where to look in the codebase

### Router changes

**File:** `ruleshield/router.py`

1. **Add to `model_map` (line ~162):**
   ```python
   "groq": {
       "cheap": "llama-3.1-8b-instant",
       "mid": "llama-3.3-70b-versatile",
       "premium": None,  # keep original
   },
   ```

2. **Add to `_detect_provider()` (line ~312):**
   ```python
   if "groq" in url:
       return "groq"
   ```
   Place this check before the generic `"default"` return at the end of the method.

### Rules changes

**File:** `ruleshield/rules.py`

Add Groq model names to `MODEL_CONFIDENCE_THRESHOLDS` (line ~54):
```python
# Groq
"llama-3.1-8b-instant": 0.50,
"llama-3.3-70b-versatile": 0.70,
"mixtral-8x7b-32768": 0.65,
"gemma2-9b-it": 0.55,
```

## Acceptance criteria

- [ ] `SmartRouter.model_map` in `ruleshield/router.py` contains a `"groq"` entry
- [ ] `SmartRouter._detect_provider()` returns `"groq"` for URLs containing `groq` (e.g., `https://api.groq.com/openai`)
- [ ] `MODEL_CONFIDENCE_THRESHOLDS` in `ruleshield/rules.py` contains entries for at least 3 Groq model names
- [ ] Existing tests in `tests/` still pass
- [ ] (Bonus) Add a test case verifying provider detection for `https://api.groq.com/openai/v1`

## Estimated difficulty

**Easy** -- Two small dict additions and one URL check. The pattern is already established by existing providers like OpenAI and DeepSeek in the same files.

## Helpful links and references

- [Groq API documentation](https://console.groq.com/docs/quickstart) -- OpenAI-compatible endpoints
- [Groq supported models](https://console.groq.com/docs/models) -- Current model list
- [Router source](../../ruleshield/router.py) -- Existing provider mappings to follow
- [Rules source](../../ruleshield/rules.py) -- Existing threshold entries to follow
