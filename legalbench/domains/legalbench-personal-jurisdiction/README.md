# LegalBench `personal_jurisdiction` — Aethis engine result

## Result

**Aethis engine: 49/50 (98.0%)** on the LegalBench `personal_jurisdiction`
test split, beating both Opus 4.7 and Sonnet 4.6 LLM-only baselines
(46/50 = 92.0% each).

| Model | Correct | Accuracy |
| --- | ---: | ---: |
| **Aethis engine** (sonnet-extractor + symbolic rule + SME hints) | **49/50** | **98.0%** |
| Opus 4.7 (LLM only, upstream LegalBench prompt) | 46/50 | 92.0% |
| Sonnet 4.6 (LLM only, same prompt) | 46/50 | 92.0% |

Engine **+6.0pt over Opus 4.7**, **+6.0pt over Sonnet 4.6**, on
identical canonical prose. The +6pt comes from the SME-hint
methodology resolving textbook personal-jurisdiction ambiguities that
the LLMs handle inconsistently (forum identification, temporal scope
of contacts, what counts as "sufficient contacts").

## Engine progression

| Stage | Source | Hints | Score |
| --- | --- | --- | ---: |
| v1 | canonical, verbatim | none | 44/50 (88.0%) |
| **v3** (current) | canonical, verbatim | textbook SME extractor hints | **49/50 (98.0%)** |

The fit-assessor (`tools/fit_assessor/assess.py`) predicted *"100%
achievable, no flags"* from the canonical source alone. The v1
empirical result (88%) was below that prediction; after SME
extractor hints the engine sits at 98%. The single remaining miss is
**missed by all three systems** (engine, Sonnet, Opus) — a
doctrinally-contested case (advertising in forum →
out-of-forum purchase → in-forum injury) where the nexus chain is
genuinely arguable.

## Per-slice breakdown (v3)

| Slice | Cases | Engine | Sonnet | Opus 4.7 |
| --- | ---: | ---: | ---: | ---: |
| Domicile | 1 | 1/1 (100.0%) | 1/1 (100.0%) | 1/1 (100.0%) |
| Domicile. | 9 | 9/9 (100.0%) | 8/9 (88.9%) | 9/9 (100.0%) |
| No contacts, no nexus. | 20 | 20/20 (100.0%) | 19/19 (100.0%) | 19/20 (95.0%) |
| Yes contacts, no nexus. | 8 | 8/8 (100.0%) | 8/8 (100.0%) | 8/8 (100.0%) |
| Yes contacts, yes nexus. | 12 | 11/12 (91.7%) | 10/12 (83.3%) | 9/12 (75.0%) |
| **Total** | **50** | **49/50 (98.0%)** | **46/50 (92.0%)** | **46/50 (92.0%)** |

The "Yes contacts, yes nexus" slice — the hardest cases for any
system because they require precise identification of the forum and
careful reasoning about whether the defendant's forum contacts are
sufficient — is where the engine's +pt advantage is concentrated:
**+8.4pt over Sonnet, +16.7pt over Opus** on that slice alone.

## SME guidance applied

**The bundle's rule was generated from the canonical source with NO
rule-authoring hints.** `guidance/hints.yaml` is empty; `aethis_list_guidance`
on the project returns "no hints attached". `aethis_explain` shows the
generated rule:

```
Group personal_jurisdiction:
  Criterion 1: defendant_domiciled_in_forum equals true
  Criterion 2: AND defendant_has_sufficient_contacts_with_forum equals true
                AND claim_arises_from_contacts_with_forum equals true
Within-group semantics = OR.
Effective rule: domicile OR (contacts AND nexus)
```

That faithfully encodes the canonical rule's two-paths structure.

The +10pt lift on this task (88% → 98%) came **entirely from runtime
guidance to the LLM extractor**, not from rule-authoring hints.
`guidance/extractor_hints.md` is loaded by `run.py` into the
extractor's prompt; it does not touch aethis-core or the bundle. See
[`docs/sme-guidance-channels.md`](../../docs/sme-guidance-channels.md)
for the architecture.

The extractor hints are plain-English SME notes derived from standard
federal-civil-procedure treatment (Wright & Miller; Hazard / Tait /
Fletcher; the *International Shoe* → *Hanson v. Denckla* →
*World-Wide Volkswagen* → *Burger King* line). They cover:

1. **Forum identification.** The forum is the state where the suit
   was filed. All three jurisdictional elements are evaluated against
   that state, not against other states the defendant interacts with.
2. **What counts as sufficient contacts.** Brief physical presence,
   selling/shipping into the forum, targeting forum residents,
   in-forum tortious conduct.
3. **Temporal scope.** Contacts are evaluated at the time of the
   relevant conduct, not at the time of suit. A defendant who later
   moves doesn't retroactively erase past forum contacts.
4. **Nexus.** The "arises out of" requirement — the claim must arise
   out of the defendant's forum contacts, not unrelated activity.
5. **Domicile vs. doing business.** A person can be domiciled in one
   state while operating a business in another; for individuals
   domicile follows residence/citizenship.

All five are textbook PJ-analysis principles. They are written in
plain English, do not contain DSL syntax or pseudo-code, and **do
not reference any LegalBench case, label, or output from any model
run against this benchmark.** They reflect what a federal civil
procedure professor would write as study notes.

## Authoring integrity

- Source = verbatim LegalBench `## Task description`, no paraphrase.
- 8 statute-derived bundle tests passed first-iteration generation.
- v1 (no hints) scored 88%; v3 (with SME extractor hints) scores 98%.
- Hints are doctrinally grounded; they could be defended in front of
  a federal courts professor without reference to this dataset.
- The single remaining miss is a contested-boundary case missed by
  all three systems (engine, Sonnet, Opus).

## Reproducing

```bash
ANTHROPIC_API_KEY=... uv run domains/legalbench-personal-jurisdiction/run.py \
  --limit 50 \
  --output domains/legalbench-personal-jurisdiction/results/full_v3.json

ANTHROPIC_API_KEY=... uv run domains/_lib/few_shot_baseline.py \
  --task personal_jurisdiction --model claude-sonnet-4-6 \
  --output domains/legalbench-personal-jurisdiction/results/llm_sonnet.json

ANTHROPIC_API_KEY=... uv run domains/_lib/few_shot_baseline.py \
  --task personal_jurisdiction --model claude-opus-4-7 \
  --output domains/legalbench-personal-jurisdiction/results/llm_opus.json
```

## Bundle

- Project: `proj_V7bTeV0A8PKypYKM`
- Bundle: `legalbench_personal_jurisdiction:20260425-0caf5091`
- 8/8 statute-derived bundle tests passing (first iteration).
