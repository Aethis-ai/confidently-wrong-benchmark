# SME guidance channels — what lives where

Two distinct channels of subject-matter-expert guidance can be applied
to a benchmark integration. They affect different stages of the
pipeline and are stored in different places. Conflating them caused a
bookkeeping inconsistency in the early commits which is documented and
fixed here.

## Channel 1 — Rule-authoring hints (canonical)

**Where**: `domains/<task>/guidance/hints.yaml`
**Or attached server-side via**: `mcp__aethis__aethis_add_guidance(project_id, ...)`
**Affects**: aethis-core's bundle generation step. Hints flow into the
DSL rule the engine compiles. Restructures fields, criteria, groups,
and how prongs combine (AND vs OR).
**Visible in**: `aethis_explain(bundle_id)` — the generated rule's
shape.

This is the CLI-canonical channel. `aethis-cli generate` reads
`hints.yaml` from the project directory and forwards it. When we author
via MCP we use `aethis_add_guidance` directly; the server is the source
of truth and the local file should mirror it.

**Used in this repo for**:
- `legalbench-jcrew-blocker` — 4 hints attached server-side, mirrored
  in the local `hints.yaml`. Restructured the rule from AND-of-two-prongs
  (v1) to single-prohibition (v3). Visible in the engine score: 16.7%
  → 98.1% lift.

**Not used for**:
- All `legalbench-diversity-*` (canonical sources were unambiguous)
- `legalbench-hearsay` (rule was correctly generated; remaining errors
  are extractor-level, not rule-level)
- `legalbench-personal-jurisdiction` (rule was correctly generated;
  remaining errors are extractor-level)

## Channel 2 — Runtime extractor hints (this-repo extension)

**Where**: `domains/<task>/guidance/extractor_hints.md`
**How**: loaded by the domain's `run.py` and folded into the LLM
extractor prompt at *runtime*.
**Affects**: how the LLM extractor reads case narratives → field
values. **Does NOT touch aethis-core, the bundle, or the generated
rule.** The bundle remains unchanged; only the case-understanding
step is shaped.
**Not visible in**: `aethis_explain` (it's a runner-level concept,
outside the engine).

This is a benchmark-runtime concept. In a real Aethis production
deployment the equivalent would be domain-specific prompt
configuration, terminology glossaries, or a fine-tuned extractor
model.

**Used in this repo for**:
- `legalbench-jcrew-blocker` — LSTA terminology synonyms for
  "unrestricted subsidiary". Lifted v3 (98.1%) to v4 (100%).
- `legalbench-personal-jurisdiction` — five textbook PJ-analysis
  principles (forum identification, contacts taxonomy, temporal
  scope, nexus, domicile vs. doing business). Lifted v1 (88%) to v3
  (98%).

**Not used for** (file present but empty):
- `legalbench-hearsay` — we attempted treatise-style hints; they
  regressed accuracy and were reverted (see the file's commentary).
- `legalbench-diversity-*` — narratives are templated, regex
  extraction is deterministic, no LLM extractor involved.

## The honest summary

| Bundle | Rule-authoring hints (Channel 1) | Runtime extractor hints (Channel 2) | Engine score |
| --- | :---: | :---: | ---: |
| `diversity_1`..`_6` | none | none (regex extractor) | 1800/1800 (100%) |
| `hearsay` | none | none (attempted, reverted as defensible negative result) | 85/94 (90.4%) |
| `jcrew_blocker` v3 | **4 hints** | none | 53/54 (98.1%) |
| `jcrew_blocker` v4 | **4 hints** | LSTA glossary | 54/54 (100%) |
| `personal_jurisdiction` | none | **5 textbook PJ principles** | 49/50 (98.0%) |

**Both channels are SME guidance.** Both are written in plain English.
Neither contains DSL syntax. Both reflect practitioner knowledge that
exists independently of the LegalBench dataset. They differ only in
**where** in the pipeline they apply.

To verify which is in play for any bundle:

```bash
# Channel 1 — what aethis-core has on the project:
mcp__aethis__aethis_list_guidance(project_id=...)

# Channel 1 — local file the CLI would read:
cat domains/<task>/guidance/hints.yaml

# Generated rule (proves Channel 1's effect):
mcp__aethis__aethis_explain(bundle_id=...)

# Channel 2 — runtime prompt that the runner loads:
cat domains/<task>/guidance/extractor_hints.md
# Folded into run.py's extractor prompt — see _EXTRACTOR_PROMPT in
# domains/<task>/run.py.
```

## Why this distinction matters

A sceptical reviewer asked: *"Is the engine actually doing anything
different from the LLM-only baseline, or are the SME hints just
prompt-engineering tricks?"*

The answer is **different for each task**:

- **`jcrew_blocker`**: Channel 1 hints visibly restructured the rule
  (two-group AND → one-criterion single-prong), provable by
  `aethis_explain`. The engine is doing different rule application
  from before.
- **`personal_jurisdiction`**: The rule itself is unchanged from the
  canonical source. The engine's win over Sonnet/Opus 4.7 (+6pt)
  comes from **structural decomposition of the task**: rather than
  asking the LLM to do the whole thing in one chain-of-thought, we
  ask it to extract three discrete facts (with practitioner
  guidance) and let the deterministic engine combine them. That's a
  pipeline-architecture win, not a rule-authoring win.
- **`hearsay`**: Same architecture as personal_jurisdiction. The
  engine's +12pt over Sonnet comes purely from this conjunction-step
  decomposition, with no Channel 1 or Channel 2 hints in play.
- **`diversity_*`**: Pure rule-authoring win. No hints, regex
  extraction. The bundle generated from canonical text is the entire
  story.

Different commercial pitches map to each:
- *"Aethis encodes complex eligibility rules from regulation directly"* — diversity, hearsay.
- *"Aethis incorporates practitioner SME knowledge as living, plain-English guidance"* — jcrew_blocker (Channel 1).
- *"Aethis pipelines beat end-to-end LLM reasoning on multi-prong cases by separating extraction from rule application"* — personal_jurisdiction, hearsay.
