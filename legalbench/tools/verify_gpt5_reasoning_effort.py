#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["openai>=1.50", "pyyaml>=6.0"]
# ///
"""Verify GPT-5.4 reasoning_effort behaviour with explicit instrumentation.

The v3.7/v3.8 paper claims GPT-5.4 at `reasoning_effort=low` scores
7/11 on the construction-CAR exception-chain subset. The committed
LLM-comparison harness (`benchmarks/run_llm_comparison.py`) does NOT
pass `reasoning_effort` as an API parameter — there is no committed
script that produced the claimed result. The paper has a precedent
(v3.5 → v3.6 token-budget bug) where a low score was a harness
artefact, not a real model finding.

This script runs a minimal, fully-logged test on a small sample of
construction-CAR scenarios with both default and `reasoning_effort=low`,
recording for each call:
  - Raw response content (str)
  - Response length (chars)
  - Token usage (completion_tokens, completion_tokens_details if
    available — particularly reasoning_tokens)
  - Whether the response parses as an eligibility verdict
  - finish_reason from the API

The answer: are GPT-5.4 low-reasoning outputs empty/truncated (harness
artefact), or are they sensible content that just gets the answer wrong
(real model finding)?

Usage:
    OPENAI_API_KEY=... uv run tools/verify_gpt5_reasoning_effort.py \
        --scenarios-yaml /path/to/construction-all-risks/scenarios.yaml \
        --source-md /path/to/construction-all-risks/source.md \
        --n 6 \
        --output verify_gpt5_reasoning.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import yaml
from openai import OpenAI


def build_prompt(source_text: str, scenario: dict) -> str:
    """Single-shot eligibility prompt — exact replica of the committed
    LLM-comparison harness's `_build_prompt` (see
    `confidently-wrong-benchmark/benchmarks/run_llm_comparison.py`).
    Same prompt the paper's published GPT-5.4 numbers were produced
    against, so re-runs with this script are directly comparable to
    the paper's tables."""
    fields = scenario.get("inputs", {}) or scenario.get("fields", {}) or {}
    facts = []
    for field, value in fields.items():
        short = field.split(".")[-1].replace("_", " ")
        if isinstance(value, bool):
            facts.append(f"- {short}: {'yes' if value else 'no'}")
        else:
            facts.append(f"- {short}: {value}")
    facts_text = "\n".join(facts)
    return (
        "You are evaluating eligibility based on the following regulation.\n\n"
        f"--- REGULATION ---\n{source_text}\n--- END REGULATION ---\n\n"
        f"Given these facts:\n{facts_text}\n\n"
        "Based ONLY on the regulation above, is the applicant eligible?\n"
        "Answer with exactly one word: eligible, not_eligible, or undetermined.\n"
        "Do not explain. Just the answer."
    )


def call_gpt5(client: OpenAI, model: str, prompt: str, *,
              reasoning_effort: str | None = None,
              max_completion_tokens: int = 2000) -> dict:
    """Make a single API call and capture everything we can log."""
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_completion_tokens": max_completion_tokens,
    }
    if reasoning_effort is not None:
        kwargs["reasoning_effort"] = reasoning_effort

    started = time.time()
    try:
        r = client.chat.completions.create(**kwargs)
    except Exception as e:
        return {
            "error": f"{type(e).__name__}: {str(e)[:300]}",
            "elapsed_s": time.time() - started,
        }
    elapsed = time.time() - started

    choice = r.choices[0]
    content = choice.message.content or ""
    finish_reason = choice.finish_reason

    usage = r.usage
    usage_dict: dict[str, Any] = {
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }
    # Reasoning models surface reasoning_tokens via completion_tokens_details
    ctd = getattr(usage, "completion_tokens_details", None)
    if ctd is not None:
        usage_dict["reasoning_tokens"] = getattr(ctd, "reasoning_tokens", None)
        usage_dict["accepted_prediction_tokens"] = getattr(ctd, "accepted_prediction_tokens", None)

    return {
        "content": content,
        "content_length": len(content),
        "finish_reason": finish_reason,
        "usage": usage_dict,
        "elapsed_s": elapsed,
    }


def parse_answer(content: str) -> str:
    c = (content or "").strip().lower()
    for label in ("not_eligible", "eligible", "undetermined"):
        if label in c:
            return label
    return "parse_error"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--scenarios-yaml", type=Path, required=True)
    p.add_argument("--source-md", type=Path, required=True)
    p.add_argument("--model", default="gpt-5.4")
    p.add_argument("--n", type=int, default=6,
                   help="Number of scenarios to test from the file")
    p.add_argument("--names", nargs="+", default=None,
                   help="Test only these scenario names (overrides --n)")
    p.add_argument("--modes", nargs="+", default=["default", "low"],
                   choices=["default", "low"],
                   help="Which reasoning-effort modes to call. Default: both.")
    p.add_argument("--output", type=Path)
    a = p.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set in environment.", file=sys.stderr)
        return 2

    raw = yaml.safe_load(a.scenarios_yaml.read_text())
    if isinstance(raw, dict) and "tests" in raw:
        scenarios = raw["tests"]
    elif isinstance(raw, list):
        scenarios = raw
    else:
        print("ERROR: scenarios.yaml: expected list or dict with 'tests' key",
              file=sys.stderr)
        return 2
    if a.names:
        by_name = {s.get("name"): s for s in scenarios}
        sample = [by_name[n] for n in a.names if n in by_name]
        missing = [n for n in a.names if n not in by_name]
        if missing:
            print(f"WARN: not found in scenarios.yaml: {missing}", file=sys.stderr)
    else:
        sample = scenarios[: a.n]
    source_text = a.source_md.read_text()

    client = OpenAI()
    results = []
    print(f"Verifying {a.model} reasoning_effort behaviour on {len(sample)} scenarios.",
          file=sys.stderr)
    print(f"For each scenario: 2 calls (default + reasoning_effort=low).",
          file=sys.stderr)

    for i, scen in enumerate(sample):
        name = scen.get("name", f"scenario_{i}")
        expected = (scen.get("expect") or {}).get("outcome") \
                   or scen.get("expected") \
                   or scen.get("outcome") \
                   or scen.get("answer")
        prompt = build_prompt(source_text, scen)

        print(f"\n[{i+1}/{len(sample)}] {name} (expected={expected})", file=sys.stderr)
        row: dict[str, Any] = {"scenario": name, "expected": expected}

        if "default" in a.modes:
            r_default = call_gpt5(client, a.model, prompt)
            ans_default = parse_answer(r_default.get("content", "")) if "error" not in r_default else "API_ERROR"
            ok = "✓" if ans_default == expected else "✗"
            print(f"  default     : {ok} answer={ans_default}, len={r_default.get('content_length', '?')}, "
                  f"finish={r_default.get('finish_reason', '?')}, "
                  f"tokens={r_default.get('usage', {}).get('completion_tokens', '?')} "
                  f"(reasoning={r_default.get('usage', {}).get('reasoning_tokens', '?')})",
                  file=sys.stderr)
            row["default"] = {"answer": ans_default, **r_default}

        if "low" in a.modes:
            r_low = call_gpt5(client, a.model, prompt, reasoning_effort="low")
            ans_low = parse_answer(r_low.get("content", "")) if "error" not in r_low else "API_ERROR"
            ok = "✓" if ans_low == expected else "✗"
            print(f"  low         : {ok} answer={ans_low}, len={r_low.get('content_length', '?')}, "
                  f"finish={r_low.get('finish_reason', '?')}, "
                  f"tokens={r_low.get('usage', {}).get('completion_tokens', '?')} "
                  f"(reasoning={r_low.get('usage', {}).get('reasoning_tokens', '?')})",
                  file=sys.stderr)
            row["low_reasoning"] = {"answer": ans_low, **r_low}

        results.append(row)

    # Summary
    print("\n=== Summary ===", file=sys.stderr)
    summary: dict[str, Any] = {}
    for mode_key, label in [("default", "default"), ("low_reasoning", "low")]:
        if not any(mode_key in r for r in results):
            continue
        correct = sum(1 for r in results if r.get(mode_key, {}).get("answer") == r["expected"])
        empty = sum(1 for r in results if r.get(mode_key, {}).get("content_length", 0) == 0)
        truncated = sum(1 for r in results if r.get(mode_key, {}).get("finish_reason") == "length")
        parse_err = sum(1 for r in results if r.get(mode_key, {}).get("answer") == "parse_error")
        wrong = [r["scenario"] for r in results
                 if r.get(mode_key, {}).get("answer") not in (r["expected"], None)]
        print(f"  {label:<12}: correct {correct}/{len(results)}, "
              f"empty={empty}, finish=length={truncated}, parse_err={parse_err}",
              file=sys.stderr)
        if wrong:
            print(f"               wrong on: {', '.join(wrong)}", file=sys.stderr)
        summary[label] = {
            "correct": correct, "empty": empty, "truncated": truncated,
            "parse_err": parse_err, "wrong_scenarios": wrong,
        }

    if a.output:
        a.output.write_text(json.dumps({
            "model": a.model,
            "n": len(results),
            "modes": a.modes,
            "summary": summary,
            "per_scenario": results,
        }, indent=2, default=str))
        print(f"\nWrote {a.output}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
