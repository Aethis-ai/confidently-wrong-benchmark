#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["datasets>=2.14", "anthropic>=0.40"]
# ///
"""Frontier-LLM baseline for LegalBench `hearsay`.

Asks the same model the engine pipeline used as its extractor to answer
Yes/No directly, given the rule and the fact-pattern. Same cache layout.

This is the head-to-head: solo LLM vs (LLM extractor + Aethis engine).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from datasets import load_dataset


HERE = Path(__file__).parent
TASK = "hearsay"
RULE_TEXT = (HERE / "sources/rule.md").read_text()


_PROMPT = """You are an expert on the Federal Rules of Evidence. Read the rule below, then read the fact-pattern. Decide whether the fact-pattern, if offered as described, is hearsay under FRE 801(a)–(c).

--- RULE ---
{rule}
--- END RULE ---

Fact-pattern:
{fact}

Is the fact-pattern hearsay under FRE 801? Answer with exactly one word: Yes or No."""


def _cache_key(model: str, prompt: str) -> str:
    return f"{model}__{hashlib.sha256(prompt.encode()).hexdigest()[:16]}"


def ask(model: str, prompt: str, cache_dir: Path) -> str:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{_cache_key(model, prompt)}.txt"
    if cache_path.exists():
        return cache_path.read_text()
    import anthropic
    client = anthropic.Anthropic()
    try:
        resp = client.messages.create(
            model=model, max_tokens=16,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text if resp.content else ""
    except Exception as e:
        return f"__error__:{type(e).__name__}: {str(e)[:120]}"
    cache_path.write_text(raw)
    return raw


def parse_yes_no(raw: str) -> str | None:
    head = raw.strip().lower()[:60]
    if re.search(r"\byes\b", head):
        return "yes"
    if re.search(r"\bno\b", head):
        return "no"
    return None


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int)
    p.add_argument("--split", default="test", choices=["train", "test"])
    p.add_argument("--model", default="claude-sonnet-4-6")
    p.add_argument("--cache-dir", type=Path,
                   default=HERE / "results" / "llm_cache")
    p.add_argument("--output", type=Path)
    args = p.parse_args()

    rows = load_dataset("nguha/legalbench", TASK)[args.split]
    if args.limit:
        rows = rows.select(range(min(args.limit, len(rows))))

    print(f"LLM baseline: {TASK}/{args.split}, N={len(rows)}, "
          f"model={args.model}", file=sys.stderr)

    correct = parse_err = api_err = 0
    by_slice: dict[str, dict[str, int]] = {}
    per_case: list[dict] = []
    for i, row in enumerate(rows, 1):
        text = row["text"]
        sl = row["slice"]
        expected = row["answer"].strip().lower()
        prompt = _PROMPT.format(rule=RULE_TEXT, fact=text)
        raw = ask(args.model, prompt, args.cache_dir)
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
                          "correct": ok, "raw": raw[:80]})
        b = by_slice.setdefault(sl, {"correct": 0, "total": 0})
        b["total"] += 1
        if ok:
            b["correct"] += 1

    total = len(rows)
    acc = (100 * correct / total) if total else 0
    print(f"\n{args.model}: {correct}/{total} ({acc:.1f}%)  "
          f"parse_err={parse_err}, api_err={api_err}")

    if by_slice:
        print("\n  by slice:")
        for s in sorted(by_slice):
            b = by_slice[s]
            sa = (100 * b["correct"] / b["total"]) if b["total"] else 0
            print(f"    {s:<35}  {b['correct']:>2}/{b['total']:<2}  ({sa:>5.1f}%)")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({
            "task": TASK, "model": args.model,
            "summary": {"correct": correct, "total": total,
                         "parse_err": parse_err, "api_err": api_err},
            "by_slice": by_slice,
            "per_case": per_case,
        }, indent=2))
        print(f"Wrote {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
