#!/usr/bin/env python3
"""Render hackathon voiceover blocks with OpenAI TTS.

KISS utility:
- reads the prepared recording blocks file
- splits blocks by heading
- calls /v1/audio/speech with gpt-4o-mini-tts
- writes one mp3 per block into ./tts-output/

Requires:
- OPENAI_API_KEY in the local shell
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import httpx


DEFAULT_MODEL = "gpt-4o-mini-tts"
DEFAULT_VOICE = "alloy"
DEFAULT_INSTRUCTIONS = (
    "Male voice, relaxed and conversational, warm, low-energy but confident, "
    "slightly rough texture, mellow and easygoing, dry understated humor, "
    "natural American tone, slow-medium pace, human and unpolished, "
    "not announcer-like, not too dramatic, calm and casually intelligent."
)


def parse_blocks(text: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    current_title: str | None = None
    current_lines: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if re.fullmatch(r"BLOCK \d+|OPTIONAL MID-MONITOR INSERT", line.strip()):
            if current_title and current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    blocks.append((current_title, content))
            current_title = line.strip()
            current_lines = []
            continue
        if current_title is not None:
            current_lines.append(line)

    if current_title and current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            blocks.append((current_title, content))

    return blocks


def slugify(title: str) -> str:
    slug = title.lower().strip()
    slug = slug.replace("optional ", "")
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def render_block(
    *,
    client: httpx.Client,
    api_key: str,
    model: str,
    voice: str,
    instructions: str,
    text: str,
) -> bytes:
    response = client.post(
        "https://api.openai.com/v1/audio/speech",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "voice": voice,
            "input": text,
            "instructions": instructions,
            "format": "mp3",
        },
        timeout=120.0,
    )
    response.raise_for_status()
    return response.content


def main() -> int:
    parser = argparse.ArgumentParser(description="Render hackathon TTS audio blocks with OpenAI.")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("docs/hackathon-recording-voiceover-blocks.txt"),
        help="Path to the voiceover block file",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("tts-output"),
        help="Directory to write MP3 files into",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="TTS model to use")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help="OpenAI TTS voice name")
    parser.add_argument(
        "--instructions",
        default=DEFAULT_INSTRUCTIONS,
        help="Voice style instructions",
    )
    parser.add_argument(
        "--include-optional",
        action="store_true",
        help="Also render the optional mid-monitor insert block",
    )
    args = parser.parse_args()

    api_key = __import__("os").environ.get("OPENAI_API_KEY", "").strip()  # nosec
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required in your local shell.")

    if not args.input.is_file():
        raise SystemExit(f"Input file not found: {args.input}")

    blocks = parse_blocks(args.input.read_text(encoding="utf-8"))
    if not args.include_optional:
        blocks = [block for block in blocks if block[0] != "OPTIONAL MID-MONITOR INSERT"]

    if not blocks:
        raise SystemExit("No voiceover blocks found.")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    with httpx.Client() as client:
        for idx, (title, text) in enumerate(blocks, start=1):
            audio = render_block(
                client=client,
                api_key=api_key,
                model=args.model,
                voice=args.voice,
                instructions=args.instructions,
                text=text,
            )
            filename = f"{idx:02d}-{slugify(title)}.mp3"
            output_path = args.output_dir / filename
            output_path.write_bytes(audio)
            print(f"wrote {output_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
