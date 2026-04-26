"""Reusable runner for single-clause-classification LegalBench tasks.

Each domain's run.py imports this module and provides:
  - TASK: upstream LegalBench task name
  - FIELDS: list of (field_id, plain-English description) tuples
  - OUTCOME_RULE: docstring describing how the booleans combine

The module handles: loading rule.md + extractor_hints.md, the LLM
extractor with caching, the engine /decide call, dev/holdout splitting,
and result reporting in the canonical format.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

import requests
from datasets import load_dataset


def _load_hints(path: Path) -> str:
    if not path.exists():
        return ""
    return "\n".join(
        ln for ln in path.read_text().splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ).strip()


def _cache_key(model: str, prompt: str) -> str:
    return f"{model}__{hashlib.sha256(prompt.encode()).hexdigest()[:16]}"


def _build_extractor_prompt(rule_text: str, hints: str, fields: list[tuple[str, str]],
                             instance_text: str) -> str:
    hints_block = (
        f"--- SME GUIDANCE ---\n{hints}\n--- END GUIDANCE ---\n\n"
        if hints else ""
    )
    field_lines = "\n".join(f"- {fid}: {desc}" for fid, desc in fields)
    keys_json = ", ".join(f'"{fid}": true' for fid, _ in fields)
    return f"""You are an expert reading the rule below and an instance to classify under it. Decide each statutory element as true or false based ONLY on what the instance itself says.

--- RULE (verbatim canonical source) ---
{rule_text}
--- END RULE ---

{hints_block}Instance:
{instance_text}

Decide each element:

{field_lines}

Output: a single JSON object with exactly these keys and boolean values. No prose, no markdown.

Example output:
{{{keys_json}}}"""


def extract_fields(
    instance_text: str,
    *,
    rule_text: str,
    hints: str,
    fields: list[tuple[str, str]],
    model: str,
    cache_dir: Path,
) -> tuple[dict[str, Any] | None, str]:
    prompt = _build_extractor_prompt(rule_text, hints, fields, instance_text)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cp = cache_dir / f"{_cache_key(model, prompt)}.txt"
    if cp.exists():
        raw = cp.read_text()
    else:
        try:
            import anthropic
            c = anthropic.Anthropic()
            r = c.messages.create(
                model=model, max_tokens=600,
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
    for fid, _ in fields:
        v = obj.get(fid)
        if isinstance(v, bool):
            fv[fid] = v
        else:
            return None, raw
    return fv, raw


def decide(engine_url: str, api_key: str, bundle_id: str, fv: dict) -> dict:
    r = requests.post(
        f"{engine_url.rstrip('/')}/api/v1/public/decide",
        json={"bundle_id": bundle_id, "field_values": fv},
        headers={"X-API-Key": api_key} if api_key else {},
        timeout=30,
    )
    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}: {r.text[:200]}"}
    return r.json()


def load_split_indices(task: str, split_name: str, seed: int, repo_root: Path) -> list[int]:
    sys.path.insert(0, str(repo_root / "tools"))
    from test_split import split_test  # noqa: E402
    dev, holdout = split_test(task, seed=seed, dev_fraction=0.5)
    if split_name == "dev":
        return dev
    if split_name == "holdout":
        return holdout
    if split_name == "all":
        return sorted(dev + holdout)
    raise ValueError(f"unknown split: {split_name}")


def run(
    *,
    here: Path,
    task: str,
    fields: list[tuple[str, str]],
):
    """Generic runner main. Reads rule.md + extractor_hints.md from `here`,
    runs engine on the requested split, and writes results."""
    repo_root = here.parents[1]
    bundle_id = json.loads((here / ".aethis/state.json").read_text())["bundle_id"]
    rule_text = (here / "sources/rule.md").read_text()
    hints = _load_hints(here / "guidance" / "extractor_hints.md")

    p = argparse.ArgumentParser()
    p.add_argument("--eval-split", default="dev", choices=["dev", "holdout", "all"])
    p.add_argument("--split-seed", type=int, default=7)
    p.add_argument("--limit", type=int)
    p.add_argument("--engine-url", default="http://127.0.0.1:8080")
    p.add_argument("--api-key", default="test")
    p.add_argument("--extractor-model", default="claude-sonnet-4-6")
    p.add_argument("--cache-dir", type=Path, default=here / "results" / "extract_cache")
    p.add_argument("--output", type=Path)
    p.add_argument("--verbose", "-v", action="store_true")
    a = p.parse_args()

    indices = load_split_indices(task, a.eval_split, a.split_seed, repo_root)
    if a.limit:
        indices = indices[: a.limit]

    ds = load_dataset("nguha/legalbench", task)["test"]
    rows = [ds[i] for i in indices]
    print(f"{task} split={a.eval_split} N={len(rows)} (of {len(ds)}, seed={a.split_seed}), "
          f"extractor={a.extractor_model}", file=sys.stderr)

    correct = ef = ee = 0
    per_case: list[dict] = []
    for i, row in enumerate(rows, 1):
        text = row["text"]
        expected = "eligible" if row["answer"].strip().lower() == "yes" else "not_eligible"
        fv, raw = extract_fields(
            text, rule_text=rule_text, hints=hints, fields=fields,
            model=a.extractor_model, cache_dir=a.cache_dir,
        )
        if fv is None:
            ef += 1
            per_case.append({"index": row.get("index", i - 1), "expected": expected,
                              "status": "extract_fail", "raw": raw[:200]})
            continue
        resp = decide(a.engine_url, a.api_key, bundle_id, fv)
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
            print(f"  [{i:>4}] {'OK ' if ok else 'BAD'}  exp={expected:<13} got={decision:<13} fv={fv}",
                  file=sys.stderr)

    total = len(rows)
    print(f"\nEngine on {a.eval_split} split: {correct}/{total} ({100*correct/total:.1f}%)  "
          f"extract_fail={ef} engine_err={ee}", file=sys.stderr)

    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps({
            "task": task, "bundle_id": bundle_id,
            "extractor_model": a.extractor_model,
            "split": {"method": "tools/test_split.py", "seed": a.split_seed,
                       "dev_fraction": 0.5, "evaluated_on": a.eval_split, "n_total": total},
            "summary": {"correct": correct, "total": total, "extract_fail": ef, "engine_err": ee},
            "per_case": per_case,
        }, indent=2))
        print(f"Wrote {a.output}", file=sys.stderr)

    return 0 if (correct == total and ef == 0) else 1
