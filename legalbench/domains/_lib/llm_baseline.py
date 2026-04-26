"""Shared frontier-LLM baseline helper.

Used by both `legalbench-diversity-*/run.py` and
`aethis-eligibility/run.py` to run a single LLM model on the same case
set the engine ran on, with disk caching keyed by (model, prompt_hash)
so re-runs are free.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


_ANTHROPIC_PREFIXES = ("claude-",)


def _is_anthropic(model: str) -> bool:
    return any(model.startswith(p) for p in _ANTHROPIC_PREFIXES)


def _cache_key(model: str, prompt: str) -> str:
    h = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
    return f"{model}__{h}"


def _ask_anthropic(model: str, prompt: str, max_tokens: int = 16) -> str:
    import anthropic
    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=model, max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text if resp.content else ""


def _ask_openai(model: str, prompt: str, max_tokens: int = 16) -> str:
    from openai import OpenAI
    client = OpenAI()
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    if model.startswith(("gpt-5", "o3", "o4")):
        kwargs["max_completion_tokens"] = 1024
    else:
        kwargs["max_tokens"] = max_tokens
        kwargs["temperature"] = 0
    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


def ask_llm(model: str, prompt: str, *, cache_dir: Path | None = None) -> str:
    """Ask `model` `prompt`; cache the raw text response on disk."""
    cache_path: Path | None = None
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / f"{_cache_key(model, prompt)}.txt"
        if cache_path.exists():
            return cache_path.read_text()
    try:
        raw = (_ask_anthropic if _is_anthropic(model) else _ask_openai)(model, prompt)
    except Exception as e:
        return f"__error__:{type(e).__name__}: {str(e)[:120]}"
    if cache_path is not None:
        cache_path.write_text(raw)
    return raw


# ---------------------------------------------------------------------------
# Yes/No parsing — for binary-classification tasks (LegalBench diversity_*).
# ---------------------------------------------------------------------------


def parse_yes_no(raw: str) -> str | None:
    r = raw.strip().lower()
    # Look at the first 30 chars — models tend to lead with the answer.
    head = r[:50]
    if re.search(r"\byes\b", head):
        return "yes"
    if re.search(r"\bno\b", head):
        return "no"
    return None


# ---------------------------------------------------------------------------
# Eligible / not_eligible / undetermined parsing — for Aethis-eligibility.
# ---------------------------------------------------------------------------


_ELIGIBILITY_RE = re.compile(
    r"\b(not[_\s]eligible|eligible|undetermined|insufficient[_\s]information)\b",
    re.IGNORECASE,
)


def parse_eligibility(raw: str) -> str | None:
    m = _ELIGIBILITY_RE.search(raw)
    if not m:
        return None
    val = m.group(1).lower().replace(" ", "_")
    if val in ("insufficient_information",):
        return "undetermined"
    return val
