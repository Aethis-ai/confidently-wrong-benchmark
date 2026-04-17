# Confidently Wrong: Exception Chain Collapse in Frontier LLM Rule Evaluation

Frontier LLMs achieve near-perfect accuracy on flat eligibility checks but collapse on nested exception chains -- the pattern that dominates real-world regulatory and insurance logic. This repository contains the benchmark dataset, reproduction scripts, and results from the accompanying paper.

When rules contain exceptions-to-exceptions (depth >= 3), every tested model exhibits *exception chain collapse*: confidently returning incorrect verdicts rather than signalling uncertainty.

## Headline Results

Results from the paper's primary evaluation (2026-04-06). All accuracy figures report Wilson 95% confidence intervals.

**Spacecraft Crew Certification -- 68 scenarios, depth 3**

| Model | Accuracy | 95% Wilson CI | FN |
|-------|:--------:|:-------------:|:--:|
| **Aethis Engine** | **68/68 (100%)** | **[94.7%, 100%]** | **0** |
| GPT-5.4 | 68/68 (100%) | [94.7%, 100%] | 0 |
| Claude Sonnet 4.6 | 62/68 (91.2%) | [82.1%, 95.9%] | 6 |
| Claude Opus 4.6 | 61/68 (89.7%) | [80.2%, 94.9%] | 7 |
| GPT-5-mini | 51/68 (75.0%) | [63.6%, 83.8%] | 17 |

**Construction All Risks -- 58 scenarios, depth 5**

| Model | Accuracy | 95% Wilson CI |
|-------|:--------:|:-------------:|
| **Aethis Engine** | **58/58 (100%)** | **[93.8%, 100%]** |
| GPT-5.4 | 56/58 (96.6%) | [88.3%, 99.0%] |
| GPT-4.1-mini | 46/58 (79.3%) | [67.2%, 87.7%] |

*Updated evaluations (2026-04-12) with expanded domains are in [results/llm-vs-engine.md](results/llm-vs-engine.md), including temporal stability analysis showing accuracy shifts of up to +/-24pp between evaluation dates with no change to prompts, scenarios, or API parameters.*

## Key Findings

1. **Failures are systematic, not stochastic.** Under 10 independent runs on 7 failing spacecraft scenarios (70 trials), Claude Opus 4.6 produces zero correct answers. Clopper-Pearson 95% one-sided upper bound on per-trial success: 4.19%.

2. **Prompt repair trades false negatives for false positives.** An enhanced prompt targeting the failure pattern fixes 5 of 7 FN but introduces 20 FP, dropping net accuracy from 89.7% to 64.7% (Wilson CIs disjoint). The trade-off is structural, not fixable through better wording.

3. **Reasoning-effort dependence (tentative, N=11).** GPT-5.4 at low reasoning effort drops to 63.6% on the construction exception-chain subset -- matching GPT-5.3 exactly. Pre-registered for replication at N=66.

4. **Temporal instability.** Re-evaluating the same scenarios 6 days later: Claude Opus shifts 90% to 99%, GPT-5.4-mini shifts 75% to 99%, Claude Sonnet shifts 91% to 87%. The engine's compiled rules are immutable -- same bundle, same result, any date. See [results/llm-vs-engine.md](results/llm-vs-engine.md).

## Dataset

271 hand-authored scenarios across 5 domains with increasing exception chain depth:

| Domain | Scenarios | Fields | Exception Depth | Source | Paper |
|--------|:---------:|:------:|:---------------:|--------|:-----:|
| Life in the UK | 56 | 4 | 1 | Real (BNA 1981) | v3.7 |
| English Language | 43 | 12 | 2 | Real (Form AN) | v3.7 |
| Spacecraft Crew Certification | 68 | 11 | 3 | Synthetic | v3.7 |
| Construction All Risks | 58 | 14 | 5 | Synthetic (DE3/DE5) | v3.7 |
| Construction All Risks (expanded) | 74 | 14 | 5 | Synthetic (DE3/DE5) | repo only |
| Benefits Entitlement | 30 | 8 | 3 | Synthetic (UC Regulations 2013) | repo only |

The paper (v3.7) analyses 225 scenarios across the first four domains. The expanded construction suite (74 scenarios) and benefits entitlement domain (30 scenarios) are included in the repository for reproducibility and future work.

See [`dataset/README.md`](dataset/README.md) for the full dataset card.

## Quick Start

```bash
# Clone
git clone https://github.com/Aethis-ai/confidently-wrong-benchmark.git
cd confidently-wrong-benchmark/benchmarks

# Engine accuracy tests (no API key needed)
uv run run_engine_tests.py ../dataset/spacecraft-crew-certification/
uv run run_engine_tests.py ../dataset/construction-all-risks/
uv run run_engine_tests.py ../dataset/benefits-entitlement/

# LLM comparison (requires OPENAI_API_KEY and/or ANTHROPIC_API_KEY)
uv run run_llm_comparison.py ../dataset/construction-all-risks/
uv run run_llm_comparison.py ../dataset/construction-all-risks/ --runs 3 --models gpt-5.4 claude-sonnet-4-6
```

## Repository Structure

```
dataset/                         # Benchmark scenarios (YAML)
  benefits-entitlement/          # 30 scenarios, depth 3
  construction-all-risks/        # 74 scenarios, depth 5
  english-language/              # 43 scenarios, depth 2
  life-in-the-uk/                # 56 scenarios, depth 1
  spacecraft-crew-certification/ # 68 scenarios, depth 3
benchmarks/                      # Reproduction scripts
results/                         # Raw results and analysis
paper/                           # Paper source
```

## Paper

**Confidently Wrong: Exception Chain Collapse in Frontier LLM Rule Evaluation**
Paul Simpson, John Kozak, Lisa Doake. 2026.

- arXiv: [TBD]
- Source: [`paper/confidently-wrong-v3.7.md`](paper/confidently-wrong-v3.7.md)

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
