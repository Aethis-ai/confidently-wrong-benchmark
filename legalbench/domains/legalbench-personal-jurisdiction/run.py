#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["datasets>=2.14", "requests>=2.28", "anthropic>=0.40"]
# ///
"""LegalBench `personal_jurisdiction` runner.

Pipeline per case:
  1. LLM extractor reads the fact pattern, decides three booleans:
       - defendant_domiciled_in_forum
       - defendant_has_sufficient_contacts_with_forum
       - claim_arises_from_contacts_with_forum
  2. Aethis engine applies the rule (domicile OR (contacts AND nexus))
     and returns eligible (PJ exists) / not_eligible.
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
TASK = "personal_jurisdiction"
RULE_TEXT = (HERE / "sources/rule.md").read_text()


def _load_hints(path: Path) -> str:
    """Strip comment-only and blank lines so meta notes don't leak in."""
    if not path.exists():
        return ""
    return "\n".join(
        ln for ln in path.read_text().splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ).strip()


EXTRACTOR_HINTS = _load_hints(HERE / "guidance" / "extractor_hints.md")


_EXTRACTOR_PROMPT = """You are an expert on US federal civil procedure. Read the rule below, then read the fact pattern. The fact pattern asks whether a court located in a particular forum (often called Forum A or named explicitly) has personal jurisdiction over a defendant. Decide three boolean elements that determine the answer under the rule.

--- RULE (verbatim canonical source) ---
{rule}
--- END RULE ---

{hints_block}Fact pattern:
{fact}

Decide each element as true or false based on the fact pattern and the rule:

- defendant_domiciled_in_forum: true if the defendant lives in / is a citizen of the forum state (the state where the court sits). false otherwise.

- defendant_has_sufficient_contacts_with_forum: true if the defendant has substantial contacts with the forum state — for example, marketing in the forum, selling/shipping products into the forum, doing repeated business in the forum, or otherwise availing themselves of the privileges of the state. Casual or one-off interactions are usually insufficient. false otherwise.

- claim_arises_from_contacts_with_forum: true if the claim being litigated arises out of, or is connected to, the defendant's contacts with the forum (the "nexus" requirement). false if the claim is unrelated to the defendant's forum contacts. If the defendant has no contacts at all, set this false.

Output: a single JSON object with exactly these three keys and boolean values. No prose, no markdown.

Example output:
{{"defendant_domiciled_in_forum": false, "defendant_has_sufficient_contacts_with_forum": true, "claim_arises_from_contacts_with_forum": true}}"""


def _cache_key(model: str, prompt: str) -> str:
    return f"{model}__{hashlib.sha256(prompt.encode()).hexdigest()[:16]}"


def extract_fields(text: str, *, model: str, cache_dir: Path) -> tuple[dict[str, Any] | None, str]:
    hints_block = (
        f"--- SME GUIDANCE ---\n{EXTRACTOR_HINTS}\n--- END GUIDANCE ---\n\n"
        if EXTRACTOR_HINTS else ""
    )
    prompt = _EXTRACTOR_PROMPT.format(rule=RULE_TEXT, hints_block=hints_block, fact=text)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cp = cache_dir / f"{_cache_key(model, prompt)}.txt"
    if cp.exists():
        raw = cp.read_text()
    else:
        try:
            import anthropic
            c = anthropic.Anthropic()
            r = c.messages.create(
                model=model, max_tokens=800,
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
    for k in ("defendant_domiciled_in_forum",
              "defendant_has_sufficient_contacts_with_forum",
              "claim_arises_from_contacts_with_forum"):
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
    print(f"personal_jurisdiction {a.split} N={len(rows)}, extractor={a.extractor_model}",
          file=sys.stderr)

    correct = ef = ee = 0
    by_slice: dict[str, dict[str, int]] = {}
    per_case: list[dict] = []
    for i, row in enumerate(rows, 1):
        text = row["text"]
        sl = row.get("slice", "")
        expected = "eligible" if row["answer"].strip().lower() == "yes" else "not_eligible"

        fv, raw = extract_fields(text, model=a.extractor_model, cache_dir=a.cache_dir)
        if fv is None:
            ef += 1
            per_case.append({"index": row["index"], "slice": sl, "expected": expected,
                              "status": "extract_fail", "raw": raw[:200]})
            print(f"  [{i:>3}] EXTRACT_FAIL  [{sl}] {text[:80]!r}")
            continue

        resp = decide(a.engine_url, a.api_key, fv)
        if "error" in resp:
            ee += 1
            per_case.append({"index": row["index"], "slice": sl, "expected": expected,
                              "field_values": fv, "status": resp["error"]})
            continue

        decision = resp.get("decision")
        ok = decision == expected
        correct += int(ok)
        per_case.append({"index": row["index"], "slice": sl, "expected": expected,
                          "field_values": fv, "decision": decision, "correct": ok,
                          "fact": text})

        b = by_slice.setdefault(sl or "(unknown)", {"correct": 0, "total": 0})
        b["total"] += 1
        if ok:
            b["correct"] += 1

        if a.verbose or not ok:
            status = "OK " if ok else "BAD"
            print(f"  [{i:>3}] {status}  [{sl[:25]:<25}] exp={expected:<13} got={decision:<13} fv={fv}")

    total = len(rows)
    print(f"\nEngine: {correct}/{total}  ({100*correct/total:.1f}%)")
    print(f"  extract_fail = {ef}, engine_err = {ee}")

    if by_slice:
        print("\n  by slice:")
        for s in sorted(by_slice):
            b = by_slice[s]
            sa = (100 * b["correct"] / b["total"]) if b["total"] else 0
            print(f"    {s:<35}  {b['correct']:>2}/{b['total']:<2}  ({sa:>5.1f}%)")

    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps({
            "task": TASK, "bundle_id": BUNDLE_ID,
            "extractor_model": a.extractor_model,
            "summary": {"correct": correct, "total": total,
                         "extract_fail": ef, "engine_err": ee},
            "by_slice": by_slice,
            "per_case": per_case,
        }, indent=2))
        print(f"Wrote {a.output}")

    return 0 if (correct == total and ef == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
