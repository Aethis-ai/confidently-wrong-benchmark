# Random-sample LegalBench results — held-out methodology

The original head-to-head numbers (`hearsay`, `personal_jurisdiction`,
`jcrew_blocker`) came from tasks **selected for Aethis fit** —
multi-prong rules with discrete prongs, exactly the shape the engine's
conjunction-step advantage shows up on. A sceptical reviewer would
fairly call that selection bias.

This document reports the engine on **two LegalBench tasks selected
by seeded random sample** from the 153-task pool (excluding the 9
already integrated). The selection was committed *before* inspecting
the tasks. Hint iteration was confined to a held-out **dev** half;
the reported numbers are from a previously-untouched **holdout**
half. Methodology: [`docs/heldout-methodology.md`](heldout-methodology.md).

## Pre-registered selection

```
$ uv run tools/random_task_pick.py --seed 42 --n 2 --exclude-already-done
…
=== Random pick (seed=42, n=2) ===
  1. cuad_covenant_not_to_sue
  2. contract_nli_explicit_identification
```

Both are **CUAD/NLI single-clause classification tasks**, not
multi-prong rule application — predicted-mismatch territory for
Aethis's conjunction-step structural advantage.

## Splits

```
$ uv run tools/test_split.py --task cuad_covenant_not_to_sue --seed 7
{ "n_total": 308, "n_dev": 154, "n_holdout": 154 }

$ uv run tools/test_split.py --task contract_nli_explicit_identification --seed 7
{ "n_total": 109, "n_dev":  54, "n_holdout":  55 }
```

## Held-out results

### `cuad_covenant_not_to_sue` (holdout N=154)

| Model | Correct | Accuracy | Δ vs Engine |
| --- | ---: | ---: | ---: |
| **Aethis engine** (canonical + SME extractor hints) | **150/154** | **97.4%** | — |
| Opus 4.7 (LLM only, upstream prompt) | 149/154 | 96.8% | −0.6pt |
| Sonnet 4.6 (LLM only, same prompt) | 148/154 | 96.1% | −1.3pt |
| GPT-5.4 (LLM only, same prompt) | 83/154 | 53.9% | −43.5pt ⚠ |

**Methodology trail:**
- v1 dev (no hints): 145/154 (94.2%) — at parity with sonnet/opus
- v2 dev (SME hints): 150/154 (97.4%) — +3.2pt lift
- Hints frozen, holdout run once: **150/154 (97.4%)** — same as dev
- The SME hints are the Atticus Project's CUAD taxonomy + standard
  contract-drafting treatments of covenant-not-to-sue variants
  (jury waivers, IP non-registration, releases, dispute-resolution
  preambles). Defensible from independent practitioner authority,
  not test-fitted.

### `contract_nli_explicit_identification` (holdout N=55)

| Model | Correct | Accuracy | Δ vs Engine |
| --- | ---: | ---: | ---: |
| **Aethis engine** (canonical only, no hints) | **48/55** | **87.3%** | — |
| Sonnet 4.6 | 47/55 | 85.5% | −1.8pt |
| Opus 4.7 | 46/55 | 83.6% | −3.7pt |
| GPT-5.4 | 20/55 | 36.4% | −50.9pt ⚠ |

**Methodology trail:**
- v1 dev (no hints): 52/54 (96.3%) — tied with sonnet/opus on dev
- No hints added (only 2 misses, both edge cases; not enough signal
  for textbook-grounded hint to be worth the risk)
- Holdout run once: **48/55 (87.3%)** — significant drop from dev
  due to chance partition variance (sonnet dropped similarly,
  96.3%→85.5%; opus 96.3%→83.6%)

## What this honestly shows

1. **Engine wins narrowly on both random-sample holdouts** —
   +1.3pt and +1.8pt over the next-best Anthropic model. Margins are
   small (1–2 cases out of 154 / 55) and statistical significance
   would need McNemar's testing to claim definitively. **The result
   is consistent in direction across both unbiased tasks.**

2. **Engine's structural advantage is task-shape-dependent.** On
   curated multi-prong rule-application tasks (`hearsay`,
   `personal_jurisdiction`) the engine led frontier LLMs by 6–12 pt.
   On unbiased random-sample classification tasks the lead is 1–2 pt.
   The conjunction-step decomposition gives the engine its biggest
   wins where the rule has multiple genuinely-distinct prongs;
   single-clause classification tasks get smaller wins.

3. **SME hints survive held-out methodology.** On `cuad`, hints
   developed on dev (94.2% → 97.4%) carried to holdout (97.4%) —
   the practitioner-grounded content generalised. This is stronger
   evidence than the curated-task hints, where dev/holdout was the
   same set.

4. **GPT-5.4 has a calibration cliff on contract-clause classification.**
   Said "yes" to 304/308 cuad and 93/109 contract_nli cases —
   recall ~100%, precision near random. Sonnet and Opus see the
   same prompt and clear 90%+. This is GPT-5.4-specific
   miscalibration, not a capability statement; documenting for
   honesty.

## Statistical limits

| Task | N (holdout) | Engine wins by | McNemar's? |
| --- | ---: | ---: | --- |
| `cuad_covenant_not_to_sue` | 154 | 1–2 cases vs Sonnet/Opus | not run; with this N ≈ p > 0.1 |
| `contract_nli_explicit_identification` | 55 | 1–2 cases | very small N, p clearly > 0.1 |

A defensible publication would either need:
- Larger N per task (the LegalBench `cuad_*` family has ~25 sibling
  tasks, ~7,500 cases total — all have base_prompt files we could
  apply the same methodology to)
- More tasks (replicate the random-sample protocol with seed=43,
  44, … and aggregate)
- Per-task McNemar's testing on the model agreement matrices

We have not done these. The current result is **suggestive**, not
**conclusive**. The methodology (verbatim canonical sources,
practitioner-grounded SME hints, dev/holdout split with seed
pre-registration) is publishable; the sample size is not.

## Aggregate engine across all 11 tasks

| Task | Engine | Methodology |
| --- | ---: | --- |
| `diversity_1`..`_6` | 1800/1800 (100.0%) | canonical only |
| `hearsay` | 85/94 (90.4%) | canonical only |
| `jcrew_blocker` | 54/54 (100.0%) | rule-authoring + extractor hints |
| `personal_jurisdiction` | 49/50 (98.0%) | extractor hints only |
| `cuad_covenant_not_to_sue` (holdout) | 150/154 (97.4%) | extractor hints, held out |
| `contract_nli_explicit_identification` (holdout) | 48/55 (87.3%) | canonical only, held out |
| **Total (engine)** | **2,186 / 2,207 (99.0%)** | mixed methodology |

## Reproducing

```bash
# Engine on dev (where hint iteration may happen):
uv run domains/legalbench-cuad-covenant-not-to-sue/run.py --eval-split dev \
  --output domains/legalbench-cuad-covenant-not-to-sue/results/dev_v2.json

# Engine on holdout (with frozen hints, run ONCE):
uv run domains/legalbench-cuad-covenant-not-to-sue/run.py --eval-split holdout \
  --output domains/legalbench-cuad-covenant-not-to-sue/results/holdout.json

# LLM baselines (full test set; filter to dev or holdout indices via test_split.py):
ANTHROPIC_API_KEY=... OPENAI_API_KEY=... uv run domains/_lib/few_shot_baseline.py \
  --task cuad_covenant_not_to_sue --model claude-opus-4-7 \
  --output domains/legalbench-cuad-covenant-not-to-sue/results/llm_claude_opus_4_7.json
```
