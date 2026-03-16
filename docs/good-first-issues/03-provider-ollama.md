# Add Provider Adapter: Ollama (local models)

**Labels:** `good first issue`, `help wanted`, `providers`, `enhancement`

## Description

Add Ollama support to RuleShield so that developers running local models via Ollama can benefit from the same rule-based cost optimizations and smart routing. While local models are "free" in terms of API costs, rule interception still saves GPU compute time and reduces latency for predictable prompts.

This involves three changes:

1. Add Ollama to the SmartRouter's `model_map` and `_detect_provider()` method
2. Add local model confidence thresholds to the `MODEL_CONFIDENCE_THRESHOLDS` dict in `rules.py`
3. Ensure the proxy can forward requests to a local Ollama endpoint

## Why this is useful

Ollama is one of the most popular tools for running LLMs locally. Many developers use it for privacy, cost control, or offline development. Adding Ollama support makes RuleShield useful for an entirely new audience and demonstrates that the project works beyond just cloud API providers. Even with "free" local models, intercepting trivial prompts with rules reduces GPU load and response latency.

## Where to look in the codebase

### Router (provider detection and model mapping)

**File:** `ruleshield/router.py`

The `SmartRouter` class has two places to modify:

1. **`model_map` dict (line ~162)** -- Add an `"ollama"` entry with cheap/mid/premium model mappings for common Ollama models:
   ```python
   "ollama": {
       "cheap": "llama3.2:3b",
       "mid": "llama3.1:8b",
       "premium": None,  # keep original
   },
   ```

2. **`_detect_provider()` static method (line ~312)** -- Add URL detection for Ollama's default endpoint:
   ```python
   if "localhost:11434" in url or "ollama" in url:
       return "ollama"
   ```

### Rules (confidence thresholds)

**File:** `ruleshield/rules.py`

The `MODEL_CONFIDENCE_THRESHOLDS` dict (line ~54) needs entries for common Ollama model names. Since these are generally smaller models, they should have lower thresholds (more aggressive rule matching):

```python
# Ollama local models
"llama3.2:3b": 0.45,
"llama3.2:1b": 0.40,
"llama3.1:8b": 0.50,
"llama3.1:70b": 0.70,
"mistral:7b": 0.50,
"mixtral:8x7b": 0.65,
"phi3:mini": 0.45,
"gemma2:9b": 0.50,
"qwen2.5:7b": 0.50,
"codellama:7b": 0.50,
"deepseek-coder:6.7b": 0.50,
```

### Proxy (provider URL configuration)

**File:** `ruleshield/config.py`

The `Settings` dataclass (line ~31) already supports `provider_url`. Ollama users would set this to `http://localhost:11434`. No code change needed here, but mention it in the test instructions.

## Acceptance criteria

- [ ] `SmartRouter.model_map` in `ruleshield/router.py` contains an `"ollama"` entry with at least `cheap`, `mid`, and `premium` keys
- [ ] `SmartRouter._detect_provider()` in `ruleshield/router.py` correctly returns `"ollama"` for URLs containing `localhost:11434` or `ollama`
- [ ] `MODEL_CONFIDENCE_THRESHOLDS` in `ruleshield/rules.py` contains entries for at least 5 common Ollama model name formats (e.g., `llama3.1:8b`, `mistral:7b`)
- [ ] The `_get_model_threshold()` function's partial matching logic works with Ollama's `name:tag` format
- [ ] Existing tests in `tests/` still pass
- [ ] (Bonus) Add a simple test case verifying that `_detect_provider("http://localhost:11434")` returns `"ollama"`

## Testing locally

1. Install Ollama: https://ollama.ai
2. Pull a small model: `ollama pull llama3.2:3b`
3. Start RuleShield pointed at Ollama:
   ```bash
   RULESHIELD_PROVIDER_URL=http://localhost:11434 ruleshield start
   ```
4. Send a test request:
   ```bash
   curl http://localhost:8347/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model": "llama3.1:8b", "messages": [{"role": "user", "content": "hello"}]}'
   ```
5. Verify the response comes from a rule (check `ruleshield stats`)

## Estimated difficulty

**Medium** -- Requires modifying two Python files with small, well-scoped changes. Understanding of the router and rule engine is helpful but the code is well-commented.

## Helpful links and references

- [Ollama API documentation](https://github.com/ollama/ollama/blob/main/docs/api.md) -- Ollama uses an OpenAI-compatible API at `/v1/chat/completions`
- [Router source](../../ruleshield/router.py) -- SmartRouter and provider detection
- [Rules source](../../ruleshield/rules.py) -- Confidence thresholds and model matching
- [Config source](../../ruleshield/config.py) -- Settings and environment variables
