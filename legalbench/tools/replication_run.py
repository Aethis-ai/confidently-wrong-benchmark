#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["openai>=1.50", "anthropic>=0.40", "pyyaml>=6.0"]
# ///
"""General-purpose replication harness for v3.6 / v3.7 paper cells.

Replicates the paper's published LLM-comparison results against a
specified model + scenario set, using the **same prompt format** as
the committed `confidently-wrong-benchmark/benchmarks/run_llm_comparison.py`.
For OpenAI reasoning models (`gpt-5*`, `o*`), optionally passes
`reasoning_effort`. For Anthropic models, uses the chat completion
API with `max_tokens` matching the committed harness.

Logs per call:
  - Raw response content
  - Content length
  - finish_reason / stop_reason
  - Token usage (completion / output, plus reasoning_tokens for
    OpenAI reasoning models)
  - Elapsed seconds

Output JSON schema is identical to verify_gpt5_reasoning_effort.py
so the replication-summary aggregator can consume both.

Usage:
    OPENAI_API_KEY=... ANTHROPIC_API_KEY=... \\
        uv run tools/replication_run.py \\
            --scenarios-yaml /path/to/scenarios.yaml \\
            --source-md     /path/to/source.md \\
            --model claude-opus-4-6 \\
            --output docs/replication_opus_4_6_construction.json

    # GPT-5 reasoning models, with low reasoning effort:
    --model gpt-5.4 --reasoning-effort low

    # Filter to specific scenario names:
    --names access_500m_design_pioneer_covered ...

    # Filter by tag (e.g. only the 11 exception_chain ones):
    --tag exception_chain
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


def build_paper_prompt(source_text: str, scenario: dict) -> str:
    """Exact replica of `_build_prompt` from
    confidently-wrong-benchmark/benchmarks/run_llm_comparison.py.
    Preserved verbatim so re-runs are directly comparable to paper
    figures."""
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


_OPENAI_REASONING_PREFIXES = ("gpt-5", "o3", "o4")
_ANTHROPIC_PREFIXES = ("claude-",)


def is_openai_reasoning(model: str) -> bool:
    return any(model.startswith(p) for p in _OPENAI_REASONING_PREFIXES)


def is_anthropic(model: str) -> bool:
    return any(model.startswith(p) for p in _ANTHROPIC_PREFIXES)


def call_anthropic(model: str, prompt: str, max_tokens: int = 50) -> dict:
    import anthropic
    started = time.time()
    try:
        c = anthropic.Anthropic()
        r = c.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        return {
            "error": f"{type(e).__name__}: {str(e)[:300]}",
            "elapsed_s": time.time() - started,
        }
    elapsed = time.time() - started
    content = r.content[0].text if r.content else ""
    return {
        "content": content,
        "content_length": len(content),
        "finish_reason": getattr(r, "stop_reason", None),
        "usage": {
            "prompt_tokens": getattr(r.usage, "input_tokens", None),
            "completion_tokens": getattr(r.usage, "output_tokens", None),
            "total_tokens": (
                (getattr(r.usage, "input_tokens", 0) or 0)
                + (getattr(r.usage, "output_tokens", 0) or 0)
            ),
        },
        "elapsed_s": elapsed,
    }


def call_openai(model: str, prompt: str, *,
                reasoning_effort: str | None = None,
                max_tokens: int = 50,
                max_completion_tokens: int = 2000) -> dict:
    from openai import OpenAI
    c = OpenAI()
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    if is_openai_reasoning(model):
        kwargs["max_completion_tokens"] = max_completion_tokens
        if reasoning_effort is not None:
            kwargs["reasoning_effort"] = reasoning_effort
    else:
        kwargs["max_tokens"] = max_tokens
        kwargs["temperature"] = 0

    started = time.time()
    try:
        r = c.chat.completions.create(**kwargs)
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
    ctd = getattr(usage, "completion_tokens_details", None)
    if ctd is not None:
        usage_dict["reasoning_tokens"] = getattr(ctd, "reasoning_tokens", None)

    return {
        "content": content,
        "content_length": len(content),
        "finish_reason": finish_reason,
        "usage": usage_dict,
        "elapsed_s": elapsed,
    }


def call_model(model: str, prompt: str, *,
               reasoning_effort: str | None = None) -> dict:
    if is_anthropic(model):
        return call_anthropic(model, prompt)
    return call_openai(model, prompt, reasoning_effort=reasoning_effort)


def parse_answer(content: str) -> str:
    c = (content or "").strip().lower()
    for label in ("not_eligible", "eligible", "undetermined"):
        if label in c:
            return label
    return "parse_error"


def load_scenarios(path: Path,
                   names: list[str] | None,
                   tag: str | None,
                   n: int | None) -> list[dict]:
    raw = yaml.safe_load(path.read_text())
    if isinstance(raw, dict) and "tests" in raw:
        scenarios = raw["tests"]
    elif isinstance(raw, list):
        scenarios = raw
    else:
        raise ValueError("scenarios.yaml: expected list or dict-with-tests")

    if names:
        by_name = {s.get("name"): s for s in scenarios}
        sel = [by_name[n] for n in names if n in by_name]
        missing = [n for n in names if n not in by_name]
        if missing:
            print(f"WARN: not found in scenarios.yaml: {missing}", file=sys.stderr)
        return sel
    if tag:
        sel = [s for s in scenarios if tag in (s.get("tags") or [])]
        return sel
    if n:
        return scenarios[:n]
    return scenarios


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--scenarios-yaml", type=Path, required=True)
    p.add_argument("--source-md", type=Path, required=True)
    p.add_argument("--model", required=True,
                   help="e.g. gpt-5.4, gpt-5.3, gpt-4.1-mini, "
                        "claude-opus-4-6, claude-opus-4-7, claude-sonnet-4-6")
    p.add_argument("--reasoning-effort", default=None,
                   choices=[None, "low", "medium", "high"],
                   help="Pass to OpenAI reasoning models; ignored for Anthropic")
    p.add_argument("--n", type=int, default=None)
    p.add_argument("--names", nargs="+", default=None)
    p.add_argument("--tag", default=None,
                   help="Filter to scenarios with this tag (e.g. exception_chain)")
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()

    if is_anthropic(a.model) and not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr); return 2
    if (not is_anthropic(a.model)) and not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY not set", file=sys.stderr); return 2

    scenarios = load_scenarios(a.scenarios_yaml, a.names, a.tag, a.n)
    if not scenarios:
        print("ERROR: no scenarios selected", file=sys.stderr); return 2

    source_text = a.source_md.read_text()
    re_label = (f"reasoning_effort={a.reasoning_effort}"
                if a.reasoning_effort else "default")
    print(f"replication: {a.model} ({re_label}) on {len(scenarios)} scenarios "
          f"using paper-prompt format", file=sys.stderr)

    results = []
    started = time.time()
    for i, scen in enumerate(scenarios):
        name = scen.get("name", f"scenario_{i}")
        expected = ((scen.get("expect") or {}).get("outcome")
                    or scen.get("expected") or scen.get("outcome")
                    or scen.get("answer"))
        prompt = build_paper_prompt(source_text, scen)
        r = call_model(a.model, prompt, reasoning_effort=a.reasoning_effort)
        ans = (parse_answer(r.get("content", ""))
               if "error" not in r else "API_ERROR")
        ok = "✓" if ans == expected else "✗"
        usage = r.get("usage", {})
        print(f"  [{i+1:>3}/{len(scenarios)}] {ok} {name:<50} "
              f"exp={expected:<13} got={ans:<13} "
              f"len={r.get('content_length', '?')} "
              f"finish={r.get('finish_reason', '?')} "
              f"tok={usage.get('completion_tokens', '?')}",
              file=sys.stderr)
        results.append({
            "scenario": name,
            "expected": expected,
            "answer": ans,
            **r,
        })

    elapsed_total = time.time() - started
    correct = sum(1 for r in results if r["answer"] == r["expected"])
    empty = sum(1 for r in results if r.get("content_length", 0) == 0)
    truncated = sum(1 for r in results if r.get("finish_reason") in ("length", "max_tokens"))
    parse_err = sum(1 for r in results if r["answer"] == "parse_error")
    api_err = sum(1 for r in results if r["answer"] == "API_ERROR")
    wrong_names = [r["scenario"] for r in results
                   if r["answer"] not in (r["expected"], "parse_error", "API_ERROR")]

    print(f"\n=== {a.model} ({re_label}) summary ===", file=sys.stderr)
    print(f"  correct      : {correct}/{len(results)}  ({100*correct/len(results):.1f}%)",
          file=sys.stderr)
    print(f"  empty        : {empty}", file=sys.stderr)
    print(f"  truncated    : {truncated}", file=sys.stderr)
    print(f"  parse_err    : {parse_err}", file=sys.stderr)
    print(f"  api_err      : {api_err}", file=sys.stderr)
    print(f"  elapsed      : {elapsed_total:.1f}s", file=sys.stderr)
    if wrong_names:
        print(f"  wrong on     : {wrong_names}", file=sys.stderr)

    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps({
        "model": a.model,
        "reasoning_effort": a.reasoning_effort,
        "scenarios_yaml": str(a.scenarios_yaml),
        "n": len(results),
        "summary": {
            "correct": correct, "empty": empty, "truncated": truncated,
            "parse_err": parse_err, "api_err": api_err,
            "elapsed_s": elapsed_total, "wrong_scenarios": wrong_names,
        },
        "per_scenario": results,
    }, indent=2, default=str))
    print(f"\nWrote {a.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
