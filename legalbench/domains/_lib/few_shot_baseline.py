#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["datasets>=2.14", "anthropic>=0.40", "openai>=1.0", "requests>=2.28"]
# ///
"""Frontier-LLM baseline using the upstream LegalBench `base_prompt.txt`
for any task — the same few-shot prompt the published baselines used.

Why this file exists: my earlier one-shot rule_description-style prompt
caused models to hedge with chain-of-thought instead of leading with
Yes/No, hitting the max_tokens cap, and parse-erroring. The upstream
`base_prompt.txt` provides 5–6 worked Q/A examples that prime the model
to answer directly. This is the canonical prompt format LegalBench
results have been reported against.

Usage:
    ANTHROPIC_API_KEY=... \\
        uv run domains/_lib/few_shot_baseline.py \\
            --task diversity_2 \\
            --model claude-sonnet-4-6 \\
            --output domains/legalbench-diversity-2/results/llm_sonnet.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests
from datasets import load_dataset


REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPT_CACHE = REPO_ROOT / ".legalbench_prompts"


def fetch_base_prompt(task: str) -> str:
    """Get the upstream base_prompt.txt for `task`. Cached on disk."""
    PROMPT_CACHE.mkdir(parents=True, exist_ok=True)
    local = PROMPT_CACHE / f"{task}_base_prompt.txt"
    if local.exists():
        return local.read_text()
    url = f"https://raw.githubusercontent.com/HazyResearch/legalbench/main/tasks/{task}/base_prompt.txt"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    local.write_text(resp.text)
    return resp.text


def build_prompt(template: str, text: str) -> str:
    return template.replace("{{text}}", text)


# ---------------------------------------------------------------------------
# Model dispatch + caching
# ---------------------------------------------------------------------------


_ANTHROPIC_PREFIXES = ("claude-",)


def _is_anthropic(model: str) -> bool:
    return any(model.startswith(p) for p in _ANTHROPIC_PREFIXES)


def _cache_key(model: str, prompt: str) -> str:
    return f"{model}__{hashlib.sha256(prompt.encode()).hexdigest()[:16]}"


def ask_model(model: str, prompt: str, *, cache_dir: Path, max_tokens: int = 256) -> str:
    """Send `prompt` to `model`. Stops on `Q:` so the model can't run into a
    new question. Cached on disk by (model, prompt_hash). Modern reasoning
    models tend to write a brief chain-of-thought and conclude with the
    answer, so we let them and parse the conclusion."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    cp = cache_dir / f"{_cache_key(model, prompt)}.txt"
    if cp.exists():
        return cp.read_text()
    try:
        if _is_anthropic(model):
            import anthropic
            c = anthropic.Anthropic()
            r = c.messages.create(
                model=model, max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
                stop_sequences=["\n\nQ:", "\nQ:"],
            )
            raw = r.content[0].text if r.content else ""
        else:
            from openai import OpenAI
            c = OpenAI()
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stop": ["\n\nQ:", "\nQ:"],
            }
            if model.startswith(("gpt-5", "o3", "o4")):
                kwargs["max_completion_tokens"] = max_tokens
                kwargs.pop("stop", None)
            else:
                kwargs["max_tokens"] = max_tokens
                kwargs["temperature"] = 0
            r = c.chat.completions.create(**kwargs)
            raw = r.choices[0].message.content or ""
    except Exception as e:
        return f"__error__:{type(e).__name__}: {str(e)[:120]}"
    cp.write_text(raw)
    return raw


_FINAL_ANS_RE = re.compile(
    r"(?:answer|conclusion|therefore|so[\s,]|thus[\s,]|the answer is)[^.\n]{0,40}\b(yes|no)\b",
    re.IGNORECASE,
)
_BARE_RE = re.compile(r"\b(yes|no)\b", re.IGNORECASE)


def parse_yes_no(raw: str) -> str | None:
    """Extract Yes/No from the model's response. Prefer a final-answer
    cue ('therefore Yes', 'the answer is No', etc.); fall back to the last
    bare Yes/No token in the response."""
    text = raw.strip()
    if not text:
        return None
    # Look at the last 200 chars where the conclusion lives
    tail = text[-300:]
    m = list(_FINAL_ANS_RE.finditer(tail))
    if m:
        return m[-1].group(1).lower()
    # If the response leads with Yes/No (few-shot worked as designed)
    head = text[:30].lower()
    if re.match(r"\s*yes\b", head):
        return "yes"
    if re.match(r"\s*no\b", head):
        return "no"
    # Last resort: last bare Yes/No anywhere
    bares = list(_BARE_RE.finditer(text))
    if bares:
        return bares[-1].group(1).lower()
    return None


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--task", required=True, help="LegalBench task slug (e.g. diversity_2, hearsay)")
    p.add_argument("--model", required=True)
    p.add_argument("--limit", type=int)
    p.add_argument("--split", default="test", choices=["train", "test"])
    p.add_argument("--max-tokens", type=int, default=256,
                   help="Cap LLM output. Modern reasoning models like to write a short chain-of-thought before concluding; 256 is enough headroom.")
    p.add_argument("--output", type=Path)
    p.add_argument("--cache-dir", type=Path,
                   default=REPO_ROOT / ".llm_cache")
    args = p.parse_args()

    template = fetch_base_prompt(args.task)
    rows = load_dataset("nguha/legalbench", args.task)[args.split]
    if args.limit:
        rows = rows.select(range(min(args.limit, len(rows))))

    print(f"LLM baseline: {args.task}/{args.split}, N={len(rows)}, "
          f"model={args.model}, prompt=upstream base_prompt.txt", file=sys.stderr)

    correct = parse_err = api_err = 0
    by_slice: dict[str, dict[str, int]] = {}
    per_case: list[dict[str, Any]] = []
    started = time.time()
    for i, row in enumerate(rows, 1):
        text = row["text"]
        sl = row.get("slice", "")
        expected = row["answer"].strip().lower()
        prompt = build_prompt(template, text)
        raw = ask_model(args.model, prompt, cache_dir=args.cache_dir,
                        max_tokens=args.max_tokens)
        if raw.startswith("__error__:"):
            api_err += 1
            per_case.append({"index": row["index"], "slice": sl,
                              "expected": expected, "status": raw})
            continue
        ans = parse_yes_no(raw)
        if ans is None:
            parse_err += 1
            per_case.append({"index": row["index"], "slice": sl,
                              "expected": expected, "status": "parse_err",
                              "raw": raw[:80]})
            continue
        ok = ans == expected
        correct += int(ok)
        per_case.append({"index": row["index"], "slice": sl,
                          "expected": expected, "answer": ans,
                          "correct": ok})
        if sl:
            b = by_slice.setdefault(sl, {"correct": 0, "total": 0})
            b["total"] += 1
            if ok:
                b["correct"] += 1
        if i % 50 == 0:
            elapsed = time.time() - started
            rate = i / elapsed if elapsed > 0 else 0
            print(f"  [{i:>4}/{len(rows)}] {correct}/{i} correct "
                  f"({rate:.1f}/s)", file=sys.stderr)

    total = len(rows)
    acc = (100 * correct / total) if total else 0
    print(f"\n{args.model} on {args.task}: {correct}/{total} ({acc:.1f}%)  "
          f"parse_err={parse_err}, api_err={api_err}", file=sys.stderr)
    if by_slice:
        print("\n  by slice:", file=sys.stderr)
        for s in sorted(by_slice):
            b = by_slice[s]
            sa = (100 * b["correct"] / b["total"]) if b["total"] else 0
            print(f"    {s:<35}  {b['correct']:>3}/{b['total']:<3}  ({sa:>5.1f}%)",
                  file=sys.stderr)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({
            "task": args.task, "split": args.split, "model": args.model,
            "prompt_format": "upstream_base_prompt",
            "summary": {"correct": correct, "total": total,
                         "parse_err": parse_err, "api_err": api_err},
            "by_slice": by_slice,
            "per_case": per_case,
        }, indent=2))
        print(f"Wrote {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
