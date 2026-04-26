#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["datasets>=2.14", "requests>=2.28"]
# ///
"""Phase 1 runner for `diversity_2` (1P × 2D × 1 claim each).

Templated narrative: "X is from S1. Y is from S2. Z is from S3. X sues Y and
Z each for CLAIM for $AMOUNT."
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import requests
from datasets import load_dataset


def _load_bundle_id() -> str:
    state = json.loads((Path(__file__).parent / ".aethis/state.json").read_text())
    return state["bundle_id"]


BUNDLE_ID = _load_bundle_id()
TASK = "diversity_2"

_NAME = r"[A-Z][a-z]+"
_STATE = r"[A-Z][a-z]+(?: [A-Z][a-z]+)?"
_CASE_RE = re.compile(
    rf"^(?P<p>{_NAME}) is from (?P<ps>{_STATE})\. "
    rf"(?P<d1>{_NAME}) is from (?P<d1s>{_STATE})\. "
    rf"(?P<d2>{_NAME}) is from (?P<d2s>{_STATE})\. "
    rf"(?P=p) sues (?P=d1) and (?P=d2) each for [^$]+\$(?P<amt>[\d,]+)\.?$",
)


def extract_fields(text: str) -> dict[str, Any] | None:
    m = _CASE_RE.match(text.strip())
    if not m:
        return None
    return {
        "plaintiff_state": m.group("ps"),
        "defendant_1_state": m.group("d1s"),
        "defendant_2_state": m.group("d2s"),
        "amount_per_defendant_usd": int(m.group("amt").replace(",", "")),
    }


def decide(engine_url: str, api_key: str, fv: dict) -> dict:
    resp = requests.post(
        f"{engine_url.rstrip('/')}/api/v1/public/decide",
        json={"bundle_id": BUNDLE_ID, "field_values": fv},
        headers={"X-API-Key": api_key} if api_key else {},
        timeout=30,
    )
    if resp.status_code != 200:
        return {"error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    return resp.json()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--split", default="test", choices=["train", "test"])
    p.add_argument("--engine-url", default="http://127.0.0.1:8080")
    p.add_argument("--api-key", default="test")
    p.add_argument("--output", type=Path)
    a = p.parse_args()

    rows = load_dataset("nguha/legalbench", TASK)[a.split].select(
        range(min(a.limit, len(load_dataset("nguha/legalbench", TASK)[a.split])))
    )
    print(f"Slice: {TASK}/{a.split}, N={len(rows)}", file=sys.stderr)

    correct = extract_fail = engine_err = 0
    per_case: list[dict] = []
    for i, row in enumerate(rows, 1):
        text = row["text"]
        expected = "eligible" if row["answer"].strip().lower() == "yes" else "not_eligible"
        fv = extract_fields(text)
        if fv is None:
            extract_fail += 1
            print(f"  [{i:>3}] EXTRACT_FAIL  {text[:90]!r}")
            per_case.append({"index": row["index"], "expected": expected, "status": "extract_fail", "text": text})
            continue
        resp = decide(a.engine_url, a.api_key, fv)
        if "error" in resp:
            engine_err += 1
            print(f"  [{i:>3}] ENGINE_ERR    {resp['error']}")
            per_case.append({"index": row["index"], "expected": expected, "field_values": fv, "status": resp["error"]})
            continue
        decision = resp.get("decision")
        ok = decision == expected
        if ok:
            correct += 1
        per_case.append({"index": row["index"], "expected": expected, "field_values": fv, "decision": decision, "correct": ok})
        status = "OK " if ok else "BAD"
        print(f"  [{i:>3}] {status}  exp={expected:<13} got={decision:<13} "
              f"P={fv['plaintiff_state']!r} D1={fv['defendant_1_state']!r} D2={fv['defendant_2_state']!r} "
              f"${fv['amount_per_defendant_usd']:,}")

    total = len(rows)
    print(f"\nEngine: {correct}/{total}  ({100*correct/total:.1f}%)")
    print(f"  extract_fail = {extract_fail}, engine_err = {engine_err}")
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps({
            "task": TASK, "bundle_id": BUNDLE_ID,
            "summary": {"correct": correct, "total": total,
                        "extract_fail": extract_fail, "engine_err": engine_err},
            "per_case": per_case,
        }, indent=2))
        print(f"Wrote {a.output}")
    return 0 if (correct == total and extract_fail == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
