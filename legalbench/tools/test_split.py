#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["datasets>=2.14"]
# ///
"""Deterministic dev/holdout split of a LegalBench test split.

Critical-review fix: hint iteration was happening on the same test set
we then reported numbers on. That's a soft test-set fit even when
hints are independently defensible. This script generates a stable
random partition (default 50-50) of each task's `test` split into
`dev` (where hint iteration is allowed) and `holdout` (where final
numbers are reported, with hints frozen).

The split is deterministic in the dataset's row indices given a fixed
seed, so the same set of indices is always assigned to dev vs
holdout for a given (task, seed) pair.

Methodology rule (enforced by convention, not code):
  - Iterate SME hints only after running the engine on the `dev`
    half. Compare hint variants on dev. Freeze the final hint set.
  - Run ONCE on `holdout` with the frozen hints. That's the reported
    number.
  - If the holdout result motivates further hint changes, those
    changes invalidate the held-out claim — they require a new
    holdout split (i.e. start over with a different dataset).

Usage:
    uv run tools/test_split.py --task personal_jurisdiction --seed 7
    # Prints: dev indices, holdout indices, sizes
"""
from __future__ import annotations

import argparse
import json
import random
import sys

from datasets import load_dataset


def split_test(task: str, *, seed: int, dev_fraction: float) -> tuple[list[int], list[int]]:
    """Split the task's test rows into (dev, holdout) using the dataset's
    own ``index`` column.

    Returns dataset-index values, deterministic given (task, seed).

    Why dataset-index, not positional ``range(n)``: some upstream LegalBench
    tasks ship a non-contiguous ``index`` column (e.g. ``hearsay`` has values
    [0..92, 94] for n=94 rows, skipping 93). Engine result JSONs key on the
    dataset's own ``index`` field. Mixing positional and dataset-index
    namespaces produces silent 1-case discrepancies on those tasks. Using
    the dataset's column throughout removes that ambiguity.

    For tasks where the index column is contiguous range(n), the behaviour
    is identical to the previous positional implementation given the same
    seed (``random.Random(seed).shuffle`` consumes the same RNG state on
    sequences of the same length, regardless of element values).
    """
    ds = load_dataset("nguha/legalbench", task)["test"]
    indices = [int(r["index"]) for r in ds]
    rng = random.Random(seed)
    rng.shuffle(indices)
    split = int(round(len(indices) * dev_fraction))
    dev = sorted(indices[:split])
    holdout = sorted(indices[split:])
    return dev, holdout


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--task", required=True)
    p.add_argument("--seed", type=int, default=7,
                   help="Pre-registered split seed. Don't change once results "
                        "have been reported on a given (task, seed).")
    p.add_argument("--dev-fraction", type=float, default=0.5,
                   help="Fraction of test split assigned to dev (default 0.5).")
    p.add_argument("--show-rows", action="store_true",
                   help="Print the actual test rows along with their split assignment.")
    a = p.parse_args()

    dev, holdout = split_test(a.task, seed=a.seed, dev_fraction=a.dev_fraction)
    n = len(dev) + len(holdout)
    print(json.dumps({
        "task": a.task,
        "seed": a.seed,
        "dev_fraction": a.dev_fraction,
        "n_total": n,
        "n_dev": len(dev),
        "n_holdout": len(holdout),
        "dev_indices": dev,
        "holdout_indices": holdout,
    }, indent=2))

    if a.show_rows:
        ds = load_dataset("nguha/legalbench", a.task)["test"]
        print("\n=== DEV ===", file=sys.stderr)
        for i in dev[:5]:
            print(f"  [{i}] {ds[i]['answer']:<3}  {ds[i]['text'][:100]}", file=sys.stderr)
        print(f"  ... ({len(dev)} total)", file=sys.stderr)
        print("\n=== HOLDOUT ===", file=sys.stderr)
        for i in holdout[:5]:
            print(f"  [{i}] {ds[i]['answer']:<3}  {ds[i]['text'][:100]}", file=sys.stderr)
        print(f"  ... ({len(holdout)} total)", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
