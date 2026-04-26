#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["datasets>=2.14", "requests>=2.28", "anthropic>=0.40"]
# ///
"""Phase runner for LegalBench `hearsay` (FRE 801(a)–(c)).

Pipeline per case:
  1. LLM extractor reads the case's short fact-pattern, decides the three
     statutory elements (is_assertion, made_in_current_testimony,
     offered_for_truth_of_matter_asserted), returns JSON.
  2. The Aethis engine applies the rule encoded in the bundle to those
     three booleans and returns eligible (hearsay) / not_eligible (not
     hearsay).
  3. Score against the LegalBench answer.

Extraction is cached on disk by (model, prompt_hash) so re-runs are free.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import requests
from datasets import load_dataset


HERE = Path(__file__).parent
BUNDLE_ID = json.loads((HERE / ".aethis/state.json").read_text())["bundle_id"]
TASK = "hearsay"
RULE_TEXT = (HERE / "sources/rule.md").read_text()

# Optional SME guidance for the runtime extractor. Loaded if present;
# left empty otherwise. This is *separate* from sources/rule.md (which
# stays the verbatim canonical task description) — it carries
# practitioner-level interpretive notes the extractor uses to apply the
# rule's prongs to natural-language fact patterns.
_HINTS_PATH = HERE / "guidance" / "extractor_hints.md"
def _load_hints(path: Path) -> str:
    """Load hints, stripping comment-only and blank lines so meta notes
    in the file don't leak into the prompt."""
    if not path.exists():
        return ""
    content = "\n".join(
        ln for ln in path.read_text().splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    )
    return content.strip()
EXTRACTOR_HINTS = _load_hints(_HINTS_PATH)


_EXTRACTOR_PROMPT = """You are an expert on the Federal Rules of Evidence. Read the rule below, then read the fact-pattern. For the fact-pattern, decide the three statutory elements that determine whether it is hearsay under FRE 801(a)–(c).

--- RULE (verbatim canonical source) ---
{rule}
--- END RULE ---

{hints_block}Fact-pattern:
{fact}

Decide each of the three elements as true or false based on the fact-pattern and the rule:

- is_assertion: true if the underlying conduct or speech is an intentional assertion of a proposition (an oral assertion, a written assertion, or non-verbal conduct intended as an assertion). false if it is non-assertive conduct (e.g. running, falling asleep, performing a physical act for its own sake, or any conduct from which the court might draw inferences but which the actor did not intend as a communication).

- made_in_current_testimony: true if the statement was made by the declarant while testifying at the current trial or hearing. false if it was made anywhere else (out-of-court conversations, prior depositions, letters, recordings, statements made in another proceeding).

- offered_for_truth_of_matter_asserted: true if the statement is offered in evidence to prove that what it asserts is in fact true. false if it is offered for some other purpose (to show the statement was made, to show its effect on a listener, to show the declarant's state of mind or knowledge, or as circumstantial evidence not depending on the truth of the statement).

Output: a single JSON object with exactly these three keys and boolean values. No prose, no markdown, no commentary.

Example output:
{{"is_assertion": true, "made_in_current_testimony": false, "offered_for_truth_of_matter_asserted": true}}"""


def _cache_key(model: str, prompt: str) -> str:
    return f"{model}__{hashlib.sha256(prompt.encode()).hexdigest()[:16]}"


def extract_fields(
    text: str,
    *,
    model: str,
    cache_dir: Path,
) -> tuple[dict[str, Any] | None, str]:
    """Returns (field_values_dict_or_None, raw_response)."""
    hints_block = (
        f"--- SME GUIDANCE (treatise-level interpretive notes) ---\n"
        f"{EXTRACTOR_HINTS}\n--- END GUIDANCE ---\n\n"
        if EXTRACTOR_HINTS else ""
    )
    prompt = _EXTRACTOR_PROMPT.format(rule=RULE_TEXT, hints_block=hints_block, fact=text)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{_cache_key(model, prompt)}.txt"
    if cache_path.exists():
        raw = cache_path.read_text()
    else:
        try:
            import anthropic
            client = anthropic.Anthropic()
            resp = client.messages.create(
                model=model, max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text if resp.content else ""
        except Exception as e:
            return None, f"__error__:{type(e).__name__}: {str(e)[:120]}"
        cache_path.write_text(raw)

    # Extract the JSON object from the response.
    import re
    m = re.search(r"\{[^{}]*\}", raw)
    if not m:
        return None, raw
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None, raw
    # Coerce + validate
    fv: dict[str, Any] = {}
    for key in ("is_assertion", "made_in_current_testimony",
                "offered_for_truth_of_matter_asserted"):
        v = obj.get(key)
        if isinstance(v, bool):
            fv[key] = v
        else:
            return None, raw
    return fv, raw


def decide(engine_url: str, api_key: str, field_values: dict) -> dict:
    resp = requests.post(
        f"{engine_url.rstrip('/')}/api/v1/public/decide",
        json={"bundle_id": BUNDLE_ID, "field_values": field_values},
        headers={"X-API-Key": api_key} if api_key else {},
        timeout=30,
    )
    if resp.status_code != 200:
        return {"error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    return resp.json()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--limit", type=int, default=10,
                   help="First N test cases (default: 10 — vertical slice)")
    p.add_argument("--split", default="test", choices=["train", "test"])
    p.add_argument("--engine-url", default="http://127.0.0.1:8080")
    p.add_argument("--api-key", default="test")
    p.add_argument("--extractor-model", default="claude-sonnet-4-6")
    p.add_argument("--cache-dir", type=Path,
                   default=HERE / "results" / "extract_cache")
    p.add_argument("--output", type=Path)
    p.add_argument("--verbose", "-v", action="store_true")
    args = p.parse_args()

    rows = load_dataset("nguha/legalbench", TASK)[args.split]
    rows = rows.select(range(min(args.limit, len(rows))))
    print(f"Slice: {TASK}/{args.split}, N={len(rows)}, "
          f"extractor={args.extractor_model}", file=sys.stderr)

    correct = extract_fail = engine_err = 0
    per_case: list[dict] = []
    for i, row in enumerate(rows, 1):
        text = row["text"]
        sl = row["slice"]
        expected_yes = row["answer"].strip().lower() == "yes"
        expected = "eligible" if expected_yes else "not_eligible"

        fv, raw = extract_fields(text, model=args.extractor_model,
                                  cache_dir=args.cache_dir)
        if fv is None:
            extract_fail += 1
            per_case.append({"index": row["index"], "slice": sl,
                              "expected": expected, "status": "extract_fail",
                              "raw": raw[:200]})
            print(f"  [{i:>3}] EXTRACT_FAIL  [{sl}] {text[:70]!r}")
            continue

        resp = decide(args.engine_url, args.api_key, fv)
        if "error" in resp:
            engine_err += 1
            per_case.append({"index": row["index"], "slice": sl,
                              "expected": expected, "field_values": fv,
                              "status": resp["error"]})
            print(f"  [{i:>3}] ENGINE_ERR    {resp['error']}")
            continue

        decision = resp.get("decision")
        ok = decision == expected
        correct += int(ok)
        per_case.append({"index": row["index"], "slice": sl,
                          "expected": expected, "field_values": fv,
                          "decision": decision, "correct": ok,
                          "fact": text})
        if args.verbose or not ok:
            status = "OK " if ok else "BAD"
            print(f"  [{i:>3}] {status}  [{sl[:25]:<25}] "
                  f"exp={expected:<13} got={decision:<13} fv={fv}")

    total = len(rows)
    print(f"\nEngine: {correct}/{total}  ({100*correct/total:.1f}%)")
    print(f"  extract_fail = {extract_fail}, engine_err = {engine_err}")

    # Per-slice breakdown
    by_slice: dict[str, dict[str, int]] = {}
    for r in per_case:
        s = r.get("slice", "?")
        b = by_slice.setdefault(s, {"correct": 0, "total": 0, "fail": 0})
        b["total"] += 1
        if r.get("correct"):
            b["correct"] += 1
        if r.get("status"):
            b["fail"] += 1
    if by_slice:
        print("\n  by slice:")
        for s, b in sorted(by_slice.items()):
            acc = (100 * b["correct"] / b["total"]) if b["total"] else 0
            print(f"    {s:<35}  {b['correct']:>2}/{b['total']:<2}  ({acc:>5.1f}%)")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({
            "task": TASK, "bundle_id": BUNDLE_ID,
            "extractor_model": args.extractor_model,
            "summary": {"correct": correct, "total": total,
                         "extract_fail": extract_fail, "engine_err": engine_err},
            "by_slice": by_slice,
            "per_case": per_case,
        }, indent=2))
        print(f"Wrote {args.output}")

    return 0 if (correct == total and extract_fail == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
