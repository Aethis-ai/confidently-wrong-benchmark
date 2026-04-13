# Confidently Wrong: Exception Chain Collapse in Frontier LLM Rule Evaluation

Frontier LLMs achieve near-perfect accuracy on flat eligibility checks but collapse on nested exception chains -- the pattern that dominates real-world regulatory and insurance logic. This repository contains the benchmark dataset, reproduction scripts, and results from the accompanying paper.

When rules contain exceptions-to-exceptions (depth >= 3), every tested model exhibits *exception chain collapse*: confidently returning incorrect verdicts rather than signalling uncertainty.

## Headline Results

Combined results across spacecraft (68 scenarios, depth 3) and construction (74 scenarios, depth 5):

| System | Spacecraft | Construction | Latency | Deterministic | Temporally Stable |
|--------|:----------:|:------------:|:-------:|:-------------:|:-----------------:|
| Aethis Engine | 100% | 100% | <5 ms | Yes | Yes |
| GPT-5.4 | 100% | 100% | 2--5 s | No | No |
| Claude Opus 4.6 | 99% | 99% | 2--5 s | No | No |
| Claude Sonnet 4.6 | 87% | 97% | 1--3 s | No | No |
| GPT-5.4-mini | 99% | 85% | 1--2 s | No | No |

*Evaluated 2026-04-12. LLM accuracy shifts between evaluations without user action -- see [results](results/llm-vs-engine.md) for temporal stability analysis.*

## Dataset

241 hand-authored scenarios across 4 domains with increasing exception chain depth:

| Domain | Scenarios | Fields | Exception Depth | Source |
|--------|:---------:|:------:|:---------------:|--------|
| Life in the UK | 56 | 4 | 1 | Real (BNA 1981) |
| English Language | 43 | 12 | 2 | Real (Form AN) |
| Spacecraft Crew Certification | 68 | 11 | 3 | Synthetic |
| Construction All Risks | 74 | 14 | 5 | Synthetic (DE3/DE5) |

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
uv run run_llm_comparison.py ../dataset/construction-all-risks/
uv run run_llm_comparison.py ../dataset/construction-all-risks/ --runs 3 --models gpt-5.4 claude-sonnet-4-6
```

## Repository Structure

```
dataset/                         # Benchmark scenarios (YAML)
  construction-all-risks/        # 74 scenarios, depth 5
  english-language/              # 43 scenarios, depth 2
  life-in-the-uk/                # 56 scenarios, depth 1
  spacecraft-crew-certification/ # 68 scenarios, depth 3
benchmarks/                      # Reproduction scripts
results/                         # Raw results and analysis
paper/                           # Paper source and PDF
```

## Paper

**Confidently Wrong: Exception Chain Collapse in Frontier LLM Rule Evaluation**
Paul Simpson. 2026.

- arXiv: [TBD]
- PDF: [`paper/confidently-wrong-v3.6.pdf`](paper/confidently-wrong-v3.6.pdf)

## Citation

```bibtex
@article{simpson2026confidently,
  title={Confidently Wrong: Exception Chain Collapse in Frontier LLM Rule Evaluation},
  author={Simpson, Paul},
  journal={arXiv preprint arXiv:TBD},
  year={2026}
}
```

## License

- **Code** (benchmarks/, scripts): MIT License
- **Dataset and paper** (dataset/, paper/): [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/)
