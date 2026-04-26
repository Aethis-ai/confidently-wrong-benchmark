# v3.8 Stream A reproducibility report

Run date: 2026-04-26.
Harness: `tools/replication_run.py` using paper's exact `_build_prompt`
format from `confidently-wrong-benchmark/benchmarks/run_llm_comparison.py`.

## Headline

The v3.6 / v3.7 paper documented LLM failures that have largely **closed**
in current frontier models. The §6 controlled-benchmark headline ("no
frontier model achieves 100% across all four paper domains") is
salvageable through Sonnet 4.6, but the lead-case failure (GPT-5.4 96.6%
on construction) does not replicate. Multiple paper cells need updating.

## Per-cell comparison (paper claim → v3.8 replication)

| Model | Domain | Paper (v3.6/v3.7) | v3.8 today | Status |
|---|---|---|---|---|
| GPT-5.4 default | construction (full 58/74) | 56/58 (96.6%) | **74/74 (100%)** | ❌ does not replicate |
| GPT-5.4 default | construction exception_chain (n=11) | 10/11 (90.9%) | **11/11 (100%)** | ❌ does not replicate |
| GPT-5.4 `reasoning_effort=low` | construction exception_chain (n=11) | 7/11 (63.6%) | **11/11 (100%)** | ❌ already retracted (v3.8 polish) |
| GPT-5.3 default | construction exception_chain (n=11) | 7/11 (63.6%) | **API 404** | model alias deprecated by OpenAI |
| GPT-4.1-mini | construction (full 58/74) | 46/58 (79.3%) | **65/74 (87.8%)** | ⚠ partial — direction holds, magnitude shifted |
| Claude Opus 4.6 | spacecraft (n=68) | 61/68 (89.7%) | **67/68 (98.5%)** | ❌ much better today than paper |
| Claude Opus 4.6 | construction (full 58/74) | not tested | **74/74 (100%)** | new data — perfect |
| Claude Sonnet 4.6 | spacecraft (n=68) | 62/68 (91.2%) | **60/68 (88.2%)** | ✓ approximately replicates (slightly worse) |
| Claude Sonnet 4.6 | construction (full 58/74) | not tested | **72/74 (97.3%)** | new data |
| Claude Opus 4.7 | construction (full 58/74) | not tested | **74/74 (100%)** | new data — perfect |
| Claude Opus 4.7 | spacecraft (n=68) | not tested | **68/68 (100%)** | new data — perfect |

## What still demonstrates LLM failure today

1. **GPT-4.1-mini** still fails on 9 of 74 construction scenarios. Failure pattern concentrates on:
   - `neg_de3_double_negative`, `neg_triple_not_de3_pass` (negation_stacking)
   - `surface_eligible_design_access_blocks`, `surface_ineligible_de3_saves` (contradictory_cue)
   - `ultimate_trap_1` (multi-failure)
   - `access_100m_design_not_covered`, `access_200m_design_not_covered`, `adv_case_c_at_200m_design` (depth-5 design defect)
   - `carveback_de3_only`
2. **Sonnet 4.6** still fails on 2 of 74 construction (`access_100m_design_not_covered`, `surface_eligible_design_access_blocks`) and 8 of 68 spacecraft scenarios.
3. **Opus 4.6** fails 1 of 68 spacecraft (`age_60_orbital_999hrs_licensed`).
4. **Opus 4.7 and GPT-5.4 are perfect** on the existing controlled benchmark.

## Implications for paper

### What's broken in the v3.7 paper

- Abstract sentence "GPT-5.4 — the strongest frontier model tested — drops to 96.6% on the construction insurance benchmark" — wrong. Today GPT-5.4 is 100%.
- §6.4 Table 8a: GPT-5.4 56/58 (96.6%) and GPT-4.1-mini 46/58 (79.3%) — current numbers different.
- §6.4 Table 7: "Access, £500M, design — GPT-5.4 ✗" — today GPT-5.4 returns `eligible` (correct).
- §6.4 narrative: "GPT-5.4 fails on the pioneer override boundary" — no longer true.
- §6.5 Finding 4: "GPT-5.4 ... drops to 96.6% on the construction insurance section" — wrong.
- §6.5 Finding 5 / §6.7 R5 — already withdrawn in v3.8 polish.
- §6.7 R1 (Opus 4.6 70-trial 0/70 on 7 failing spacecraft): the "7 failing" set itself doesn't replicate at the paper's claimed rate (Opus 4.6 today is 1/68 wrong, not 7/68). The 0/70 trial finding probably also doesn't replicate; A6 verification was contingent and is moot now.

### What stands

- **§6.10 LegalBench** — fully reproducible, results unchanged; *p* < 0.001 vs Sonnet 4.6 and GPT-5.4, *p* = 0.003 vs Opus 4.7. Now the load-bearing claim.
- **Sonnet 4.6 still fails** in places — the paper's frontier-LLM-fails framing can re-anchor here.
- **GPT-4.1-mini still fails** — cost-tier baseline is still informative.
- **Engine 100% across all benchmarks** — invariant.
- **§6.7 R2 (Opus 4.6 prompt-repair 89.7% → 64.7%)** — separate test, not run in this Stream A pass; status TBD (would need re-running).

## Recommended v3.8 §6 framing

1. Lead with §6.10 LegalBench as the contemporary demonstration.
2. Present §6 controlled benchmark as "documented in March 2026; by April 2026 frontier models had closed several specific cells but the structural advantage of deterministic execution remains; current Sonnet 4.6 still fails 2/74 construction and 8/68 spacecraft, GPT-4.1-mini still fails 9/74."
3. Update Tables 6, 8a with v3.8 numbers; mark v3.6/v3.7 numbers as historical.
4. Withdraw / rewrite Finding 4 and Finding 5 (Finding 5 already withdrawn).
5. Note the broader lesson explicitly: "frontier models have improved on these specific failure cases since the original test; the paper's contribution is the *architectural* claim (deterministic execution wins by construction), not the *transient empirical finding* (specific frontier-model failures)."

## What's missing for full picture

- A6 (Opus 4.6 70-trial on 7 spacecraft) — moot if Opus 4.6 doesn't replicate the 7-failure set today (it doesn't; only 1 wrong).
- A7 (Opus 4.6 prompt-repair 68 spacecraft × 1 run with the §6.7 R2 enhanced prompt) — would tell us if R2 still holds. The "enhanced prompt" itself isn't in the committed harness; would need to be reconstructed. Optional.

## Cost / time

API spend total: ~$5 (mostly Anthropic Opus calls; gpt-5.3 returned errors).
Wall clock: ~5 minutes for all 8 background tasks running in parallel.
Cheaper than estimated.
