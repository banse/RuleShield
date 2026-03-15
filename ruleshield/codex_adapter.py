"""Adapter between Codex Responses API format and RuleShield's internal format.

The OpenAI Codex Responses API uses a different request/response schema from
the Chat Completions API that RuleShield's cache and rule engine operate on
internally.

Codex Responses API uses:
  - Request:  {"model": "...", "instructions": "...", "input": [...], "stream": true}
  - Response: {"id": "resp_...", "output": [...], "usage": {...}}

RuleShield's cache/rules expect:
  - Prompt text: flat string extracted from messages
  - Response: OpenAI chat completion format with choices array

This module provides pure-function adapters that convert between the two
formats so the proxy can apply caching and rule matching to Codex traffic
without modifying the core engine.

Performance target: all functions < 1ms for typical payloads.
"""

from __future__ import annotations

import json
import time
from typing import Any


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Maximum number of characters from instructions to include in the cache
# key prefix.  Longer instructions are truncated to keep cache keys stable
# across minor wording changes in the system prompt.
_INSTRUCTIONS_PREFIX_LEN = 120

# Default chunk size (in characters) when splitting content for simulated
# streaming deltas.  Tuned to produce chunks that look natural when rendered
# by Hermes/LiteLLM -- small enough for smooth output, large enough to avoid
# excessive event overhead.
_DEFAULT_CHUNK_SIZE = 20


# ---------------------------------------------------------------------------
# Request adapters
# ---------------------------------------------------------------------------

def extract_prompt_from_codex(body: dict[str, Any]) -> str:
    """Extract a flat prompt string from a Codex Responses API request body.

    Codex request format -- structured input::

        {
            "model": "gpt-5.4",
            "instructions": "You are a helpful assistant...",
            "input": [
                {"type": "message", "role": "user", "content": "Hello"},
                {"type": "message", "role": "assistant", "content": "Hi there"},
                {"type": "message", "role": "user", "content": "What is Python?"}
            ],
            "tools": [...],
            "stream": true
        }

    Codex request format -- simple string input::

        {
            "model": "gpt-5.4",
            "input": "What is Python?",
            "stream": true
        }

    The function returns the last user message as the prompt text for
    cache/rule matching.  When ``instructions`` are present, a truncated
    prefix is prepended to produce a more specific cache key that
    distinguishes identical user prompts sent with different system
    instructions.

    Returns an empty string when no extractable content is found.
    """
    raw_input = body.get("input")
    instructions = body.get("instructions", "")

    # --- Determine the core user prompt ---
    last_user_msg = ""

    if isinstance(raw_input, str):
        # Simple string input: the entire input is the prompt.
        last_user_msg = raw_input.strip()

    elif isinstance(raw_input, list):
        # Structured message list: walk backwards to find the last user msg.
        last_user_msg = _last_user_content_from_items(raw_input)

    if not last_user_msg:
        return ""

    # Prepend a truncated instructions prefix for cache key specificity.
    if instructions:
        prefix = instructions.strip()[:_INSTRUCTIONS_PREFIX_LEN]
        return f"[inst:{prefix}] {last_user_msg}"

    return last_user_msg


def extract_messages_from_codex(body: dict[str, Any]) -> list[dict[str, str]]:
    """Convert a Codex Responses API request body to OpenAI messages format.

    The rule engine's ``match()`` method expects a list of messages in the
    standard ``[{"role": "...", "content": "..."}]`` shape.  This function
    performs the translation, mapping:

      - ``body["instructions"]``  -> ``{"role": "system", "content": ...}``
      - ``body["input"]`` items   -> ``{"role": <role>, "content": <content>}``

    When ``input`` is a plain string it is treated as a single user message.

    Returns an empty list when no input is found.
    """
    messages: list[dict[str, str]] = []
    instructions = body.get("instructions", "")
    raw_input = body.get("input")

    # System message from instructions.
    if instructions:
        messages.append({"role": "system", "content": instructions})

    if isinstance(raw_input, str):
        # Simple string input -> single user message.
        if raw_input.strip():
            messages.append({"role": "user", "content": raw_input.strip()})

    elif isinstance(raw_input, list):
        for item in raw_input:
            if not isinstance(item, dict):
                continue

            item_type = item.get("type", "")
            role = item.get("role", "")
            content = _extract_item_content(item)

            # Codex uses type="message" for conversational items.
            if item_type == "message" and role and content:
                messages.append({"role": role, "content": content})

            # Also handle items that have role+content but no explicit type,
            # for forward-compatibility with slight format variations.
            elif role and content and item_type in ("", "message"):
                messages.append({"role": role, "content": content})

    return messages


# ---------------------------------------------------------------------------
# Response adapters
# ---------------------------------------------------------------------------

def wrap_codex_response(
    content: str,
    model: str = "ruleshield-rule",
    request_id: str = "",
) -> dict[str, Any]:
    """Wrap a plain text response in Codex Responses API format (non-streaming).

    Produces a complete ``response`` object that Hermes/LiteLLM can parse
    identically to a real Codex provider response::

        {
            "id": "resp_ruleshield_1234567890",
            "object": "response",
            "created_at": 1234567890.0,
            "status": "completed",
            "model": "ruleshield-rule",
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [
                        {"type": "output_text", "text": "Hello! How can I help?"}
                    ]
                }
            ],
            "usage": {
                "input_tokens": 0,
                "output_tokens": 5,
                "total_tokens": 5
            }
        }
    """
    resp_id = request_id or f"resp_ruleshield_{int(time.time())}"
    output_tokens = max(len(content.split()), 1)

    return {
        "id": resp_id,
        "object": "response",
        "created_at": time.time(),
        "status": "completed",
        "model": model,
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [
                    {"type": "output_text", "text": content},
                ],
            }
        ],
        "usage": {
            "input_tokens": 0,
            "output_tokens": output_tokens,
            "total_tokens": output_tokens,
        },
    }


def wrap_codex_streaming_response(
    content: str,
    model: str = "ruleshield-rule",
    request_id: str = "",
) -> list[str]:
    """Generate SSE events for a Codex-style streaming response.

    Returns a list of SSE-formatted strings that mimic the Codex streaming
    event sequence.  Each string is a complete SSE event (with trailing
    blank line) ready to be written directly to the response stream.

    Event sequence:

    1. ``response.created``          -- signals response object creation
    2. ``response.in_progress``      -- status transition
    3. ``response.output_item.added``-- output message item added
    4. ``response.content_part.added``-- content part initialised
    5. ``response.output_text.delta`` -- one per text chunk (N events)
    6. ``response.content_part.done`` -- content part finalised
    7. ``response.output_item.done`` -- output message item finalised
    8. ``response.output_text.done`` -- full text available
    9. ``response.completed``        -- terminal event with usage

    All events include a monotonically increasing ``sequence_number`` field
    so consumers can detect dropped or reordered events.

    This allows rule/cache hits to return streaming responses that
    Hermes/LiteLLM can parse identically to real Codex responses.
    """
    events: list[str] = []
    resp_id = request_id or f"resp_ruleshield_{int(time.time())}"
    item_id = f"msg_{resp_id}"
    created_at = time.time()
    seq = 0  # monotonically increasing sequence number

    # -- Event 1: response.created --
    seq += 1
    events.append(format_sse("response.created", {
        "type": "response.created",
        "sequence_number": seq,
        "response": {
            "id": resp_id,
            "object": "response",
            "created_at": created_at,
            "status": "in_progress",
            "model": model,
            "output": [],
            "usage": None,
        },
    }))

    # -- Event 2: response.in_progress --
    seq += 1
    events.append(format_sse("response.in_progress", {
        "type": "response.in_progress",
        "sequence_number": seq,
        "response": {
            "id": resp_id,
            "object": "response",
            "created_at": created_at,
            "status": "in_progress",
            "model": model,
            "output": [],
            "usage": None,
        },
    }))

    # -- Event 3: output_item.added (the assistant message item) --
    output_item = {
        "type": "message",
        "id": item_id,
        "role": "assistant",
        "status": "in_progress",
        "content": [],
    }
    seq += 1
    events.append(format_sse("response.output_item.added", {
        "type": "response.output_item.added",
        "sequence_number": seq,
        "output_index": 0,
        "item": output_item,
    }))

    # -- Event 4: content_part.added --
    seq += 1
    events.append(format_sse("response.content_part.added", {
        "type": "response.content_part.added",
        "sequence_number": seq,
        "item_id": item_id,
        "output_index": 0,
        "content_index": 0,
        "part": {"type": "output_text", "text": ""},
    }))

    # -- Event 5: output_text.delta (one per chunk) --
    chunks = _split_into_chunks(content, chunk_size=_DEFAULT_CHUNK_SIZE)
    for chunk in chunks:
        seq += 1
        events.append(format_sse("response.output_text.delta", {
            "type": "response.output_text.delta",
            "sequence_number": seq,
            "item_id": item_id,
            "output_index": 0,
            "content_index": 0,
            "delta": chunk,
        }))

    # -- Event 6: content_part.done --
    seq += 1
    events.append(format_sse("response.content_part.done", {
        "type": "response.content_part.done",
        "sequence_number": seq,
        "item_id": item_id,
        "output_index": 0,
        "content_index": 0,
        "part": {"type": "output_text", "text": content},
    }))

    # -- Event 7: output_item.done --
    completed_item = {
        "type": "message",
        "id": item_id,
        "role": "assistant",
        "status": "completed",
        "content": [{"type": "output_text", "text": content}],
    }
    seq += 1
    events.append(format_sse("response.output_item.done", {
        "type": "response.output_item.done",
        "sequence_number": seq,
        "output_index": 0,
        "item": completed_item,
    }))

    # -- Event 8: output_text.done --
    seq += 1
    events.append(format_sse("response.output_text.done", {
        "type": "response.output_text.done",
        "sequence_number": seq,
        "item_id": item_id,
        "output_index": 0,
        "content_index": 0,
        "text": content,
    }))

    # -- Event 9: response.completed --
    output_tokens = max(len(content.split()), 1)
    seq += 1
    events.append(format_sse("response.completed", {
        "type": "response.completed",
        "sequence_number": seq,
        "response": {
            "id": resp_id,
            "object": "response",
            "created_at": created_at,
            "status": "completed",
            "model": model,
            "output": [
                {
                    "type": "message",
                    "id": item_id,
                    "role": "assistant",
                    "status": "completed",
                    "content": [{"type": "output_text", "text": content}],
                }
            ],
            "usage": {
                "input_tokens": 0,
                "output_tokens": output_tokens,
                "total_tokens": output_tokens,
            },
        },
    }))

    return events


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------

def is_codex_request(body: dict[str, Any]) -> bool:
    """Return True if the request body looks like a Codex Responses API call.

    Heuristic: Codex requests use ``input`` (not ``messages``) and lack the
    ``messages`` key that Chat Completions use.  The presence of
    ``instructions`` is a strong secondary signal.
    """
    if "input" in body and "messages" not in body:
        return True
    if "instructions" in body and "messages" not in body:
        return True
    return False


# ---------------------------------------------------------------------------
# SSE formatting
# ---------------------------------------------------------------------------

def format_sse(event_type: str, data: dict[str, Any]) -> str:
    """Format a single Server-Sent Event.

    Produces the standard SSE wire format::

        event: <event_type>
        data: <json>

    (with a trailing blank line to delimit the event).

    The JSON is serialised on a single line with no unnecessary whitespace
    to minimise bandwidth.
    """
    return f"event: {event_type}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _last_user_content_from_items(items: list[Any]) -> str:
    """Walk a Codex input items list backwards to find the last user message.

    Handles several content representations:
      - Plain string ``content``
      - List of content parts (``[{"type": "input_text", "text": "..."}]``)
      - Nested ``content`` arrays with ``type: "text"``
    """
    for item in reversed(items):
        if not isinstance(item, dict):
            continue
        if item.get("role") != "user":
            continue

        content = item.get("content", "")

        if isinstance(content, str):
            text = content.strip()
            if text:
                return text

        if isinstance(content, list):
            parts: list[str] = []
            for part in content:
                if not isinstance(part, dict):
                    continue
                # Codex uses "input_text" for user input parts.
                if part.get("type") in ("input_text", "text"):
                    text_val = part.get("text", "")
                    if text_val:
                        parts.append(text_val)
            joined = " ".join(parts).strip()
            if joined:
                return joined

    return ""


def _extract_item_content(item: dict[str, Any]) -> str:
    """Extract the text content from a single Codex input item.

    Supports both plain string and structured content array formats.
    """
    content = item.get("content", "")

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") in ("input_text", "text"):
                text_val = part.get("text", "")
                if text_val:
                    parts.append(text_val)
        return " ".join(parts).strip()

    return ""


def _split_into_chunks(text: str, chunk_size: int = _DEFAULT_CHUNK_SIZE) -> list[str]:
    """Split text into chunks for streaming simulation.

    Splits on word boundaries to avoid cutting words mid-character.  Each
    chunk is approximately ``chunk_size`` characters but may be slightly
    larger to preserve word integrity.

    An empty input produces a single empty-string chunk so the delta
    sequence is never empty (consumers expect at least one delta event).
    """
    if not text:
        return [""]

    words = text.split(" ")
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for word in words:
        # Account for the space separator between words.
        addition = len(word) + (1 if current else 0)

        if current and current_len + addition > chunk_size:
            chunks.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += addition

    # Flush any remaining words.
    if current:
        chunks.append(" ".join(current))

    return chunks if chunks else [""]
