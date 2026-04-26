#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["datasets>=2.14", "anthropic>=0.40", "openai>=1.0"]
# ///
"""LLM baseline for LegalBench diversity_* — runs a single model across
one of the six splits with prompt caching on disk.

The prompt loads the verbatim canonical rule prose from each task's
`sources/rule.md` (the same upstream LegalBench Task description the
engine bundle was authored from), so the engine and LLM-only paths see
identical rule text. Fact-pattern comes from the LegalBench test set.

Usage:
    ANTHROPIC_API_KEY=... \\
        uv run domains/_lib/diversity_llm.py \\
            --task diversity_1 --model claude-sonnet-4-6 \\
            --output domains/legalbench-diversity-1/results/llm_sonnet.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from datasets import load_dataset

# Make sibling imports work whether invoked via `uv run path/to/file.py`
# or as a module.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from llm_baseline import ask_llm, parse_yes_no  # noqa: E402


_PROMPT_TEMPLATE = """{rule}

Facts: {text}

Does this court have diversity jurisdiction? Answer with exactly one word: Yes or No."""


def _load_canonical_rule(task: str) -> str:
    """Load the verbatim LegalBench Task description for the given task,
    from the project's sources/rule.md."""
    n = task.split("_")[-1]
    rule_path = (Path(__file__).resolve().parents[1]
                 / f"legalbench-diversity-{n}" / "sources" / "rule.md")
    return rule_path.read_text()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--task", required=True, help="diversity_1 .. diversity_6")
    p.add_argument("--model", default="claude-sonnet-4-6")
    p.add_argument("--limit", type=int)
    p.add_argument("--split", default="test", choices=["train", "test"])
    p.add_argument("--output", type=Path)
    p.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / ".llm_cache",
    )
    args = p.parse_args()

    rule = _load_canonical_rule(args.task)
    rows = load_dataset("nguha/legalbench", args.task)[args.split]
    if args.limit:
        rows = rows.select(range(min(args.limit, len(rows))))

    print(f"LLM baseline: {args.task}/{args.split}, N={len(rows)}, "
          f"model={args.model}", file=sys.stderr)

    correct = parse_err = api_err = 0
    per_case: list[dict[str, Any]] = []
    for i, row in enumerate(rows, 1):
        text = row["text"]
        expected = row["answer"].strip().lower()  # "yes" or "no"
        prompt = _PROMPT_TEMPLATE.format(rule=rule, text=text)
        raw = ask_llm(args.model, prompt, cache_dir=args.cache_dir)
        if raw.startswith("__error__:"):
            api_err += 1
            per_case.append({"index": row["index"], "expected": expected,
                              "status": raw, "raw": raw})
            print(f"  [{i:>4}] API_ERR  {raw[:80]}")
            continue
        ans = parse_yes_no(raw)
        if ans is None:
            parse_err += 1
            per_case.append({"index": row["index"], "expected": expected,
                              "status": "parse_err", "raw": raw[:80]})
            print(f"  [{i:>4}] PARSE_ERR  {raw[:60]!r}")
            continue
        ok = ans == expected
        correct += int(ok)
        per_case.append({"index": row["index"], "expected": expected,
                          "answer": ans, "correct": ok, "raw": raw[:80]})
        if i % 50 == 0:
            print(f"  [{i:>4}/{len(rows)}] running… {correct}/{i}", file=sys.stderr)

    total = len(rows)
    acc = (100 * correct / total) if total else 0.0
    print(f"\n{args.model} on {args.task}: {correct}/{total} ({acc:.1f}%)  "
          f"parse_err={parse_err}, api_err={api_err}", file=sys.stderr)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({
            "task": args.task, "split": args.split, "model": args.model,
            "summary": {"correct": correct, "total": total,
                         "parse_err": parse_err, "api_err": api_err},
            "per_case": per_case,
        }, indent=2))
        print(f"Wrote {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
