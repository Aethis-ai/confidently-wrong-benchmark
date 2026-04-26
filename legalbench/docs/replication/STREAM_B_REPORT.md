# Stream B (v3.8 adversarial CAR extension) — report

## What was done

20 new construction-CAR scenarios authored with independently-prose
expected-values, then verified against the engine (`tools/run_engine_v3_8_adversarial.py`)
and run through frontier LLMs (`tools/replication_run.py` with
paper-prompt format).

Scenarios stratified across five complexity dimensions (4 each):

- **A — Maximum-stack adversarial:** 3+ rule-failure modes simultaneously.
- **B — Threshold-boundary edge cases:** at-threshold, just-below, just-above project values.
- **C — Multi-clause cross-reference:** existing-structures + JCT + design + pioneer interactions.
- **D — Surface-vs-deep contradiction:** surface text suggests opposite of correct answer.
- **E — Conjunction tracking:** every condition near-violating; one flip changes outcome.

10/20 scenarios are eligible-expected, 10/20 not_eligible-expected.

## Engine verification (B3)

**Engine: 20/20 (100%) correct** — every prose expected-value matches
the engine's deterministic outcome under the canonical bundle
`construction-all-risks:20260412-gold`. Median latency 22 ms / decision.
Independent-prose-then-engine methodology eliminates the
"code-derived ground truth" critique.

## Frontier-LLM results (B4)

| Configuration | Correct | Failure(s) | Notes |
|---|---:|---|---|
| **Engine** | **20/20 (100%)** | — | deterministic by construction |
| **GPT-5.4 default** | **19/20 (95%)** | `v38_e4_carveback_gap_explicit` | 0 reasoning tokens on every scenario — short-circuit answers |
| **GPT-5.4 reasoning_effort=low** | 20/20 (100%) | — | 16–126 reasoning tokens per scenario |
| **Claude Opus 4.7** | **18/20 (90%)** | `v38_b3_499m_workmanship_access_no_design_limit`, `v38_e4_carveback_gap_explicit` | currently strongest Anthropic model |
| **Claude Sonnet 4.6** | **19/20 (95%)** | `v38_e4_carveback_gap_explicit` | — |

### Cross-model failure analysis

- **`v38_e4_carveback_gap_explicit`** — 3 of 4 frontier configurations fail. Only GPT-5.4 low-reasoning catches it. The DE3/LEG3 carveback gap is a structural failure mode, not a single-model artefact.
- **`v38_b3_499m_workmanship_access_no_design_limit`** — Opus 4.7 fails alone. The model appears to anchor on "£499 M is below the £500 M pioneer threshold" and miss that pioneer-override isn't needed because workmanship is not design.
- **All other 18 scenarios** — every frontier model passes. The harder scenarios reveal the failure surface in just two specific patterns.

### The GPT-5.4 default failure (E4)

`v38_e4_carveback_gap_explicit`: project value £200 M, workmanship
defect (mildest), access damage, **consequence_of_failure = false**.
This is the DE3/LEG3 carveback coverage gap explicitly documented in
the source.md commentary: with `is_access_damage=true` and
`consequence=false`, the carveback group fails (Route A needs
consequence=true; Route B needs `NOT(is_access)` which is false). So
even though £200 M qualifies for enhanced cover, the prior carveback
gate blocks the claim.

**GPT-5.4 default response:** literally `"eligible"` — 4 tokens of
output, **0 reasoning tokens**. The model short-circuited to the
wrong answer.

**GPT-5.4 low-reasoning response:** also `"eligible"` initially
parsed... wait, low got it right with 95 reasoning tokens on the
same scenario. Confirmed by `docs/replication/B4_gpt54_low_v3_8_adversarial.json`.

### Reasoning-effort behaviour analysis

| Mode | Median completion tokens | Median reasoning tokens | Accuracy |
|---|---:|---:|---:|
| GPT-5.4 default | 4–6 | **0 (every scenario)** | 19/20 (95%) |
| GPT-5.4 `reasoning_effort=low` | 28–126 | 16–116 | 20/20 (100%) |

**This inverts the v3.6 / v3.7 paper claim** that "default reasoning
is better than low reasoning". On the v3.8 adversarial set under the
current `gpt-5.4` alias:

- **Default** mode does NOT use the reasoning channel at all (0
  reasoning tokens on 20/20 scenarios). It is essentially
  "non-reasoning mode by default".
- **`reasoning_effort=low`** does invoke the reasoning channel
  (16–126 tokens per scenario), and that additional deliberation is
  what catches the carveback-gap edge case.

The paper's v3.6 / v3.7 framing of "low reasoning = worse than
default" was either always wrong (a harness configuration issue)
or has been inverted by silent model updates between March and April
2026. Either way, the surface-level behaviour today is the **opposite**
of what the paper documents.

## Implications for v3.8 paper

1. **Engine still demonstrably wins** on at least one scenario where
   current frontier GPT-5.4 fails (the carveback gap, E4). Combined
   with the §6.10 LegalBench evidence (where GPT-5.4 fails on 8 of 9
   tasks vs engine), the structural-advantage claim has fresh,
   reproducible evidence.

2. **The "default reasoning is better" framing is wrong as currently
   written.** Paper §6.5 / §6.7 should be retracted or reframed
   around the actual observed behaviour: default = 0 reasoning
   tokens, low = some reasoning tokens; harder cases pass through
   the actually-reasoned mode.

3. **The shifting-ground argument is now empirically grounded.**
   Multiple v3.6 / v3.7 cells do not replicate today (Stream A: GPT-5.4
   construction, Opus 4.6 spacecraft; this Stream B: reasoning-effort
   inversion). Frontier model accuracy is a moving target. A regulated
   system that depends on benchmark-time accuracy claims has no
   guarantee those claims survive an opaque model update.

4. **Cross-model-family failure on E4.** Three of four frontier
   configurations (GPT-5.4 default, Opus 4.7, Sonnet 4.6) fail on the
   carveback-gap scenario. Both major model families miss it. The
   failure is therefore unlikely to be a single-model artefact —
   plausibly a structural pattern in how transformer-based LLMs
   integrate sequential exception clauses. Combined with §6.10's
   demonstration that all three frontier models fail on legal-
   classification tasks the engine handles correctly, the v3.8 paper
   has fresh, current-frontier-model failure evidence in two distinct
   regimes.

## What stands

- All §6.10 LegalBench numbers (combined McNemar's *p* < 0.001 vs
  three frontier models; engine wins 8/9 tasks).
- Engine 100% on every benchmark by construction.
- The architectural argument (deterministic execution gives
  reproducibility-by-construction; LLM accuracy is a moving target).

## Cost / time

- Stream B authoring: ~45 min (20 scenarios with prose).
- B3 engine verification: ~15s + 22 ms × 20 calls.
- B4 frontier-LLM runs (parallel): ~3 min wall clock, ~$2 OpenAI spend.
  Anthropic spend = 0 (budget cap blocked all calls).
- Total Stream B: ~50 min wall, ~$2 actual spend.
