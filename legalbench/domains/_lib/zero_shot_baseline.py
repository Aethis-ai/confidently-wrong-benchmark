#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["datasets>=2.14", "anthropic>=0.40", "openai>=1.0", "requests>=2.28"]
# ///
"""Zero-shot LLM baseline — task description + clause + Yes/No question.

Sibling of `few_shot_baseline.py`, used for B6 (§6.10.4) prompt-sensitivity
sanity check. Where `few_shot_baseline.py` uses the upstream LegalBench
`base_prompt.txt` (5–6 worked Q/A examples), this variant strips the
examples entirely and gives the model only:

  1. The verbatim task description from `domains/<task>/sources/rule.md`.
  2. The clause / fact pattern.
  3. A trailing "Answer Yes or No." instruction.

§6.10.4 of the v3.8 paper notes that GPT-5.4 has a systematic positive-class
bias on five LegalBench classification-style few-shot prompts (returns "yes"
on 304/308 cases of cuad_covenant_not_to_sue regardless of clause content).
The §6.10.4 framing — "prompt-format-coupled, not capability claim" — is
defensive and untested. This script tests it.

Output is the same JSON schema as `few_shot_baseline.py` so
`tools/significance.py` can ingest it via the same path.

Usage:
    OPENAI_API_KEY=... \\
        uv run domains/_lib/zero_shot_baseline.py \\
            --task cuad_covenant_not_to_sue \\
            --model gpt-5.4 \\
            --output domains/legalbench-cuad-covenant-not-to-sue/results/llm_gpt_5_4_zero_shot.json
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

from datasets import load_dataset


REPO_ROOT = Path(__file__).resolve().parents[2]


# Reuse the cache + dispatch + parser from few_shot_baseline.
sys.path.insert(0, str(Path(__file__).parent))
from few_shot_baseline import ask_model, parse_yes_no  # noqa: E402


def domain_for_task(task: str) -> Path:
    """Return the canonical domain dir for a LegalBench task slug."""
    slug = task.replace("_", "-")
    candidate = REPO_ROOT / "domains" / f"legalbench-{slug}"
    if candidate.exists():
        return candidate
    raise FileNotFoundError(
        f"No domain dir for task {task!r}; expected {candidate}")


def task_description(task: str) -> str:
    """Pull the rule.md task description for the zero-shot prompt."""
    domain = domain_for_task(task)
    rule_md = domain / "sources" / "rule.md"
    if not rule_md.exists():
        raise FileNotFoundError(f"Missing {rule_md}")
    return rule_md.read_text()


def build_zero_shot_prompt(rule_text: str, clause: str, question: str) -> str:
    """Construct the zero-shot prompt: rule + clause + Yes/No instruction."""
    return f"""{rule_text}

---

Clause to classify:

{clause}

---

{question}

Answer with a single word: Yes or No."""


# Per-task classification question (matches the upstream base_prompt.txt
# question for fair comparison — the only thing we strip is the few-shot
# Q/A examples).
TASK_QUESTIONS: dict[str, str] = {
    "cuad_covenant_not_to_sue":
        "Does the clause contain a covenant not to sue?",
}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--task", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--limit", type=int)
    p.add_argument("--split", default="test", choices=["train", "test"])
    p.add_argument("--max-tokens", type=int, default=256)
    p.add_argument("--output", type=Path)
    p.add_argument("--cache-dir", type=Path,
                   default=REPO_ROOT / ".llm_cache")
    args = p.parse_args()

    if args.task not in TASK_QUESTIONS:
        print(f"ERROR: no zero-shot question registered for task {args.task!r}. "
              f"Add it to TASK_QUESTIONS in zero_shot_baseline.py.",
              file=sys.stderr)
        return 2

    rule_text = task_description(args.task)
    question = TASK_QUESTIONS[args.task]
    rows = load_dataset("nguha/legalbench", args.task)[args.split]
    if args.limit:
        rows = rows.select(range(min(args.limit, len(rows))))

    print(f"Zero-shot LLM baseline: {args.task}/{args.split}, N={len(rows)}, "
          f"model={args.model}, prompt=zero_shot (rule + clause + question)",
          file=sys.stderr)

    correct = parse_err = api_err = 0
    yes_count = no_count = 0
    per_case: list[dict[str, Any]] = []
    started = time.time()
    for i, row in enumerate(rows, 1):
        text = row["text"]
        expected = row["answer"].strip().lower()
        prompt = build_zero_shot_prompt(rule_text, text, question)
        raw = ask_model(args.model, prompt, cache_dir=args.cache_dir,
                        max_tokens=args.max_tokens)
        if raw.startswith("__error__:"):
            api_err += 1
            per_case.append({"index": row["index"], "expected": expected,
                              "status": raw})
            continue
        ans = parse_yes_no(raw)
        if ans is None:
            parse_err += 1
            per_case.append({"index": row["index"], "expected": expected,
                              "status": "parse_err", "raw": raw[:80]})
            continue
        ok = ans == expected
        correct += int(ok)
        if ans == "yes":
            yes_count += 1
        else:
            no_count += 1
        per_case.append({"index": row["index"], "expected": expected,
                          "answer": ans, "correct": ok})
        if i % 50 == 0:
            elapsed = time.time() - started
            rate = i / elapsed if elapsed > 0 else 0
            print(f"  [{i:>4}/{len(rows)}] {correct}/{i} correct "
                  f"(yes={yes_count}, no={no_count}, {rate:.1f}/s)",
                  file=sys.stderr)

    total = len(rows)
    acc = (100 * correct / total) if total else 0
    print(f"\n{args.model} on {args.task} (ZERO-SHOT): "
          f"{correct}/{total} ({acc:.1f}%)  "
          f"parse_err={parse_err}, api_err={api_err}, "
          f"yes={yes_count}/{total}, no={no_count}/{total}",
          file=sys.stderr)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({
            "task": args.task, "split": args.split, "model": args.model,
            "prompt_format": "zero_shot",
            "prompt_question": question,
            "summary": {"correct": correct, "total": total,
                         "parse_err": parse_err, "api_err": api_err,
                         "yes_count": yes_count, "no_count": no_count},
            "per_case": per_case,
        }, indent=2))
        print(f"Wrote {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
