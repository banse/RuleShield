"""LLM model pricing for cost estimation."""

# Prices in USD per 1M tokens
MODEL_PRICING = {
    # OpenAI Codex
    "gpt-5.3-codex": {"input": 5.00, "output": 20.00},
    "gpt-5.2-codex": {"input": 2.50, "output": 10.00},
    "gpt-5.1-codex-max": {"input": 4.00, "output": 16.00},
    "gpt-5.1-codex-mini": {"input": 0.25, "output": 2.00},
    "gpt-5.4": {"input": 2.00, "output": 8.00},
    "gpt-5.4-pro": {"input": 5.00, "output": 20.00},
    # OpenAI Standard
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4.1": {"input": 2.00, "output": 8.00},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
    "gpt-4.1-nano": {"input": 0.10, "output": 0.40},
    "gpt-4.5": {"input": 75.00, "output": 150.00},
    "o3": {"input": 10.00, "output": 40.00},
    "o4-mini": {"input": 1.10, "output": 4.40},
    # Anthropic
    "claude-opus-4-6": {"input": 15.00, "output": 75.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.00},
    # Google
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    # DeepSeek
    "deepseek-chat": {"input": 0.27, "output": 1.10},
    "deepseek-r1": {"input": 0.55, "output": 2.19},
    # Open Source (approx hosting cost)
    "llama-3.1-8b": {"input": 0.05, "output": 0.08},
    "llama-3.1-70b": {"input": 0.52, "output": 0.75},
    "qwen-2.5-72b": {"input": 0.50, "output": 0.70},
    # Ollama / Local models (effectively free, track compute time instead)
    "llama3": {"input": 0.0, "output": 0.0},
    "llama3.1": {"input": 0.0, "output": 0.0},
    "mistral": {"input": 0.0, "output": 0.0},
    "phi3": {"input": 0.0, "output": 0.0},
    "phi4": {"input": 0.0, "output": 0.0},
    "gemma2": {"input": 0.0, "output": 0.0},
    "codellama": {"input": 0.0, "output": 0.0},
    "qwen2.5": {"input": 0.0, "output": 0.0},
}

DEFAULT_PRICING = {"input": 2.50, "output": 10.00}


def get_model_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost in USD for a given model and token counts."""
    model_lower = model.lower()

    # Strip provider prefix
    if "/" in model_lower:
        model_lower = model_lower.rsplit("/", 1)[-1]

    # Handle Ollama format: "llama3:8b" -> "llama3"
    if ":" in model_lower:
        model_lower = model_lower.split(":")[0]

    # Exact match
    pricing = MODEL_PRICING.get(model_lower)

    # Partial match
    if not pricing:
        for key, val in MODEL_PRICING.items():
            if key in model_lower or model_lower.startswith(key.split("-")[0]):
                pricing = val
                break

    if not pricing:
        pricing = DEFAULT_PRICING

    return (input_tokens / 1_000_000) * pricing["input"] + (output_tokens / 1_000_000) * pricing["output"]
