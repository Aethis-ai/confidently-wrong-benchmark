#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["datasets>=2.14", "requests>=2.28", "anthropic>=0.40"]
# ///
"""LegalBench `jcrew_blocker` runner.

Pipeline per case:
  1. LLM extractor reads the contract clause and decides whether each
     of the two J.Crew Blocker prongs is present:
       - prohibits_transfer_ip_to_unrestricted_subsidiary
       - requires_lender_consent_for_ip_transfer
  2. Aethis engine applies the rule (both prongs required) and returns
     eligible / not_eligible.
  3. Score against LegalBench answer (Yes / No).
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
BUNDLE_ID = json.loads((HERE / ".aethis/state.json").read_text())["bundle_id"]
TASK = "jcrew_blocker"
RULE_TEXT = (HERE / "sources/rule.md").read_text()


def _load_hints(path: Path) -> str:
    """Load hints, stripping comment-only and blank lines so meta notes
    don't leak into the prompt."""
    if not path.exists():
        return ""
    return "\n".join(
        ln for ln in path.read_text().splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ).strip()


EXTRACTOR_HINTS = _load_hints(HERE / "guidance" / "extractor_hints.md")


_EXTRACTOR_PROMPT = """You are an expert on leveraged loan documents. Read the rule below, then read the contract clause. Decide whether each of the two J.Crew Blocker prongs is present in the clause.

--- RULE (verbatim canonical source) ---
{rule}
--- END RULE ---

{hints_block}Contract clause:
{text}

Decide each prong as true or false based ONLY on what the clause itself says:

- prohibits_transfer_ip_to_unrestricted_subsidiary: true if the clause prohibits the borrower from transferring intellectual property (or material assets identified as IP) to an unrestricted subsidiary. false otherwise.

- requires_lender_consent_for_ip_transfer: true if the clause requires the borrower to obtain consent from its agent or lenders before transferring IP to any subsidiary. false otherwise.

Output: a single JSON object with exactly these two keys and boolean values. No prose, no markdown.

Example output:
{{"prohibits_transfer_ip_to_unrestricted_subsidiary": true, "requires_lender_consent_for_ip_transfer": false}}"""


def _cache_key(model: str, prompt: str) -> str:
    return f"{model}__{hashlib.sha256(prompt.encode()).hexdigest()[:16]}"


def extract_fields(text: str, *, model: str, cache_dir: Path) -> tuple[dict[str, Any] | None, str]:
    hints_block = (
        f"--- SME GUIDANCE (LSTA / leveraged-finance practitioner notes) ---\n"
        f"{EXTRACTOR_HINTS}\n--- END GUIDANCE ---\n\n"
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
                model=model, max_tokens=300,
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
    for k in ("prohibits_transfer_ip_to_unrestricted_subsidiary",
              "requires_lender_consent_for_ip_transfer"):
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


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--split", default="test", choices=["train", "test"])
    p.add_argument("--engine-url", default="http://127.0.0.1:8080")
    p.add_argument("--api-key", default="test")
    p.add_argument("--extractor-model", default="claude-sonnet-4-6")
    p.add_argument("--cache-dir", type=Path,
                   default=HERE / "results" / "extract_cache")
    p.add_argument("--output", type=Path)
    p.add_argument("--verbose", "-v", action="store_true")
    a = p.parse_args()

    rows = load_dataset("nguha/legalbench", TASK)[a.split].select(
        range(min(a.limit, len(load_dataset("nguha/legalbench", TASK)[a.split])))
    )
    print(f"jcrew_blocker {a.split} N={len(rows)}, extractor={a.extractor_model}", file=sys.stderr)

    correct = ef = ee = 0
    per_case: list[dict] = []
    for i, row in enumerate(rows, 1):
        text = row["text"]
        expected = "eligible" if row["answer"].strip().lower() == "yes" else "not_eligible"
        fv, raw = extract_fields(text, model=a.extractor_model,
                                  cache_dir=a.cache_dir)
        if fv is None:
            ef += 1
            per_case.append({"index": row["index"], "expected": expected,
                              "status": "extract_fail", "raw": raw[:200]})
            print(f"  [{i:>3}] EXTRACT_FAIL  {raw[:80]!r}")
            continue
        resp = decide(a.engine_url, a.api_key, fv)
        if "error" in resp:
            ee += 1
            per_case.append({"index": row["index"], "expected": expected,
                              "field_values": fv, "status": resp["error"]})
            continue
        decision = resp.get("decision")
        ok = decision == expected
        correct += int(ok)
        per_case.append({"index": row["index"], "expected": expected,
                          "field_values": fv, "decision": decision,
                          "correct": ok, "text": text})
        if a.verbose or not ok:
            print(f"  [{i:>3}] {'OK ' if ok else 'BAD'}  exp={expected:<13} got={decision:<13} fv={fv}")

    total = len(rows)
    print(f"\nEngine: {correct}/{total}  ({100*correct/total:.1f}%)")
    print(f"  extract_fail = {ef}, engine_err = {ee}")

    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps({
            "task": TASK, "bundle_id": BUNDLE_ID,
            "extractor_model": a.extractor_model,
            "summary": {"correct": correct, "total": total,
                         "extract_fail": ef, "engine_err": ee},
            "per_case": per_case,
        }, indent=2))
        print(f"Wrote {a.output}")
    return 0 if (correct == total and ef == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
