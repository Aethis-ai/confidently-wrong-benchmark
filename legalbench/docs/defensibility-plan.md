# Defensibility plan — hardening the LegalBench results for peer review

This is the plan to take the current LegalBench work from "defensible to a
friendly reviewer / sales prospect" to "defensible at a top-tier venue
peer review", *and* to integrate the strongest pieces into the existing
"Confidently Wrong" white paper (Simpson et al. 2026, v3.7).

It's structured by effort and dependency: cheap statistical work first,
then targeted replication, then the integration call.

## Current state — what we have, what we don't

| What we claim | Strength of evidence | What's missing |
| --- | --- | --- |
| Engine encodes statutory rules cleanly from canonical text | Strong (verifiable via `aethis_explain`) | — |
| Conjunction-step structural advantage on multi-prong tasks | Strong direction, **3 tasks** (hearsay, PJ, jcrew) | Held-out validation; significance testing |
| Engine wins on unbiased random sample | Real but **1–2 case margin**, **n=2 tasks** | More random tasks; significance testing; replication seeds |
| Held-out methodology survives hint iteration | Cleanly demonstrated, **n=1 task** (cuad) | Replication on 2–3 more tasks |
| Two-channel SME guidance (rule-authoring + extractor) | Demonstrated on jcrew (rule-shape change) and PJ (extractor-only) | — |
| GPT-5.4 calibration cliff on classification tasks | 2 tasks confirm | Untested with alternative prompt strategies |

What a hostile peer reviewer would still flag:
1. Curated-task hint iteration was on the full test split (no held-out)
2. Random-sample N is too small (2 tasks, 1–2 case wins)
3. No significance testing reported
4. Cross-extractor experiment missing (sonnet-as-extractor only)
5. GPT-5.4 anomaly is prompt-coupled

## Phase 1 — Statistical hardening (cheap, ~1 day, no token spend)

**Goal:** put numbers on every claim. Most of this is just code over the per-case JSON files we already have.

1. **Per-task Wilson confidence intervals** on every accuracy number reported. The white paper already does this (e.g. §6.3 reports CI [80.2%, 94.9%]). Match that style.
2. **McNemar's test on per-case agreement matrices** between engine and each LLM, per task. Publish the b/c/χ²/p table.
3. **Effect-size analysis** (Cohen's h or McNemar odds ratio) — gives reviewers a sense of magnitude beyond raw accuracy delta.
4. **Aggregate analysis where appropriate** — e.g. random-sample tasks combined (paired binomial test on engine-wins-LLM-loses cases).
5. **Per-slice analysis** for tasks that have slices (hearsay, PJ) — currently in READMEs but not in paper-ready format.

Deliverable: `tools/significance.py` and a `docs/statistical-summary.md` with the full tables.

Cost: zero LLM tokens. ~1 day.

## Phase 2 — Held-out methodology applied retroactively (~$0–1, ~1 day)

**Goal:** address the "hint iteration on full test split" critique on the curated tasks where the strongest claims live.

1. For each of `hearsay`, `personal_jurisdiction`, `jcrew_blocker`:
   - Generate dev/holdout split (`tools/test_split.py --task X --seed 7`)
   - Re-run engine on held-out indices using existing frozen hints (no token cost — engine extractor cache is keyed by `(model, prompt_hash)` so previously-seen cases are free; only the few that haven't been read get fresh extraction)
   - Re-run LLM baselines from cached results, filtered to held-out indices (zero tokens, all cached)
   - Report holdout numbers alongside the existing full-test numbers
2. Honest framing: *"the hints were iterated on the full test set but the same fixed-hint configuration scores X on a held-out half not used for iteration"* — mitigates but doesn't fully eliminate the soft test-set fit.

Deliverable: holdout JSON for each task; updated README sections.

Cost: <$1 in extraction (most cases already cached). ~1 day.

## Phase 3 — Random-sample replication (~$5–10, ~2 days)

**Goal:** address the "n=2 random tasks" critique. Replicate the held-out protocol with multiple seeds.

1. `tools/random_task_pick.py --seed 43 --n 2` and `--seed 44 --n 2` — pre-registered, committed before authoring. 4 more random tasks (potentially overlapping with already-done; if so, increase n until 4 fresh tasks).
2. For each new task: scaffold, author bundle from canonical Task description, run engine on dev → consider hints (using textbook authority only) → run held out.
3. Run sonnet + opus + gpt-5.4 baselines on each.
4. Report aggregate across the now 6 random-sample tasks.

Why this matters: with 6 random tasks, *consistent* engine wins (even at 1–2 case margins each) becomes statistically meaningful via combined paired-binomial analysis.

Deliverable: 4 new task projects under `domains/legalbench-*/`, full LLM head-to-head per task, aggregate stats.

Cost: ~$5–10 in LLM tokens (3 models × ~150 cases × 4 tasks). ~2 days.

## Phase 4 — Cross-extractor experiment (~$3, ~1 day)

**Goal:** disentangle "split pipeline vs end-to-end" from "this model vs that model".

Currently the engine path uses sonnet as extractor. The LLM-only baseline uses each model end-to-end. A reviewer reads this as: *"you compared `sonnet-extractor + symbolic engine` vs `that-model end-to-end` — which model is doing the conjunction step matters."*

The clean experiment: run engine with **opus as extractor** and **gpt-5.4 as extractor**. Then we have a 3×3 grid:

|  | sonnet ext. | opus ext. | gpt-5.4 ext. |
|---|---|---|---|
| + symbolic engine | (current) | new | new |
| end-to-end LLM | (have) | (have) | (have) |

If `opus-extractor + engine` ≥ `opus-end-to-end`, the win is structural (the symbolic engine matters). If `opus-extractor + engine` < `sonnet-extractor + engine`, the win is partly model-specific (opus extracts worse than sonnet for some reason).

Run on hearsay (94 cases) + personal_jurisdiction (50 cases) — the two tasks with the cleanest existing structural advantage. ~$3 spend.

Deliverable: head-to-head matrix per task; honest discussion of what's structural vs model-coupled.

Cost: ~$3. ~1 day.

## Phase 5 — Cuad-family extension (~$15–20, ~3 days)

**Goal:** proper N. The cuad_* family on LegalBench has ~25 sibling tasks (covenant_not_to_sue, anti_assignment, change_of_control, etc.) all with similar structure (clause classification with practitioner-defined categories), each with 50–500 cases. Total ~7,500 cases.

If we apply the held-out methodology to even 5–10 cuad_* sibling tasks:
- Sample size jumps to ~3,000+ test cases
- Cross-task aggregation gives proper statistical power
- The CUAD/Atticus taxonomy hint approach we developed for `cuad_covenant_not_to_sue` may transfer

Risks: this is more work. Each task needs its own bundle, extractor field schema, runner. Some might not fit the conjunction-step pattern at all (single-prong classification).

Deliverable: 5–10 new domain projects, aggregate held-out result on 1,500–3,000 cases.

Cost: ~$15–20. ~3 days.

## Phase 6 — Integration with the white paper (decision point, dependent on 1–4)

**Goal:** decide how the LegalBench work feeds into the v3.7 paper.

Three paths:

### Path A — Add to v3.7 as new Section 6.10 "External Validation on LegalBench"

Insert a new subsection in §6 (Accuracy Benchmark) reporting the LegalBench results as **external validation** of the architecture's generalisation beyond Aethis-internal benchmarks. Keep the paper's core 100% / 225-scenario story unchanged; add LegalBench as the cross-benchmark cross-check.

What goes in:
- 6.10.1: 11 LegalBench tasks integrated, aggregate engine 99.0%
- 6.10.2: Multi-prong task wins (hearsay +12pt over Sonnet, +7pt over Opus, +12pt over GPT-5.4; PJ +6pt; jcrew 100%) — with Wilson CIs and McNemar's
- 6.10.3: Random-sample replication (cuad + NLI + 4 more from Phase 3) — confirms direction, narrower margins
- 6.10.4: Cross-model consistency — failure pattern documented in main paper extends to OpenAI family
- 6.10.5: Cross-extractor analysis (Phase 4) — disentangles structural vs model-specific

What needs Phase 1–4 to land first:
- Wilson CIs (Phase 1)
- McNemar's tables (Phase 1)
- Random-sample replication beyond n=2 (Phase 3)
- Cross-extractor disentanglement (Phase 4)

Pros: keeps the paper's argument unified; LegalBench is genuinely the right complement; the v3.7 paper's "pre-registered replication" framing in §6.9 dovetails naturally.

Cons: requires the paper's authors to agree to a v3.8 revision; extends the paper.

### Path B — Companion paper (separate submission, citing v3.7)

Title: *"External replication of the exception-chain failure pattern on LegalBench: cross-benchmark validation of the Aethis Eligibility Module"*

What goes in: same content as Path A but as a standalone short paper. Cites Simpson et al. 2026 throughout.

Pros: doesn't disturb the original; faster to land independently; can target a workshop or short-paper venue.

Cons: two papers to read; less unified narrative; risk of being seen as a redundant follow-on.

### Path C — Supplementary online material to v3.7

Add LegalBench results to the paper's repository as a supplementary appendix without re-submitting the main text. Cite from §6.9 ("Pre-Registered Replication") footnote.

Pros: no submission overhead.

Cons: less visible; doesn't strengthen the main paper's claims.

**Recommendation: Path A**, conditional on Phases 1–4 landing. The v3.7 paper's claim is *"LLMs fail on nested exception chains; deterministic execution is the safer architecture"*. LegalBench is the natural external test of that claim because it's a public peer-reviewed benchmark with the same shape of task. Adding it as Section 6.10 strengthens the paper's external validity without changing its central thesis.

## Cost summary

| Phase | Token spend | Time | Strengthens |
| --- | ---: | ---: | --- |
| 1. Statistical hardening | $0 | 1 day | All claims (CIs + significance) |
| 2. Retro held-out for curated | <$1 | 1 day | Hearsay, PJ, jcrew claims |
| 3. Random-sample replication (4 more tasks) | $5–10 | 2 days | Random-sample claim (n=2 → n=6) |
| 4. Cross-extractor experiment | $3 | 1 day | Disentangles structural vs model |
| 5. Cuad-family extension (optional, deferred) | $15–20 | 3 days | Proper N (only if Phases 1–4 don't suffice) |
| **6. Paper integration** | $0 | 2–3 days | All of the above into v3.8 § 6.10 |

**Total to "defensible at top-tier venue" (Phases 1–4 + 6): ~$8–14, ~7–8 days.**

Phase 5 only if a hostile reviewer specifically pushes back on N; can defer.

## Order of operations

The dependency chain is:

```
Phase 1 (stats)  ─┐
                  ├─→ Phase 6 (paper integration)
Phase 2 (retro)  ─┤
                  │
Phase 3 (more)   ─┤
                  │
Phase 4 (cross)  ─┘
```

Phases 1, 2, 3, 4 are independent of each other and can be parallelised. Phase 6 depends on 1–4 being available (otherwise the paper sections will be incomplete).

Quickest path: do Phase 1 + Phase 2 immediately (zero token spend, ~2 days), commit, then evaluate whether Phase 3 + 4 are needed before paper integration. If the retroactive held-out numbers (Phase 2) hold up, the curated-task claims survive review even without Phase 3 expansion.

## Stop conditions

We stop hardening and integrate to the paper when:

- Phase 1 statistical tests show p < 0.05 on the engine-vs-best-LLM comparison on at least 3 individual tasks **and** combined p < 0.01 across the random-sample tasks.

- Phase 2 retro-held-out doesn't materially erode the curated-task claims (we expect a ~1–2pt drop; if it's >5pt that's a different story).

- Phase 4 cross-extractor shows the engine win persists when opus is the extractor (not just sonnet).

If those conditions are met after Phases 1+2+4, we can integrate to v3.8 § 6.10 without Phase 3/5.

## Out of scope of this plan

- Adversarial evaluation against red-teamed contract clauses
- Multi-language testing (the source-prose hygiene is English-legal only)
- Cost-of-deployment analysis beyond what's already in the paper §6.6
- LegalBench tasks that fundamentally don't fit (multi-label, generative). Phase 5 explicitly skips these.
