# LLM vs Deterministic Engine: Per-Domain Results

> See the [main README](../README.md) for the headline benchmark table.

## Evaluation: 2026-04-12

LLM evaluation covers 172 scenarios across three domains (spacecraft 68, construction 74, benefits entitlement 30).
The remaining 99 scenarios (life_uk 56, english_language 43) are engine-only — LLM comparison not run on depth ≤ 2 domains.
Total benchmark: 271 scenarios across 5 domains (up from 225 across 4 in v3.6).
All models tested with full source text, no truncation, no pattern hints.
Engine bundle: gold-standard fixture (hand-authored, not LLM-generated).

### Spacecraft Crew Certification — 68 scenarios, depth 3

| Model | Accuracy | Consistent (3 runs) |
|-------|:--------:|:-------------------:|
| **Aethis Engine** | **68/68 (100%)** | **100%** |
| GPT-5.4 | 68/68 (100%) | 100% |
| Claude Opus 4.6 | 67/68 (99%) | 100% |
| Claude Sonnet 4.6 | 59/68 (87%) | — |
| GPT-5.4-mini | 67/68 (99%) | — |

Opus gets 1 wrong but gives the same wrong answer every time (confidently wrong).

### Construction All Risks — 74 scenarios, depth 5

| Model | Accuracy | Consistent (3 runs) |
|-------|:--------:|:-------------------:|
| **Aethis Engine** | **74/74 (100%)** | **100%** |
| GPT-5.4 | 74/74 (100%) | 100% |
| Claude Opus 4.6 | 73/74 (99%) | 99% (73/74) |
| Claude Sonnet 4.6 | 72/74 (97%) | — |
| GPT-5.4-mini | 63/74 (85%) | — |

GPT-5.4-mini drops to 85% on the 5-level exception chain — 11 failures concentrated
on the access damage / enhanced cover / pioneer override logic.

### Benefits Entitlement — 30 scenarios, depth 3

| Model | Accuracy | Boundary (8) | Consistent (3 runs) |
|-------|:--------:|:------------:|:-------------------:|
| **Aethis Engine** | **30/30 (100%)** | **8/8 (100%)** | **100%** |
| Claude Opus 4.6 | 29/30 (97%) | 8/8 (100%) | 100% |
| GPT-5.4 | 28/30 (93%) | 7/8 (88%) | 29/30 (97%) |

Both frontier models fail `refugee_high_income_not_eligible`: a refugee (exempt from
habitual residence only) with weekly income of £400 above the £350 threshold.
Both confidently return eligible — 0/3 correct across all runs — treating the
immigration exemption as a general override rather than one scoped to condition 3.

## Temporal stability note

These results differ materially from the 2026-04-06 evaluation on the same scenarios
with the same model identifiers:

| Model | Spacecraft (Apr 6) | Spacecraft (Apr 12) | Delta |
|-------|:------------------:|:-------------------:|:-----:|
| Opus 4.6 | 90% | 99% | +9% |
| Sonnet 4.6 | 91% | 87% | -4% |
| GPT-5.4-mini | 75% | 99% | +24% |
| GPT-5.4 | 100% | 100% | — |
| Engine | 100% | 100% | — |

No prompts, scenarios, or API parameters changed. The model weights behind the
identifier shifted silently. The engine's compiled rules are immutable — same
bundle, same result, any date.

## Previous evaluation: 2026-04-06

Retained for comparison. 58 construction scenarios (pre-expansion), 11-scenario
exception chain subset.

| # | Test | Expected | GPT-5.4 | Opus | Sonnet | Mini | Engine |
|---|------|----------|---------|------|--------|------|--------|
| 1 | Rectification — absolute exclusion | not_eligible | Pass | Pass | Pass | Pass | Pass |
| 2 | Consequential damage — carve-back | eligible | Pass | Pass | Pass | Pass | Pass |
| 3 | Access damage, standard project | not_eligible | Pass | Pass | Pass | Pass | Pass |
| 4 | Access damage, enhanced (£150M) | eligible | Pass | Pass | Pass | Pass | Pass |
| 5 | Design defect, enhanced | not_eligible | Pass | Pass | **Fail** | **Fail** | Pass |
| 6 | Design defect, pioneer (£600M) | eligible | Pass | Pass | Pass | Pass | Pass |
| 7 | Plant equipment — excluded | not_eligible | Pass | Pass | Pass | Pass | Pass |
| 8 | Late notification | not_eligible | Pass | Pass | Pass | Pass | Pass |
| 9 | Pioneer + known defect — blocked | not_eligible | Pass | Pass | Pass | Pass | Pass |
| 10 | Pioneer + known + engineer — unblocked | eligible | Pass | Pass | Pass | **Fail** | Pass |
| 11 | Pioneer + defect not known | eligible | Pass | Pass | Pass | Pass | Pass |

## Reproduce

```bash
cd benchmarks

# Engine accuracy (no LLM keys needed, requires AETHIS_API_KEY for rate limits)
uv run run_engine_tests.py ../dataset/spacecraft-crew-certification/ --api-key $AETHIS_API_KEY
uv run run_engine_tests.py ../dataset/construction-all-risks/ --api-key $AETHIS_API_KEY --bundle-id construction-all-risks:20260412-gold

# LLM comparison (requires OPENAI_API_KEY + ANTHROPIC_API_KEY)
uv run run_llm_comparison.py ../dataset/spacecraft-crew-certification/ --api-key $AETHIS_API_KEY
uv run run_llm_comparison.py ../dataset/construction-all-risks/ --api-key $AETHIS_API_KEY --bundle-id construction-all-risks:20260412-gold

# Consistency (3 runs per test)
uv run run_llm_comparison.py ../dataset/spacecraft-crew-certification/ --api-key $AETHIS_API_KEY --models gpt-5.4 claude-opus-4-6 --runs 3
```
