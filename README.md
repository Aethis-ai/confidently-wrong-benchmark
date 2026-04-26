# Confidently Wrong: Exception Chain Collapse in Frontier LLM Rule Evaluation

Frontier LLMs collapse on nested conditional rules of the form "A is required UNLESS B applies, UNLESS C overrides B" — the pattern that dominates real-world regulatory and insurance logic. *And* the specific empirical surface of the failure is unstable: between March and April 2026 several v3.7 paper cells closed silently under the same model alias, with no version bump. For a regulated workflow that depends on benchmark-time accuracy claims, this is the central problem: the ground shifts under the production system without notice.

This repository contains the benchmark dataset, the v3.8 adversarial extension, the LegalBench external-validation harness, full per-call replication artefacts, and the accompanying paper.

## Headline Results (v3.8, April 2026)

All numbers from the paper ([Simpson, Kozak, Doake, v3.8, 2026](paper/Simpson_Exception_Chain_Collapse_2026.md)). Three independent evidence sources.

### 1. v3.8 Adversarial Construction-CAR Extension (paper §6.4.1)

20 newly-authored adversarial scenarios stratified across five complexity dimensions (independent-prose-then-engine methodology). The 11 GPT-5.4-failed scenarios from v3.7 have closed under model drift; these 20 are the v3.8 demonstration that the failure pattern remains observable on the same domain at deeper composition.

| Configuration | Accuracy on N=20 | Notes |
|---|:--:|---|
| **Aethis Engine** | **20/20 (100%)** | deterministic by construction |
| GPT-5.4 (`reasoning_effort=low`) | 20/20 (100%) | 16–126 reasoning tokens per scenario |
| Claude Sonnet 4.6 | 19/20 (95%) | fails E4 (DE3/LEG3 carveback gap) |
| GPT-5.4 (default) | 19/20 (95%) | fails E4; **0 reasoning tokens on every scenario** |
| **Claude Opus 4.7** (current Anthropic strongest) | **18/20 (90%)** | fails B3 (£499 M boundary) + E4 |

Three of four frontier-LLM configurations fail on the same scenario (the DE3/LEG3 carveback gap) across both Anthropic and OpenAI. Reproducible from `tools/replication_run.py` against `dataset/construction-all-risks/scenarios_v3_8_adversarial.yaml`.

### 2. v3.7 controlled-benchmark replication (paper §6.3 / §6.4)

The v3.7 paper documented LLM failures in March 2026 across 225 scenarios in four domains. A v3.8 reproducibility pass found that several specific cells have closed:

| Cell | March 2026 (v3.7) | April 2026 (v3.8 replication) |
|---|---|---|
| GPT-5.4 on construction-CAR | 56/58 (96.6%) | **74/74 (100%)** |
| Opus 4.6 on spacecraft | 61/68 (89.7%) | **67/68 (98.5%)** |
| Sonnet 4.6 on spacecraft | 62/68 (91.2%) | 60/68 (88.2%) |
| GPT-4.1-mini on construction | 46/58 (79.3%) | 65/74 (87.8%) |
| GPT-5.3 (production-tier ref) | 7/11 on n=11 | **model alias deprecated by OpenAI** |

The Aethis Engine remains 100% on every cell, in both March and April, by construction. Same bundle, same answer, regardless of upstream model behaviour. **The fact that the v3.7 cells moved silently is itself the central evidence** — a regulated system cannot rely on benchmark-time accuracy claims that can be invalidated by an opaque model update.

Full replication artefacts: `legalbench/docs/replication/A*.json`, `legalbench/docs/replication/REPORT.md`.

### 3. External validation on LegalBench (paper §6.10)

On 9 peer-reviewed LegalBench tasks (949 held-out cases authored by Stanford researchers, not by Aethis), the Eligibility Module is significantly more accurate than each of three frontier LLMs by exact combined paired-binomial McNemar's test: *p* < 0.001 vs Claude Sonnet 4.6, *p* = 0.003 vs Claude Opus 4.7, *p* < 0.001 vs GPT-5.4. The structural advantage is largest on multi-prong rule-application tasks (Δ up to +41 pp) and persists at a smaller but cross-task-significant margin on randomly-sampled tasks chosen without fit inspection (seeds 42 + 43; seed 44 pre-registered at tag [`pre-v3.8-legalbench-preregistration`](https://github.com/Aethis-ai/confidently-wrong-benchmark/releases/tag/pre-v3.8-legalbench-preregistration)).

See [`legalbench/`](legalbench/) for the full harness, all per-task results, the statistical pipeline, and the v3.8 reproducibility / adversarial-extension artefacts.

## Key Findings (v3.8)

1. **The structural advantage of deterministic execution holds across model drift.** Even when specific v3.7 frontier-LLM failure cells close under model updates, the engine remains 100%. The §6.4.1 adversarial extension and §6.10 LegalBench results both demonstrate that current frontier models still fail; the engine still wins. The architectural argument is independent of any specific empirical snapshot.

2. **GPT-5.4 default reasoning is essentially "no reasoning".** On the 20 v3.8 adversarial scenarios, GPT-5.4 at default reasoning effort uses 0 reasoning tokens per call — the API short-circuits to a 4–6 token answer. Switching to `reasoning_effort=low` invokes the reasoning channel (16–126 tokens per scenario) and catches the carveback-gap edge case that default misses. The v3.7 paper claim that "default reasoning is better than low" was withdrawn in v3.8 after instrumented replication produced the opposite.

3. **The DE3/LEG3 carveback gap is a structural failure mode across both major model families.** Three of four frontier-LLM configurations (GPT-5.4 default, Opus 4.7, Sonnet 4.6) return the wrong verdict on the explicit carveback-gap scenario (where `is_access_damage=true` and `consequence_of_failure=false` causes the carveback group to fail before enhanced-cover logic is reached). Pattern is consistent with compositional-evaluation limits of transformer-based LLMs documented in §3.3 (Dziri et al., Valmeekam et al.).

4. **External validation on LegalBench replicates the structural-advantage finding cross-model-family, with statistical significance.** §6.10 combined McNemar's *p* < 0.001 against Sonnet 4.6 and GPT-5.4; *p* = 0.003 against Opus 4.7. Reproducible from `legalbench/tools/significance.py`.

5. **The shifting-ground problem is the central practical implication.** Frontier-LLM accuracy on a fixed benchmark is a function of the model snapshot, the harness configuration, and the prompt format — at least one of which can shift without notice. For regulated workflows, this is structurally incompatible with verification pipelines required by frameworks like the EU AI Act. Deterministic execution avoids this class of risk by construction.

## Dataset

225 hand-authored scenarios across four paper-scope domains, released as a public benchmark:

| Domain | Scenarios | Fields | Exception Depth | Source |
|--------|:---------:|:------:|:---------------:|--------|
| Life in the UK | 56 | 4 | 1 | Real (BNA 1981) |
| English Language | 43 | 12 | 2 | Real (Form AN) |
| Spacecraft Crew Certification | 68 | 11 | 3 | Synthetic |
| Construction All Risks | 58 | 14 | 5 | Synthetic (DE3/DE5) |

The construction dataset directory contains 74 scenarios on disk; the paper's Table 8a reports on the original 58-scenario suite, and the remaining 16 are included for the pre-registered replication programme described in Section 6.9 of the paper.

Additionally, the repo contains a **Benefits Entitlement** domain (30 scenarios) that is **out of scope for the paper** — included for future work per the paper's "Note on repository scope". It is not referenced in any accuracy table in this README.

See [`dataset/README.md`](dataset/README.md) for the full dataset card.

## Quick Start

```bash
# Clone
git clone https://github.com/Aethis-ai/confidently-wrong-benchmark.git
cd confidently-wrong-benchmark/benchmarks

# Engine accuracy tests (no API key needed)
uv run run_engine_tests.py ../dataset/spacecraft-crew-certification/
uv run run_engine_tests.py ../dataset/construction-all-risks/

# LLM comparison (requires OPENAI_API_KEY and/or ANTHROPIC_API_KEY)
uv run run_llm_comparison.py ../dataset/spacecraft-crew-certification/
uv run run_llm_comparison.py ../dataset/construction-all-risks/ --runs 3 --models gpt-5.4 claude-sonnet-4-6
```

## Repository Structure

```
dataset/                         # Benchmark scenarios (YAML)
  english-language/              # 43 scenarios, depth 2 (paper scope)
  life-in-the-uk/                # 56 scenarios, depth 1 (paper scope)
  spacecraft-crew-certification/ # 68 scenarios, depth 3 (paper scope)
  construction-all-risks/        # 58 paper scenarios + 16 replication extras
  benefits-entitlement/          # 30 scenarios — out of scope for paper
benchmarks/                      # Reproduction scripts (225-scenario harness)
results/                         # Raw results and analysis
paper/                           # Paper source (markdown + rendered PDF)
legalbench/                      # External validation on LegalBench (§6.10, v3.8)
                                 #   9 tasks, 949 held-out cases, combined
                                 #   paired-binomial p<0.001 vs Sonnet/GPT-5.4,
                                 #   p=0.003 vs Opus 4.7. See legalbench/README.md.
```

## Paper

**Confidently Wrong: Exception Chain Collapse in Frontier LLM Rule Evaluation**
Paul Simpson, John Kozak, Lisa Doake. April 2026 (v3.8).

- Source: [`paper/Simpson_Exception_Chain_Collapse_2026.md`](paper/Simpson_Exception_Chain_Collapse_2026.md)
- PDF: [`paper/Simpson_Exception_Chain_Collapse_2026.pdf`](paper/Simpson_Exception_Chain_Collapse_2026.pdf)
- arXiv: [TBD — added on submission]
- LegalBench external-validation harness (§6.10): [`legalbench/`](legalbench/)

## Citation

```bibtex
@article{simpson2026confidently,
  title={Confidently Wrong: Exception Chain Collapse in Frontier LLM Rule Evaluation},
  author={Simpson, Paul and Kozak, John and Doake, Lisa},
  journal={arXiv preprint arXiv:TBD},
  year={2026}
}
```

## License

- **Code** (benchmarks/, scripts): MIT License
- **Dataset and paper** (dataset/, paper/): [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/)
