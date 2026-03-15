# Add Provider Adapter: Together AI

**Labels:** `good first issue`, `help wanted`, `providers`, `enhancement`

## Description

Add Together AI as a supported provider in RuleShield's smart router and rule engine. Together AI hosts a wide range of open-source models with an OpenAI-compatible API, making it a popular choice for developers who want access to many models through a single provider.

## Why this is useful

Together AI is one of the largest open-source model hosting platforms, offering models from Llama, Mistral, Qwen, and many other families. By adding explicit Together AI support, RuleShield can intelligently route requests between cheap and expensive models on their platform, and apply appropriate rule confidence thresholds based on model capability. This makes RuleShield useful for the significant developer community already using Together AI.

## Where to look in the codebase

### Router changes

**File:** `ruleshield/router.py`

1. **Add to `model_map` (line ~162):**
   ```python
   "together": {
       "cheap": "meta-llama/Llama-3.2-3B-Instruct-Turbo",
       "mid": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
       "premium": None,  # keep original
   },
   ```

2. **Add to `_detect_provider()` (line ~312):**
   ```python
   if "together" in url:
       return "together"
   ```
   Place this before the `return "default"` fallback.

### Rules changes

**File:** `ruleshield/rules.py`

Add Together AI model names to `MODEL_CONFIDENCE_THRESHOLDS` (line ~54). Together AI uses fully-qualified model names with org prefixes:

```python
# Together AI
"meta-llama/llama-3.2-3b-instruct-turbo": 0.45,
"meta-llama/llama-3.1-8b-instruct-turbo": 0.50,
"meta-llama/llama-3.3-70b-instruct-turbo": 0.70,
"mistralai/mixtral-8x7b-instruct-v0.1": 0.65,
"qwen/qwen2.5-72b-instruct-turbo": 0.75,
```

Note: The `_get_model_threshold()` function in `ruleshield/rules.py` already strips provider prefixes using `rsplit("/", 1)[-1]` (line ~152), so models like `meta-llama/Llama-3.1-8B-Instruct-Turbo` will be matched against the part after the `/`. Consider whether to add thresholds for the full name, the short name, or both.

## Acceptance criteria

- [ ] `SmartRouter.model_map` in `ruleshield/router.py` contains a `"together"` entry with `cheap`, `mid`, and `premium` keys
- [ ] `SmartRouter._detect_provider()` returns `"together"` for URLs containing `together` (e.g., `https://api.together.xyz`)
- [ ] `MODEL_CONFIDENCE_THRESHOLDS` in `ruleshield/rules.py` contains entries for at least 3 Together AI model names
- [ ] Existing tests in `tests/` still pass
- [ ] (Bonus) Add a test case verifying provider detection for `https://api.together.xyz/v1`

## Estimated difficulty

**Easy** -- Same pattern as the existing Groq and DeepSeek provider entries. Two dict additions and one URL string check.

## Helpful links and references

- [Together AI API documentation](https://docs.together.ai/reference/chat-completions-1) -- OpenAI-compatible chat completions
- [Together AI model list](https://docs.together.ai/docs/chat-models) -- Available models and their names
- [Router source](../../ruleshield/router.py) -- Follow the pattern of existing providers
- [Rules source](../../ruleshield/rules.py) -- See `_get_model_threshold()` for how model names are resolved
