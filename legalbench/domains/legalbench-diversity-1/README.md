# LegalBench `diversity_*` — Aethis engine results

## Result

**Aethis engine: 1,800 / 1,800 (100%)** across all six LegalBench
`diversity_*` sub-tasks (300 test cases each).

| Sub-task | Shape | Cases | Engine |
| --- | --- | ---: | ---: |
| `diversity_1` | 1P × 1D × 1 claim | 300 | **300/300 (100.0%)** |
| `diversity_2` | 1P × 2D × 1 claim each | 300 | **300/300 (100.0%)** |
| `diversity_3` | 1P × 1D × 2 claims (aggregated) | 300 | **300/300 (100.0%)** |
| `diversity_4` | 2P × 1D × 1 claim | 300 | **300/300 (100.0%)** |
| `diversity_5` | 2P × 1D × 2 claims (aggregated) | 300 | **300/300 (100.0%)** |
| `diversity_6` | 2P × 2D × 2 claims per defendant | 300 | **300/300 (100.0%)** |

Published frontier-LLM baselines on LegalBench `diversity_*` sit in the
high-80s to mid-90s, with GPT-4 reported at ~95% on the easiest split
and lower on the multi-party / multi-claim variants.

## LLM-only head-to-head (partial)

A clean head-to-head against `claude-sonnet-4-6` only exists for
`diversity_1` so far — both engine and sonnet score 300/300 (tie at
100%) on the easiest variant, which doesn't separate them. For
`diversity_2`…`_5` our LLM-baseline harness ran into a prompt-format
issue (sonnet hedges with chain-of-thought instead of leading with
Yes/No, which gets truncated at the 16-token cap), so those numbers
are unreliable until the harness is rewritten with few-shot prompts.
See [`docs/headtohead.md`](../../docs/headtohead.md). The diversity
rule is too simple for symbolic execution to give a meaningful edge
over a strong LLM, so we don't expect a clean re-run to change the
top-line conclusion much.

## Source provenance — important

Each `sources/rule.md` is the **verbatim canonical Task description**
from the upstream LegalBench task README, fetched from
`HazyResearch/legalbench/tasks/diversity_<n>/README.md`, license
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (Source author:
Neel Guha). No paraphrase, no editorial choice. This is the same rule
prose that frontier-LLM baselines are evaluated against, so the engine
result is comparable.

**v1 was invalidated.** The first round of bundles (April 2026, bundle
IDs `legalbench_diversity_jurisdiction:20260425-03b7c5fc` etc.) were
authored from a paraphrased `rule.md` that contained `## Inputs`,
`## Output`, and `## Edge cases` sections — pre-specifying the field
schema, outcome enum, and threshold-flip cases. Those bundles still
scored 100% but the experiment didn't measure honest rule extraction.
v2 bundles (`legalbench_diversity_<n>_v2:20260425-...`) are authored
from the canonical source. The 100% score holds — the diversity rule
is genuinely simple enough that the DSL generator finds the right
encoding from the canonical prose alone.

## How it works

Each split has its own CLI-canonical project under
`domains/legalbench-diversity-{1..6}/`:

```
aethis.yaml            # CLI project config
.aethis/state.json     # bundle_id + project_id (CLI-managed)
sources/rule.md        # verbatim LegalBench Task description
guidance/hints.yaml    # CLI-canonical (empty)
tests/scenarios.yaml   # 8 statute-derived test cases per split
run.py                 # benchmark runner: regex extract → /decide → score
results/full_v2.json   # output of the full 300-case run
```

Authoring used `aethis_create_bundle` → `aethis_generate_and_test` →
`aethis_publish` via the MCP server. Each bundle passed all 8
statute-derived tests on the first generation iteration. Bundle IDs are
recorded in each project's `.aethis/state.json` (current and previous
contaminated for audit).

The benchmark runner does not call any LLM. The narratives are
deterministically templated, so a small per-shape regex extracts
plaintiff/defendant states and claim amounts from the text and posts
them straight to `/api/v1/public/decide`. Token cost across all six
splits and 1,800 cases: **$0** for extraction. Authoring spend was a
single `aethis_generate_and_test` per bundle (~6 × ~$0.05 ≈ $0.30 for
v1 + the same for v2).

## Reproducing

```bash
# From repo root, with local aethis-core running on :8080:
for n in 1 2 3 4 5 6; do
  uv run domains/legalbench-diversity-$n/run.py \
    --limit 300 \
    --output domains/legalbench-diversity-$n/results/full_v2.json
done
```

## v2 bundle IDs

| Sub-task | Bundle ID (v2 — canonical) |
| --- | --- |
| `diversity_1` | `legalbench_diversity_1_v2:20260425-f3d5cd59` |
| `diversity_2` | `legalbench_diversity_2_v2:20260425-f2e82362` |
| `diversity_3` | `legalbench_diversity_3_v2:20260425-35d86578` |
| `diversity_4` | `legalbench_diversity_4_v2:20260425-ad737155` |
| `diversity_5` | `legalbench_diversity_5_v2:20260425-e4357c72` |
| `diversity_6` | `legalbench_diversity_6_v2:20260425-36b6dabe` |
