#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.28"]
# ///
"""Seeded random pick of LegalBench tasks for unbiased evaluation.

Critical-review fix from the head-to-head methodology audit: previously
we picked tasks by inspecting their structure for "Aethis fit" before
authoring. That's selection bias. This script picks tasks by seeded
random sample from the upstream LegalBench task list, with no
inspection of structure or expected difficulty. Whatever comes out
is what we author — including tasks where Aethis is structurally
mismatched (e.g. multi-label outputs).

Pre-register the seed BEFORE running. Don't iterate seeds to "find a
better sample" — that's just selection bias dressed differently.

Usage:
    uv run tools/random_task_pick.py --seed 42 --n 2 \\
        --exclude-already-done domains/legalbench-*/.aethis/state.json
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import requests


REPO_ROOT = Path(__file__).resolve().parents[1]


def fetch_task_list() -> list[str]:
    """Pull the upstream LegalBench task directory list."""
    r = requests.get(
        "https://api.github.com/repos/HazyResearch/legalbench/contents/tasks",
        timeout=30,
    )
    r.raise_for_status()
    return sorted(f["name"] for f in r.json() if f["type"] == "dir")


def already_done_tasks(domains_glob: str) -> set[str]:
    """Discover which LegalBench tasks have already been integrated by
    looking at existing domains/legalbench-*/ directories."""
    out: set[str] = set()
    for d in sorted((REPO_ROOT / "domains").glob("legalbench-*")):
        if not d.is_dir():
            continue
        # Domain name like "legalbench-personal-jurisdiction" maps to upstream
        # task name "personal_jurisdiction" — convert kebab → snake.
        slug = d.name.removeprefix("legalbench-").replace("-", "_")
        # Special case: numbered diversity sub-tasks
        if slug.startswith("diversity_"):
            out.add(slug)
        else:
            out.add(slug)
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--seed", type=int, required=True,
                   help="PRE-REGISTERED random seed. Do not change after running.")
    p.add_argument("--n", type=int, default=2,
                   help="Number of tasks to pick.")
    p.add_argument("--exclude-already-done", action="store_true",
                   help="Skip tasks already integrated under domains/legalbench-*.")
    args = p.parse_args()

    all_tasks = fetch_task_list()
    excluded = already_done_tasks("legalbench-*") if args.exclude_already_done else set()
    candidates = [t for t in all_tasks if t not in excluded]

    print(f"Upstream task count: {len(all_tasks)}", file=sys.stderr)
    if excluded:
        print(f"Excluded (already done): {sorted(excluded)}", file=sys.stderr)
    print(f"Candidate pool: {len(candidates)}", file=sys.stderr)

    rng = random.Random(args.seed)
    picked = rng.sample(candidates, k=args.n)

    print(f"\n=== Random pick (seed={args.seed}, n={args.n}) ===", file=sys.stderr)
    for i, t in enumerate(picked, 1):
        print(f"  {i}. {t}", file=sys.stderr)

    # Output as JSON on stdout for machine consumption
    print(json.dumps({
        "seed": args.seed,
        "n": args.n,
        "candidate_pool_size": len(candidates),
        "excluded": sorted(excluded),
        "picked": picked,
    }, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
