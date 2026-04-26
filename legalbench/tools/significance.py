#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6.0", "datasets>=2.14"]
# ///
"""Statistical hardening — Wilson CIs and McNemar's per-task,
combined paired-binomial across tasks. No external stats deps; pure
math. Output is a markdown report ready to drop into the paper.

Reads result JSON files (engine + per-model LLM baseline JSON) for
each task, computes:
  - Wilson 95% CI on each accuracy
  - McNemar's exact (binomial) test on engine-vs-LLM per-case
    agreement, per task
  - Cohen's h effect size on accuracy difference
  - Combined paired-binomial on engine-wins-LLM-loses cases across
    multiple tasks

Usage:
    uv run tools/significance.py --tasks docs/significance_tasks.yaml \\
        --output docs/statistical-summary.md
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]


def wilson_ci(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """Wilson 95% CI for a binomial proportion. z=1.959963984... gives 95%."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def cohen_h(p1: float, p2: float) -> float:
    """Cohen's h for two proportions. |h| ~ 0.2 small, 0.5 medium, 0.8 large."""
    phi1 = 2 * math.asin(math.sqrt(p1))
    phi2 = 2 * math.asin(math.sqrt(p2))
    return phi1 - phi2


def _binom_cdf(k: int, n: int, p: float = 0.5) -> float:
    """P(X <= k | X ~ Bin(n, p)). For McNemar's exact via binomial."""
    # Sum binomial PMF up to k. Avoid scipy.
    if n == 0:
        return 1.0
    log_p = math.log(p)
    log_q = math.log(1 - p)
    # Use log-sum-exp for stability
    log_pmfs = []
    for i in range(k + 1):
        log_choose = (math.lgamma(n + 1) - math.lgamma(i + 1)
                       - math.lgamma(n - i + 1))
        log_pmfs.append(log_choose + i * log_p + (n - i) * log_q)
    m = max(log_pmfs)
    return math.exp(m) * sum(math.exp(x - m) for x in log_pmfs)


def mcnemar_exact_two_sided(b: int, c: int) -> float:
    """Exact two-sided McNemar's test (binomial), where b and c are
    the discordant counts (engine right & LLM wrong, vs engine wrong
    & LLM right)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    one_sided = _binom_cdf(k, n, p=0.5)
    p = min(1.0, 2 * one_sided)
    return p


def per_case_correctness(d: dict) -> dict[int, bool]:
    """Map {row_index: was_correct?} from a result JSON."""
    out: dict[int, bool] = {}
    for r in d.get("per_case", []):
        idx = r.get("index")
        if idx is None:
            continue
        out[idx] = bool(r.get("correct"))
    return out


def task_block(spec: dict) -> dict[str, Any]:
    """Compute per-task statistics. spec has: task_name, engine_path,
    llm_paths (dict), holdout_only (bool), task_label."""
    name = spec["task_name"]
    label = spec.get("task_label", name)
    engine_path = REPO / spec["engine_path"]
    if not engine_path.exists():
        return {"name": name, "label": label, "error": f"missing {engine_path}"}
    engine_d = json.loads(engine_path.read_text())
    engine_correct = per_case_correctness(engine_d)
    n_engine = len(engine_correct)

    if spec.get("filter_to_holdout"):
        # Engine result is full-test; intersect with the task's holdout
        # indices for fair comparison.
        sys.path.insert(0, str(REPO / "tools"))
        from test_split import split_test  # noqa: E402
        seed = spec.get("split_seed", 7)
        _, holdout = split_test(name, seed=seed, dev_fraction=0.5)
        h = set(holdout)
        engine_correct = {i: v for i, v in engine_correct.items() if i in h}
        n_engine = len(engine_correct)

    e_correct = sum(engine_correct.values())
    e_acc = e_correct / n_engine if n_engine else 0.0
    e_lo, e_hi = wilson_ci(e_correct, n_engine)

    block: dict[str, Any] = {
        "name": name, "label": label,
        "n": n_engine,
        "engine": {"correct": e_correct, "n": n_engine, "acc": e_acc, "ci95": (e_lo, e_hi)},
        "models": {},
        "engine_path": str(engine_path),
    }

    for model, llm_path in spec.get("llm_paths", {}).items():
        full_path = REPO / llm_path
        if not full_path.exists():
            block["models"][model] = {"error": f"missing {full_path}"}
            continue
        llm_d = json.loads(full_path.read_text())
        llm_correct = per_case_correctness(llm_d)
        if spec.get("filter_to_holdout"):
            llm_correct = {i: v for i, v in llm_correct.items() if i in h}
        # Intersect with engine indices for paired analysis
        common = set(engine_correct) & set(llm_correct)
        n_common = len(common)
        if n_common == 0:
            block["models"][model] = {"error": "no overlapping indices"}
            continue
        l_correct = sum(llm_correct[i] for i in common)
        l_acc = l_correct / n_common
        l_lo, l_hi = wilson_ci(l_correct, n_common)
        # McNemar's discordant counts
        b = sum(1 for i in common if engine_correct[i] and not llm_correct[i])
        c = sum(1 for i in common if not engine_correct[i] and llm_correct[i])
        p = mcnemar_exact_two_sided(b, c)
        h_eff = cohen_h(e_correct / n_common, l_acc)
        block["models"][model] = {
            "correct": l_correct, "n": n_common, "acc": l_acc,
            "ci95": (l_lo, l_hi),
            "mcnemar": {"b_engine_only": b, "c_llm_only": c, "p_two_sided": p},
            "delta_pp": (e_correct / n_common - l_acc) * 100,
            "cohen_h": h_eff,
        }
    return block


def fmt_pct(p: float) -> str:
    return f"{p*100:.1f}%"


def fmt_p(p: float) -> str:
    if p < 0.001:
        return "<0.001"
    if p < 0.01:
        return f"{p:.3f}"
    return f"{p:.3f}"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--tasks", type=Path, default=REPO / "docs" / "significance_tasks.yaml",
                   help="YAML with task → engine_path / llm_paths mapping")
    p.add_argument("--output", type=Path,
                   help="Write markdown report here (default: stdout)")
    args = p.parse_args()

    import yaml
    spec_doc = yaml.safe_load(args.tasks.read_text())
    blocks = [task_block(s) for s in spec_doc["tasks"]]

    md_lines: list[str] = []
    md_lines.append("# Statistical summary — Aethis engine vs frontier LLMs on LegalBench")
    md_lines.append("")
    md_lines.append("Generated by `tools/significance.py`. Confidence intervals are 95% Wilson; McNemar's tests are exact (binomial) on per-case discordant pairs; effect sizes are Cohen's h.")
    md_lines.append("")
    md_lines.append("## Per-task summary")
    md_lines.append("")
    md_lines.append("| Task | N | Engine | Sonnet 4.6 | Opus 4.7 | GPT-5.4 |")
    md_lines.append("|---|---:|---|---|---|---|")
    for b in blocks:
        if "error" in b:
            md_lines.append(f"| {b.get('label', b.get('name'))} | — | error: {b['error']} | | | |")
            continue
        e = b["engine"]
        engine_cell = f"{e['correct']}/{e['n']} ({fmt_pct(e['acc'])}, [{fmt_pct(e['ci95'][0])}–{fmt_pct(e['ci95'][1])}])"
        cells = [b["label"], str(b["n"]), engine_cell]
        for m in ["claude-sonnet-4-6", "claude-opus-4-7", "gpt-5.4"]:
            mb = b["models"].get(m)
            if not mb or "error" in (mb or {}):
                cells.append(mb.get("error", "—") if mb else "—")
                continue
            cell = (f"{mb['correct']}/{mb['n']} ({fmt_pct(mb['acc'])}); "
                    f"Δ {mb['delta_pp']:+.1f}pp; "
                    f"McNemar p={fmt_p(mb['mcnemar']['p_two_sided'])} "
                    f"(b={mb['mcnemar']['b_engine_only']}, c={mb['mcnemar']['c_llm_only']})")
            cells.append(cell)
        md_lines.append("| " + " | ".join(cells) + " |")
    md_lines.append("")

    md_lines.append("## Combined paired-binomial across tasks")
    md_lines.append("")
    md_lines.append("Aggregated per-case engine-vs-LLM agreement across all tasks in the report. Tests the null *engine and LLM are equally accurate per case*.")
    md_lines.append("")
    md_lines.append("| LLM | Total b (engine-only) | Total c (LLM-only) | Two-sided p |")
    md_lines.append("|---|---:|---:|---:|")
    for m in ["claude-sonnet-4-6", "claude-opus-4-7", "gpt-5.4"]:
        bs = sum(b["models"].get(m, {}).get("mcnemar", {}).get("b_engine_only", 0)
                 for b in blocks if "error" not in b)
        cs = sum(b["models"].get(m, {}).get("mcnemar", {}).get("c_llm_only", 0)
                 for b in blocks if "error" not in b)
        p_combined = mcnemar_exact_two_sided(bs, cs)
        md_lines.append(f"| {m} | {bs} | {cs} | {fmt_p(p_combined)} |")
    md_lines.append("")

    out = "\n".join(md_lines)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(out)
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
