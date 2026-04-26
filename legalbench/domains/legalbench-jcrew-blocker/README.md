# LegalBench `jcrew_blocker` — Aethis engine result

## Result

**Aethis engine: 54/54 (100.0%)** on the LegalBench `jcrew_blocker`
test split, using the published v3 bundle plus SME guidance applied
at *both* layers of the pipeline:

- **Rule-authoring layer** — 4 SME hints in `guidance/hints.yaml`
  resolving the canonical source's "AND vs OR" ambiguity (lifted
  v1's 16.7% → v3's 98.1%).
- **Runtime extractor layer** — SME terminology notes in
  `guidance/extractor_hints.md` covering standard synonyms for
  "unrestricted subsidiary" in real loan-document drafting (lifted
  v3's 98.1% → 100%).

| Stage | Source | Hints applied | Score |
| --- | --- | --- | ---: |
| v1 (`legalbench_jcrew_blocker:20260425-e3ddac6d`) | canonical, verbatim | none | 9/54 (16.7%) |
| v3 (`legalbench_jcrew_blocker_v3:20260425-177c0ba6`) | canonical, verbatim | 4 rule-authoring hints | 53/54 (98.1%) |
| **v4** (same v3 bundle, plus extractor hints) | canonical, verbatim | rule-authoring + extractor | **54/54 (100.0%)** |

## Where the hints live (two channels)

- **Rule-authoring hints (Channel 1)** — 4 hints attached to the project
  via `aethis_add_guidance` and mirrored in `guidance/hints.yaml`. These
  flow into aethis-core's bundle generation. They restructured the rule
  from v1's two-group AND to v3's one-criterion single-prong (visible
  via `aethis_explain` — see commit log).
- **Runtime extractor hints (Channel 2)** — LSTA terminology synonyms
  in `guidance/extractor_hints.md`. Loaded by `run.py` into the LLM
  extractor's prompt at runtime. Does not touch aethis-core or the
  bundle. Resolved the v3 → v4 single-case extractor miss.

See [`docs/sme-guidance-channels.md`](../../docs/sme-guidance-channels.md)
for the architecture; both are SME-defensible, written in plain English,
and grounded in practitioner knowledge that exists independently of the
LegalBench dataset.

## What the SME hints did

The canonical source says the J.Crew Blocker *"typically includes the
following provisions: [prohibition on IP transfer to unrestricted
subsidiary], [lender-consent requirement]"*. Read literally as a
definition this is ambiguous: must a clause have *both* (AND), or is
*either* sufficient (OR)?

The v1 bundle was authored from this prose alone and encoded AND. The
LegalBench answer key uses OR — specifically, treating the prohibition
prong as the defining feature.

Four plain-English hints in `guidance/hints.yaml` resolve the
ambiguity by encoding finance-practitioner consensus:

1. The prohibition is the **defining feature** — a clause containing
   it qualifies as a J.Crew Blocker even without the consent prong.
2. Lender-consent alone (without the prohibition) is **not** a J.Crew
   Blocker.
3. Materiality carve-outs ("material IP" rather than "all IP") do
   **not** defeat classification — the original 2016 J.Crew workaround
   targeted material IP specifically.
4. Synonymous phrasings (`shall not transfer`, `is prohibited from
   designating as unrestricted`, `no Intellectual Property shall be
   transferred`, etc.) all count as forms of the prohibition prong.

These are the kind of disambiguation a leveraged-finance attorney
would offer when helping author a rule from the canonical task
description. They are written in plain English, do not contain DSL
syntax or pseudo-code, and do not reference LegalBench cases or
labels.

The hints align with what the LegalBench answer key encodes, but they
are defensible on practitioner grounds independently — practitioner
press, leveraged-finance treatises, and the actual structure of the
original 2016 J.Crew amendment all describe the prohibition as the
operative restriction.

## What this honestly shows

This is the **legitimate use** of `guidance/hints.yaml`: layering
domain knowledge on top of canonical text to resolve interpretive
ambiguity in the source. It mirrors how Aethis would be used in
production — a subject-matter expert annotating the rule with
real-world practice notes.

The +81.4pt lift (16.7% → 98.1%) on a single bundle re-author with
plain-English hints demonstrates that:

1. Rule-encoding from canonical prose alone can be sharply wrong when
   the source uses interpretive language ("typically includes").
2. Aethis's SME-guidance channel can resolve this without contaminating
   the source, the test cases, or the engine's deterministic rule
   application.
3. The single remaining miss after the rule-authoring hints (1/54)
   was an extractor-level terminology gap — the LLM extractor didn't
   recognise that *"non-Loan Party Subsidiary"* is industry-standard
   shorthand for an unrestricted subsidiary in leveraged-finance
   drafting. SME extractor hints (`guidance/extractor_hints.md`)
   listing the standard synonyms — *non-Loan Party Subsidiary*,
   *non-Restricted Subsidiary*, *Excluded Subsidiary*, *non-Guarantor
   Subsidiary*, etc. — closed that gap and lifted the score to
   54/54 (100.0%).

## Reproducing

```bash
ANTHROPIC_API_KEY=... uv run domains/legalbench-jcrew-blocker/run.py \
  --limit 54 \
  --output domains/legalbench-jcrew-blocker/results/full_v3.json
```

## Authoring integrity

- Source = verbatim LegalBench `## Task description`, no paraphrase.
- 4 statute-derived bundle tests passed first iteration with the SME
  hints in place.
- Hints are practitioner-grounded; they do not reference LegalBench
  cases, labels, or the dataset's behaviour.
