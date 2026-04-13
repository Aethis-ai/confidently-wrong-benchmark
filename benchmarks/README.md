# Benchmark Scripts

Scripts to reproduce the results from the paper.

## Two evaluation paths

**Paper benchmark (full scenarios).** The results in the paper are produced by compiling gold-standard rule fixtures locally using the Aethis eligibility engine. The fixture-based benchmark is not included in this public repo because it requires the engine's compilation pipeline. The scenarios and source legislation are published in `dataset/` as the research artifact.

**Public API spot-check.** The scripts below call the Aethis public API (`api.aethis.ai`) to verify scenarios against deployed rule bundles. The public API bundles are LLM-authored (not the hand-coded gold-standard fixtures), so results may differ on edge cases.

## Engine accuracy tests (public API)

Tests against deployed bundles on the public API. No API key needed.

```bash
# Single domain
uv run run_engine_tests.py ../dataset/spacecraft-crew-certification/

# All domains
uv run run_engine_tests.py ../dataset/ --all

# With options
uv run run_engine_tests.py ../dataset/construction-all-risks/ --concurrency 5 --sequential --no-cache
```

Options:
- `--concurrency N` / `-c N` — max concurrent API requests (default: 5)
- `--sequential` — run tests one at a time instead of in parallel
- `--no-cache` — bypass server caches to measure uncached performance
- `--all` — run all domain directories found under the given path
- `--quiet` / `-q` — minimal output (pass/fail only)

## LLM comparison

Compares frontier LLM answers against the deterministic engine on the same test cases. Requires `OPENAI_API_KEY` and/or `ANTHROPIC_API_KEY`.

```bash
# Single run, default models
uv run run_llm_comparison.py ../dataset/construction-all-risks/

# Consistency check (3 runs per test)
uv run run_llm_comparison.py ../dataset/construction-all-risks/ --runs 3

# Specific models
uv run run_llm_comparison.py ../dataset/construction-all-risks/ --models gpt-5.4 claude-sonnet-4-6

# Ordering sensitivity (randomise field order per run)
uv run run_llm_comparison.py ../dataset/construction-all-risks/ --runs 3 --shuffle
```

Options:
- `--models MODEL [MODEL ...]` — models to test (default: gpt-5.4, gpt-5.4-mini, claude-opus-4-6, claude-sonnet-4-6)
- `--runs N` — runs per test per model (default: 1, try 3 for consistency)
- `--concurrency N` / `-c N` — max concurrent LLM requests per model (default: 10)
- `--sequential` — run tests one at a time
- `--shuffle` — randomise field order in prompts per run (tests ordering sensitivity)

## Requirements

```bash
pip install -r requirements.txt
```

Or use uv (recommended — dependencies are declared inline via PEP 723):

```bash
uv run run_engine_tests.py ../dataset/spacecraft-crew-certification/
```
