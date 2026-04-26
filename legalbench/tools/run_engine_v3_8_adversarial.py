#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.28", "pyyaml>=6.0"]
# ///
"""Run engine on v3.8 adversarial CAR scenarios + verify against the
independently-authored prose expected-values.

Posts each scenario to /api/v1/public/decide with the canonical
bundle_id. Compares engine outcome to the scenario's `expect.outcome`
field. Reports any disagreements (engine bug OR authoring error).

Independent of the LLM-comparison harness — direct engine API calls.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import requests
import yaml


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--scenarios-yaml", type=Path, required=True)
    p.add_argument("--bundle-id", required=True,
                   help="e.g. construction-all-risks:20260412-gold")
    p.add_argument("--api-url", default="http://127.0.0.1:8080")
    p.add_argument("--api-key", default="test")
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()

    raw = yaml.safe_load(a.scenarios_yaml.read_text())
    tests = raw["tests"] if isinstance(raw, dict) and "tests" in raw else raw

    print(f"Engine verification: {len(tests)} scenarios against bundle "
          f"{a.bundle_id}", file=sys.stderr)
    headers = {"X-API-Key": a.api_key, "Content-Type": "application/json"}

    results = []
    correct = 0
    for i, t in enumerate(tests):
        name = t.get("name", f"scenario_{i}")
        expected = t.get("expect", {}).get("outcome")
        inputs = t.get("inputs", {})
        body = {"bundle_id": a.bundle_id, "field_values": inputs}
        started = time.time()
        try:
            r = requests.post(
                f"{a.api_url.rstrip('/')}/api/v1/public/decide",
                headers=headers, json=body, timeout=30,
            )
            elapsed = time.time() - started
            if r.status_code != 200:
                outcome = "API_ERROR"
                detail = f"HTTP {r.status_code}: {r.text[:200]}"
            else:
                d = r.json()
                outcome = d.get("decision", "?")
                detail = None
        except Exception as e:
            outcome = "API_ERROR"
            detail = f"{type(e).__name__}: {str(e)[:200]}"
            elapsed = time.time() - started

        ok = outcome == expected
        if ok:
            correct += 1
        mark = "✓" if ok else "✗"
        print(f"  [{i+1:>2}/{len(tests)}] {mark} {name:<48} "
              f"expected={expected:<13} got={outcome:<13} ({elapsed*1000:.0f}ms)",
              file=sys.stderr)
        if detail:
            print(f"        detail: {detail}", file=sys.stderr)
        results.append({
            "name": name, "expected": expected, "got": outcome,
            "ok": ok, "detail": detail, "elapsed_ms": int(elapsed * 1000),
        })

    print(f"\n=== Engine verification summary ===", file=sys.stderr)
    print(f"  correct: {correct}/{len(tests)}  ({100*correct/len(tests):.1f}%)",
          file=sys.stderr)
    disagreements = [r for r in results if not r["ok"]]
    if disagreements:
        print(f"  disagreements:", file=sys.stderr)
        for r in disagreements:
            print(f"    - {r['name']}: prose says {r['expected']}, engine says {r['got']}",
                  file=sys.stderr)

    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps({
        "bundle_id": a.bundle_id,
        "scenarios_yaml": str(a.scenarios_yaml),
        "n": len(tests),
        "correct": correct,
        "per_scenario": results,
    }, indent=2))
    print(f"\nWrote {a.output}", file=sys.stderr)
    return 0 if correct == len(tests) else 1


if __name__ == "__main__":
    sys.exit(main())
