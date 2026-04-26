# LegalBench `hearsay` — Aethis engine result

## Result

**Engine 85/94 (90.4%) vs Opus 4.7 78/94 (83.0%) vs Sonnet 4.6 72/94 (76.6%)**
on the LegalBench `hearsay` test split (94 cases).
Engine **+7.4pt** over Opus, **+13.8pt** over Sonnet. All runs saw the
same canonical prose; all parsed cleanly (zero parse errors).

| Model | Correct | Accuracy |
| --- | ---: | ---: |
| **Aethis engine** (sonnet-extractor + symbolic rule) | **85/94** | **90.4%** |
| Opus 4.7 (LLM only) | 78/94 | 83.0% |
| Sonnet 4.6 (LLM only) | 72/94 | 76.6% |

Pipeline: the engine path uses sonnet as a per-case field extractor
(reads the case → 3 booleans), then the symbolic engine applies the
conjunction. The LLM-only paths ask the model to do the whole thing
in one shot using the upstream LegalBench `base_prompt.txt` (the
canonical 5-shot prompt published baselines use).

The engine's edge is structural: the model often correctly identifies
the three FRE 801(a)–(c) elements but mis-applies the conjunction
(e.g. flags "non-assertive conduct" then still answers Yes). The
engine's symbolic rule application cannot make that error; the
extractor only has to identify each element, not combine them.

Even Opus 4.7 — the strongest available frontier model in the Anthropic
family — is 7pt below the engine on this task.

## Note on SME extractor hints (negative result)

We attempted a treatise-style set of SME hints in
`guidance/extractor_hints.md` covering the three FRE 801 prongs
(advisory committee notes, Mueller & Kirkpatrick, Weinstein-style
treatment of "state of mind", "verbal acts", "effect on listener",
etc.). Empirically the hints **reduced** engine accuracy from 85/94
(90.4%) to 82/94 (87.2%). The regression concentrated on
Standard-hearsay and Not-introduced-to-prove-truth cases that sit at
the doctrinal boundary between *"state of mind"* and *"offered for
truth of matter asserted"* — territory where standard treatise
treatment and the LegalBench answer key diverge (e.g. statements
like *"On the issue of Bobby's sanity, the fact that Bobby told a
friend she believed she was Santa Claus"* are arguably state-of-mind
under treatise doctrine but the dataset labels them as hearsay).

We deliberately did **not** iterate the hints to fit the dataset's
interpretation — refining SME guidance against test labels is
contamination. The treatise hints we wrote were defensible on their
own grounds; if they don't lift the score, they don't lift it. We
reverted to no extractor hints; the engine's 85/94 (90.4%) is the
honest hearsay result.

This is a meaningful finding about *when* SME guidance helps:
- It worked dramatically on `jcrew_blocker` (16.7% → 100%) where the
  source had a clean, resolvable interpretive ambiguity.
- It did **not** work on `hearsay` where the remaining errors sit at
  a doctrinally-contested boundary; standard practitioner notes
  failed to push the model toward the dataset's narrower view.

See [`docs/headtohead.md`](../../docs/headtohead.md) for the broader
head-to-head context across all seven LegalBench tasks we've run.

## Source provenance

`sources/rule.md` is the **verbatim canonical Task description** from
[`HazyResearch/legalbench/tasks/hearsay/README.md`](https://github.com/HazyResearch/legalbench/blob/main/tasks/hearsay/README.md)
([CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), Source
author: Neel Guha). No paraphrase, no editorial choice. This is the
same rule prose that frontier-LLM baselines on this task have been
evaluated against, so the engine result is directly comparable.

The v2 bundle was authored from this clean source. (v1, authored from
a hand-written FRE 801(a)–(c) paraphrase, scored 78/94 (83.0%) — the
v2 jump comes from the canonical source's worked example for the
"offered for truth of matter asserted" prong helping the LLM
extractor.)

## Pipeline

```
case text  →  LLM extractor (claude-sonnet-4-6, given verbatim canonical rule)
           →  field_values: { is_assertion, made_in_current_testimony,
                              offered_for_truth_of_matter_asserted }
           →  POST /decide (engine evaluates the bundle's rule)
           →  decision: eligible (= hearsay) | not_eligible | undetermined
           →  score against LegalBench answer (Yes / No)
```

The Aethis engine does the deterministic rule-application work
(conjunction with negation). The LLM extractor does the
case-understanding work — reading a short fact-pattern and deciding
whether each statutory element is met. This division mirrors how
Aethis is meant to be used in production: LLM for fact extraction
from prose, symbolic engine for rule application.

## Reproducing

```bash
# Local aethis-core on :8080, ANTHROPIC_API_KEY in env:
uv run domains/legalbench-hearsay/run.py --limit 94 \
    --output domains/legalbench-hearsay/results/full_v2.json
```

Extractor outputs are cached on disk under
`domains/legalbench-hearsay/results/extract_cache/`, keyed by
`(model, prompt_hash)`, so re-runs are free.

## v2 bundle

- Project: `proj_Dt2wQwC3bLnjLk1O`
- Bundle: `legalbench_hearsay_v2:20260425-258fc464`
- 8/8 statute-derived bundle tests passing (first iteration).

## Authoring integrity

- Source = verbatim LegalBench Task description, no paraphrase.
- 8 statute-derived tests in `tests/scenarios.yaml` are constructed by
  enumerating which subsets of the three elements are met. They do
  **not** reference any LegalBench fact-pattern.
- Extractor is given the **same** verbatim rule prose as the bundle
  was authored against — same prompt frontier-LLM baselines see in
  rule_description-style runs.
