#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["datasets>=2.14", "requests>=2.28"]
# ///
"""diversity_6 (2P × 2D × 2 claims per defendant): "X is from S1. Y is from S2. Z is from S3. W is from S4. X and Y both sue Z for CLAIM_A for $A1 and CLAIM_B for $A2. X and Y both sue W for CLAIM_C for $B1 and CLAIM_D for $B2." """
from __future__ import annotations

import argparse, json, re, sys
from pathlib import Path

import requests
from datasets import load_dataset


BUNDLE_ID = json.loads((Path(__file__).parent / ".aethis/state.json").read_text())["bundle_id"]
TASK = "diversity_6"

_NAME = r"[A-Z][a-z]+"
_STATE = r"[A-Z][a-z]+(?: [A-Z][a-z]+)?"
_CASE_RE = re.compile(
    rf"^(?P<p1>{_NAME}) is from (?P<p1s>{_STATE})\. "
    rf"(?P<p2>{_NAME}) is from (?P<p2s>{_STATE})\. "
    rf"(?P<d1>{_NAME}) is from (?P<d1s>{_STATE})\. "
    rf"(?P<d2>{_NAME}) is from (?P<d2s>{_STATE})\. "
    rf"(?P=p1) and (?P=p2) both sue (?P=d1) for [^$]+\$(?P<d1a>[\d,]+) and [^$]+\$(?P<d1b>[\d,]+)\. "
    rf"(?P=p1) and (?P=p2) both sue (?P=d2) for [^$]+\$(?P<d2a>[\d,]+) and [^$]+\$(?P<d2b>[\d,]+)\.?$",
)


def extract_fields(text: str):
    m = _CASE_RE.match(text.strip())
    if not m:
        return None
    return {
        "plaintiff_1_state": m.group("p1s"),
        "plaintiff_2_state": m.group("p2s"),
        "defendant_1_state": m.group("d1s"),
        "defendant_2_state": m.group("d2s"),
        "d1_claim_a_amount_usd": int(m.group("d1a").replace(",", "")),
        "d1_claim_b_amount_usd": int(m.group("d1b").replace(",", "")),
        "d2_claim_a_amount_usd": int(m.group("d2a").replace(",", "")),
        "d2_claim_b_amount_usd": int(m.group("d2b").replace(",", "")),
    }


def decide(engine_url, api_key, fv):
    r = requests.post(f"{engine_url.rstrip('/')}/api/v1/public/decide",
                      json={"bundle_id": BUNDLE_ID, "field_values": fv},
                      headers={"X-API-Key": api_key} if api_key else {}, timeout=30)
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text[:200]}"}
    return r.json()


def main():
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

    correct = ef = ee = 0
    per_case = []
    for i, row in enumerate(rows, 1):
        text = row["text"]
        expected = "eligible" if row["answer"].strip().lower() == "yes" else "not_eligible"
        fv = extract_fields(text)
        if fv is None:
            ef += 1
            print(f"  [{i:>3}] EXTRACT_FAIL  {text[:90]!r}")
            per_case.append({"index": row["index"], "expected": expected, "status": "extract_fail", "text": text})
            continue
        resp = decide(a.engine_url, a.api_key, fv)
        if "error" in resp:
            ee += 1
            print(f"  [{i:>3}] ENGINE_ERR    {resp['error']}")
            per_case.append({"index": row["index"], "expected": expected, "field_values": fv, "status": resp["error"]})
            continue
        d = resp.get("decision")
        ok = d == expected
        correct += int(ok)
        per_case.append({"index": row["index"], "expected": expected, "field_values": fv, "decision": d, "correct": ok})
        d1_sum = fv["d1_claim_a_amount_usd"] + fv["d1_claim_b_amount_usd"]
        d2_sum = fv["d2_claim_a_amount_usd"] + fv["d2_claim_b_amount_usd"]
        print(f"  [{i:>3}] {'OK ' if ok else 'BAD'}  exp={expected:<13} got={d:<13} "
              f"P=({fv['plaintiff_1_state']},{fv['plaintiff_2_state']}) "
              f"D=({fv['defendant_1_state']},{fv['defendant_2_state']}) "
              f"d1=${d1_sum:,} d2=${d2_sum:,}")
    total = len(rows)
    print(f"\nEngine: {correct}/{total}  ({100*correct/total:.1f}%)")
    print(f"  extract_fail = {ef}, engine_err = {ee}")
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps({"task": TASK, "bundle_id": BUNDLE_ID,
            "summary": {"correct": correct, "total": total, "extract_fail": ef, "engine_err": ee},
            "per_case": per_case}, indent=2))
    return 0 if (correct == total and ef == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
