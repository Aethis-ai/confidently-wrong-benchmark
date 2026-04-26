# Pre-registration index

Master index of pre-registered random-sample seeds for the LegalBench
external-validation programme described in *Confidently Wrong:
Exception Chain Collapse* §6.10.

For each seed, the listed tasks were selected from the upstream
LegalBench task pool by `tools/random_task_pick.py --seed <N>
--exclude-already-done` **before** the upstream Task descriptions
were inspected for structure or expected difficulty. Whatever results
land in the holdout runs are reported.

| Seed | n | Picked at | Tasks | Verifiable via |
|---:|---:|---|---|---|
| 42 | 2 | v3.7 (April 2026) | `cuad_covenant_not_to_sue`, `contract_nli_explicit_identification` | dated commit history |
| 43 | 4 | early v3.8 (April 2026) | `contract_nli_notice_on_compelled_disclosure`, `learned_hands_health`, `cuad_liquidated_damages`, `opp115_international_and_specific_audiences` | dated commit history |
| 44 | 2 | v3.8 (April 2026) | `maud_pandemic_or_other_public_health_event__subject_to_disproportionate_impact_modifier`, `supply_chain_disclosure_best_practice_audits` | tag `pre-v3.8-legalbench-preregistration` (this repo) |

## Tag verifiability for seed 44

In the present repo, the migration commit that lands the seed-44 task
selection (without any seed-44 result JSONs) is tagged as
`pre-v3.8-legalbench-preregistration`. That tag is the verifiable
boundary: any subsequent result JSON for `legalbench-maud-…` or
`legalbench-supply-chain-…` was produced after the seed-44 task IDs
were already public.

The selection itself was committed first in the private internal
research workspace (restricted access) on 2026-04-26 under tag
`pre-v3.8-preregistration`. The migration commit in the present repo
carries the same `docs/preregistration-seed-44.md` file content, so
the seed-44 selection chain is verifiable from this artefact alone.

For seeds 42 and 43, no equivalent tag exists — those were
pre-registered via dated commits in the private workspace before the
explicit-tag protocol was introduced for v3.8. They remain verifiable
via the upstream `tools/random_task_pick.py --seed 42` and `--seed 43`
commands reproducing the same task selection deterministically (the
function depends only on the upstream LegalBench task list at the time
of selection and the seed).

## Per-seed details

- Seed 44: see `docs/preregistration-seed-44.md`.
- Seed 42, 43: see `docs/random-sample-results.md`.

## Protocol

Future pre-registered selections must:

1. Run `tools/random_task_pick.py --seed <N> --exclude-already-done`
   without iterating seeds for "better samples" (that's selection
   bias).
2. Commit the resulting `docs/preregistration-seed-<N>.md` with
   message `preregister: seed=<N> random task selection for v<X.Y>
   replication`.
3. Tag the commit as `pre-v<X.Y>-legalbench-preregistration` and
   push the tag.
4. Only then begin authoring or running.
5. Add the seed's row to the table above.
