# Confidently Wrong: Exception Chain Collapse in Frontier LLM Rule Evaluation

Frontier LLMs achieve near-perfect accuracy on flat eligibility checks but degrade sharply on nested exception chains — the pattern that dominates real-world regulatory and insurance logic. This repository contains the benchmark dataset, reproduction scripts, and the accompanying paper.

When rules contain exceptions-to-exceptions with depth ≥ 3, and when reasoning compute is constrained, every tested model exhibits *exception chain collapse*: confidently returning incorrect verdicts rather than signalling uncertainty.

## Headline Results

All numbers below are from the paper ([Simpson, Kozak, Doake, 2026](paper/Simpson_Exception_Chain_Collapse_2026.md)). Wilson 95% confidence intervals where shown.

| Model | english_language (n=43) | spacecraft (n=68) | construction (n=58) | construction exception chain @ low reasoning (n=11) |
|-------|:-----------------------:|:-----------------:|:-------------------:|:---------------------------------------------------:|
| **Aethis Engine** | **100%** | **100%** | **100%** | **100%** |
| GPT-5.4 | 100% | 100% | **96.6%** | **63.6%** |
| Claude Opus 4.6 | 100% | 89.7% | — | — |
| Claude Sonnet 4.6 | 100% | 91.2% | — | — |
| GPT-5-mini | 97.7% | 75.0% | — | — |
| GPT-4.1-mini | — | — | 79.3% | 45.5% |

**No frontier model achieves 100% across all four domains.** GPT-5.4 is the strongest frontier model tested; it drops to 96.6% on the construction insurance benchmark and to 63.6% on the same domain when reasoning compute is reduced to `reasoning_effort=low`. On the spacecraft benchmark Claude Opus 4.6 returns the wrong answer on 7/68 scenarios, and under 70 independent trials on those 7 failing scenarios produces **zero** correct answers (Clopper–Pearson 95% upper bound on per-trial success: 4.19%).

The Aethis Engine achieves 100% across every section by construction: rules are compiled ahead of time and evaluated deterministically. Same bundle, same result, any date, any compute budget.

## Key Findings

1. **Failures are systematic, not stochastic.** Under 10 independent runs on 7 failing spacecraft scenarios (70 trials total), Claude Opus 4.6 produces zero correct answers. The failures are not noise that can be averaged away.

2. **Prompt repair trades false negatives for false positives.** An enhanced prompt targeting the failure pattern fixes 5 of 7 false negatives on spacecraft but introduces 20 new false positives, dropping net accuracy from 89.7% to 64.7% (disjoint Wilson 95% CIs). The trade-off is structural, not fixable through better wording.

3. **Reasoning-effort dependence (tentative, N=11, pre-registered for replication at N=66).** GPT-5.4 at `reasoning_effort=low` scores 63.6% on the construction exception-chain subset — matching GPT-5.3 at default reasoning effort exactly. The paper treats this as hypothesis-generating, not confirmatory, and pre-registers a higher-power replication.

4. **The failure pattern is exception-chain specific, not general to legal reasoning.** All frontier models achieve 100% on the depth-2 English Language section (43 scenarios). Failures emerge at depth 3 (spacecraft) and deepen at depth 5 (construction).

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
Paul Simpson, John Kozak, Lisa Doake. April 2026.

- Source: [`paper/Simpson_Exception_Chain_Collapse_2026.md`](paper/Simpson_Exception_Chain_Collapse_2026.md)
- PDF: [`paper/Simpson_Exception_Chain_Collapse_2026.pdf`](paper/Simpson_Exception_Chain_Collapse_2026.pdf)
- arXiv: [TBD]

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
