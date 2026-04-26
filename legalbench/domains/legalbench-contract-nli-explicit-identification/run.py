#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["datasets>=2.14", "requests>=2.28", "anthropic>=0.40"]
# ///
"""LegalBench `contract_nli_explicit_identification` runner.

Random-sampled task. Held-out methodology applies; see
docs/heldout-methodology.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import requests
from datasets import load_dataset


HERE = Path(__file__).parent
REPO_ROOT = HERE.parents[1]
BUNDLE_ID = json.loads((HERE / ".aethis/state.json").read_text())["bundle_id"]
TASK = "contract_nli_explicit_identification"
RULE_TEXT = (HERE / "sources/rule.md").read_text()


def _load_hints(path: Path) -> str:
    if not path.exists():
        return ""
    return "\n".join(
        ln for ln in path.read_text().splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ).strip()


EXTRACTOR_HINTS = _load_hints(HERE / "guidance" / "extractor_hints.md")


_EXTRACTOR_PROMPT = """You are an expert on US commercial-contract drafting, especially non-disclosure agreements. Read the rule below, then read the NDA clause. Decide whether each of the three implicit elements of the classification question is present in the clause.

--- RULE (verbatim canonical source + classification question) ---
{rule}
--- END RULE ---

{hints_block}NDA clause:
{text}

Decide each element as true or false based ONLY on what the clause itself says:

- clause_addresses_confidential_information: true if the clause defines, scopes, or describes how Confidential Information is identified or marked. false if the clause is about something else entirely.

- clause_requires_explicit_identification: true if the clause requires affirmative designation of information as confidential — e.g. labelling, marking, stamping with a "Confidential" legend, written notice, or some other explicit identification act. false if the clause makes information confidential by default (e.g. "all information disclosed shall be deemed confidential") or doesn't address identification at all.

- duty_assigned_to_disclosing_party: true if the duty to identify falls on the Disclosing Party (the party making the disclosure). false if the duty falls on the Receiving Party, is mutual, is passive, or is not assigned at all.

Output: a single JSON object with exactly these three keys and boolean values. No prose, no markdown.

Example output:
{{"clause_addresses_confidential_information": true, "clause_requires_explicit_identification": true, "duty_assigned_to_disclosing_party": true}}"""


def _cache_key(model: str, prompt: str) -> str:
    return f"{model}__{hashlib.sha256(prompt.encode()).hexdigest()[:16]}"


def extract_fields(text: str, *, model: str, cache_dir: Path) -> tuple[dict[str, Any] | None, str]:
    hints_block = (
        f"--- SME GUIDANCE ---\n{EXTRACTOR_HINTS}\n--- END GUIDANCE ---\n\n"
        if EXTRACTOR_HINTS else ""
    )
    prompt = _EXTRACTOR_PROMPT.format(rule=RULE_TEXT, hints_block=hints_block, text=text)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cp = cache_dir / f"{_cache_key(model, prompt)}.txt"
    if cp.exists():
        raw = cp.read_text()
    else:
        try:
            import anthropic
            c = anthropic.Anthropic()
            r = c.messages.create(
                model=model, max_tokens=400,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = r.content[0].text if r.content else ""
        except Exception as e:
            return None, f"__error__:{type(e).__name__}: {str(e)[:120]}"
        cp.write_text(raw)

    m = re.search(r"\{[^{}]*\}", raw)
    if not m:
        return None, raw
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None, raw
    fv: dict[str, Any] = {}
    for k in ("clause_addresses_confidential_information",
              "clause_requires_explicit_identification",
              "duty_assigned_to_disclosing_party"):
        v = obj.get(k)
        if isinstance(v, bool):
            fv[k] = v
        else:
            return None, raw
    return fv, raw


def decide(engine_url: str, api_key: str, fv: dict) -> dict:
    r = requests.post(
        f"{engine_url.rstrip('/')}/api/v1/public/decide",
        json={"bundle_id": BUNDLE_ID, "field_values": fv},
        headers={"X-API-Key": api_key} if api_key else {},
        timeout=30,
    )
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text[:200]}"}
    return r.json()


def _load_split_indices(split_name: str, seed: int) -> list[int]:
    sys.path.insert(0, str(REPO_ROOT / "tools"))
    from test_split import split_test
    dev, holdout = split_test(TASK, seed=seed, dev_fraction=0.5)
    if split_name == "dev":
        return dev
    if split_name == "holdout":
        return holdout
    if split_name == "all":
        return sorted(dev + holdout)
    raise ValueError(f"unknown split: {split_name}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--eval-split", default="dev", choices=["dev", "holdout", "all"])
    p.add_argument("--split-seed", type=int, default=7)
    p.add_argument("--limit", type=int)
    p.add_argument("--engine-url", default="http://127.0.0.1:8080")
    p.add_argument("--api-key", default="test")
    p.add_argument("--extractor-model", default="claude-sonnet-4-6")
    p.add_argument("--cache-dir", type=Path,
                   default=HERE / "results" / "extract_cache")
    p.add_argument("--output", type=Path)
    p.add_argument("--verbose", "-v", action="store_true")
    a = p.parse_args()

    indices = _load_split_indices(a.eval_split, a.split_seed)
    if a.limit:
        indices = indices[:a.limit]

    ds = load_dataset("nguha/legalbench", TASK)["test"]
    rows = [ds[i] for i in indices]
    print(f"contract_nli_explicit_identification split={a.eval_split} N={len(rows)} "
          f"(of {len(ds)}, seed={a.split_seed}), extractor={a.extractor_model}",
          file=sys.stderr)

    correct = ef = ee = 0
    per_case: list[dict] = []
    for i, row in enumerate(rows, 1):
        text = row["text"]
        expected = "eligible" if row["answer"].strip().lower() == "yes" else "not_eligible"
        fv, raw = extract_fields(text, model=a.extractor_model, cache_dir=a.cache_dir)
        if fv is None:
            ef += 1
            per_case.append({"index": row.get("index", i - 1), "expected": expected,
                              "status": "extract_fail", "raw": raw[:200]})
            continue
        resp = decide(a.engine_url, a.api_key, fv)
        if "error" in resp:
            ee += 1
            per_case.append({"index": row.get("index", i - 1), "expected": expected,
                              "field_values": fv, "status": resp["error"]})
            continue
        decision = resp.get("decision")
        ok = decision == expected
        correct += int(ok)
        per_case.append({"index": row.get("index", i - 1), "expected": expected,
                          "field_values": fv, "decision": decision, "correct": ok,
                          "text": text})
        if a.verbose or not ok:
            status = "OK " if ok else "BAD"
            print(f"  [{i:>3}] {status}  exp={expected:<13} got={decision:<13} fv={fv}",
                  file=sys.stderr)

    total = len(rows)
    print(f"\nEngine on {a.eval_split} split: {correct}/{total}  ({100*correct/total:.1f}%)",
          file=sys.stderr)
    print(f"  extract_fail = {ef}, engine_err = {ee}", file=sys.stderr)

    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps({
            "task": TASK, "bundle_id": BUNDLE_ID,
            "extractor_model": a.extractor_model,
            "split": {
                "method": "tools/test_split.py",
                "seed": a.split_seed,
                "dev_fraction": 0.5,
                "evaluated_on": a.eval_split,
                "n_total": total,
            },
            "summary": {"correct": correct, "total": total,
                         "extract_fail": ef, "engine_err": ee},
            "per_case": per_case,
        }, indent=2))
        print(f"Wrote {a.output}", file=sys.stderr)

    return 0 if (correct == total and ef == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
