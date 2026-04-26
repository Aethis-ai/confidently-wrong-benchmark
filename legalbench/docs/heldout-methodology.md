# Held-out validation methodology

A response to the critical-review observation that hint iteration was
happening on the same test set we then reported numbers on. This is a
soft test-set fit, even when each individual hint is independently
defensible. From now on, for any new task, we use this protocol.

## The split

For each task, `tools/test_split.py --task <task> --seed 7` partitions
the upstream LegalBench `test` split into:

- **`dev`** (50%) — where hint iteration is allowed.
- **`holdout`** (50%) — final score reported, with hints frozen.

The split is deterministic in (task, seed). Don't change the seed for
a task once a holdout number has been reported — that would let us
silently re-roll until we got a favourable partition.

## Allowed iteration loops

On `dev`:
- Run the engine; observe failures.
- Write or refine SME guidance hints (Channel 1 or Channel 2; see
  [`docs/sme-guidance-channels.md`](sme-guidance-channels.md)).
- Re-run on `dev`. Iterate.
- Each hint must remain plain-English, practitioner-grounded, and
  defensible without reference to LegalBench cases or labels.

On `holdout`:
- Run engine ONCE per (task, frozen hint set). Report.
- Do not edit hints in response to holdout results. If you must,
  the holdout claim is invalidated — start over with a different
  partition (different `--seed`).

## Where the rule lives

The rule is enforced by convention, not by the runner. The runner has
an `--eval-split` flag (`dev` / `holdout` / `both`) which selects
which subset of test cases to evaluate. Logging and result filenames
should make clear which split a number came from.

## Applying retrospectively

The four LegalBench tasks already integrated (`diversity_*`, `hearsay`,
`jcrew_blocker`, `personal_jurisdiction`) had their hints iterated on
the **full** test split, not a held-out one. Their reported numbers
therefore have a soft test-set fit. We don't retroactively split
them — that would discard real engineering work. We *do* note this
explicitly in the head-to-head writeup and apply held-out methodology
strictly to the random-sample tasks (`cuad_covenant_not_to_sue`,
`contract_nli_explicit_identification`) and any future integrations.

## Reporting

When a result is published from a held-out split, the result file
should include:

```json
{
  "task": "...",
  "split": {
    "method": "tools/test_split.py",
    "seed": 7,
    "dev_fraction": 0.5,
    "evaluated_on": "holdout",
    "n_holdout": 25
  },
  "summary": { ... }
}
```

When a result is from `dev` (e.g. for hint-iteration logging),
similarly note `"evaluated_on": "dev"`. **The headline number
reported in any README should be the holdout number, not dev.**
