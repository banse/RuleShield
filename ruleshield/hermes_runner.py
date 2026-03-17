"""Compact execution runner for cron optimization profiles.

This keeps Phase 4 simple:
- the profile already contains a compact prompt template
- the caller provides the dynamic payload
- we execute one minimized chat-completions call against the configured provider
"""

from __future__ import annotations

from typing import Any

from ruleshield.config import Settings, load_settings


def _normalize_base_url(provider_url: str) -> str:
    provider_url = provider_url.rstrip("/")
    if provider_url.endswith("/v1"):
        return provider_url
    return f"{provider_url}/v1"


def _build_user_prompt(prompt_template: str, payload_text: str) -> str:
    """Build the compact user prompt from template plus payload."""
    template = (prompt_template or "Summarize this content.").strip()
    if "{content}" in template:
        return template.replace("{content}", payload_text)
    return f"{template}\n\nContent:\n{payload_text.strip()}"


class HermesRunner:
    """Minimal OpenAI-compatible execution wrapper for compact cron tasks."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()

    def run_compact_task(
        self,
        *,
        prompt_template: str,
        payload_text: str,
        model: str,
    ) -> dict[str, Any]:
        """Execute a compact prompt against the configured provider."""
        try:
            import openai
        except ImportError as exc:
            raise RuntimeError("The 'openai' package is required for compact cron execution.") from exc

        client = openai.OpenAI(
            api_key=self.settings.api_key or None,  # nosec
            base_url=_normalize_base_url(self.settings.provider_url),
        )
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": _build_user_prompt(prompt_template, payload_text),
                }
            ],
        )

        message = ""
        if response.choices:
            message = response.choices[0].message.content or ""

        return {
            "model": model,
            "prompt": _build_user_prompt(prompt_template, payload_text),
            "response_text": message,
            "raw_response": response.model_dump() if hasattr(response, "model_dump") else {},
        }


def run_compact_task(
    *,
    prompt_template: str,
    payload_text: str,
    model: str,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Convenience wrapper for one-shot compact execution."""
    runner = HermesRunner(settings=settings)
    return runner.run_compact_task(
        prompt_template=prompt_template,
        payload_text=payload_text,
        model=model,
    )
