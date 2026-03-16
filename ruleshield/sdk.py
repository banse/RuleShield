"""Drop-in OpenAI SDK wrapper that routes through RuleShield proxy.

Usage:
    # Before:
    from openai import OpenAI
    client = OpenAI()

    # After (one line change):
    from ruleshield.sdk import OpenAI
    client = OpenAI()

    # Everything else stays the same
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Hello"}],
    )
"""

import os

RULESHIELD_PROXY_URL = os.getenv("RULESHIELD_PROXY_URL", "http://127.0.0.1:8347/v1")


def OpenAI(**kwargs):
    """Create an OpenAI client that routes through RuleShield proxy.

    Automatically sets base_url to the RuleShield proxy.
    All other arguments are passed through to the real OpenAI client.

    Environment variables:
        RULESHIELD_PROXY_URL: Override proxy URL (default: http://127.0.0.1:8347/v1)
        OPENAI_API_KEY: Your OpenAI API key (passed through to proxy)
    """
    try:
        import openai
    except ImportError:
        raise ImportError(
            "The 'openai' package is required. Install it with: pip install openai"
        )

    # Set base_url to proxy unless explicitly provided
    if "base_url" not in kwargs:
        kwargs["base_url"] = RULESHIELD_PROXY_URL

    return openai.OpenAI(**kwargs)


def AsyncOpenAI(**kwargs):
    """Async version of the RuleShield OpenAI wrapper."""
    try:
        import openai
    except ImportError:
        raise ImportError(
            "The 'openai' package is required. Install it with: pip install openai"
        )

    if "base_url" not in kwargs:
        kwargs["base_url"] = RULESHIELD_PROXY_URL

    return openai.AsyncOpenAI(**kwargs)


def Anthropic(**kwargs):
    """Create an Anthropic client that routes through RuleShield proxy."""
    try:
        import anthropic
    except ImportError:
        raise ImportError(
            "The 'anthropic' package is required. Install it with: pip install anthropic"
        )

    if "base_url" not in kwargs:
        kwargs["base_url"] = RULESHIELD_PROXY_URL.replace("/v1", "")

    return anthropic.Anthropic(**kwargs)
