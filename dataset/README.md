# Dataset Card: Confidently Wrong Benchmark

## Overview

| | |
|---|---|
| **Name** | Confidently Wrong Benchmark |
| **Paper version** | v3.8 (April 2026) |
| **Dataset version** | 1.0 |
| **License** | CC-BY-4.0 |
| **Size** | 225 scenarios across 4 paper-scope domains (plus 30 out-of-scope supplementary) |
| **Task** | Binary eligibility classification under nested exception chains |
| **Format** | YAML |
| **External validation** | v3.8 §6.10 — 9 LegalBench tasks, 949 held-out cases. See [`../legalbench/`](../legalbench/). |

## Domains

| Domain | Scenarios | Fields | Exception Depth | Source | Difficulty |
|--------|:---------:|:------:|:---------------:|--------|:----------:|
| Life in the UK | 56 | 4 | 1 | Real (BNA 1981) | Low |
| English Language | 43 | 12 | 2 | Real (Form AN) | Medium |
| Spacecraft Crew Certification | 68 | 11 | 3 | Synthetic | High |
| Construction All Risks | 58 | 14 | 5 | Synthetic (DE3/DE5) | High |

**Out-of-scope supplementary (not analysed in the paper):**

| Domain | Scenarios | Fields | Exception Depth | Source | Status |
|--------|:---------:|:------:|:---------------:|--------|--------|
| Benefits Entitlement | 30 | 8 | 2 | Synthetic (UC Regs 2013) | Included for future work (paper §"Note on repository scope") |

The construction directory contains 74 scenarios on disk; Table 8a of the paper reports on the 58-scenario suite, and the remaining 16 are for the pre-registered replication programme (paper §6.9). The `paper_suite_size` field in `construction-all-risks/metadata.yaml` records this split.

Each domain directory contains:

- `metadata.yaml` -- domain description, field definitions, exception chain patterns
- `scenarios.yaml` -- test scenarios with inputs and expected outcomes
- `source.md` -- source material or synthetic rule specification

## Scenario Format

Each scenario is a YAML object with the following fields:

```yaml
- name: outside_period_rejected
  inputs:
    car.policy.period_valid: false
    car.property.category: permanent_works
    car.loss.is_physical: true
    car.component.is_defective: true
    car.defect.origin: workmanship
    car.claim.is_rectification: false
    car.claim.is_access_damage: false
    car.damage.consequence_of_failure: true
    car.project.value_millions_gbp: 200
    car.notification.within_period: true
    car.contract.jct_compliant: true
  expect:
    outcome: not_eligible
  tags:
    - policy_period
```

- **name**: unique identifier within the domain
- **inputs**: dictionary of field values representing a single case
- **expect.outcome**: `eligible` or `not_eligible`
- **tags**: classification labels for analysis (e.g., which rule path the scenario targets)

## Field Types

All input fields use one of three types:

| Type | Examples |
|------|---------|
| `bool` | `true`, `false` |
| `int` | `35`, `200` |
| `enum` | `"permanent_works"`, `"workmanship"`, `"Vogon"` |

There are no free-text fields. Every scenario is fully determined by its inputs -- there is exactly one correct answer for each.

## Methodology

The benchmark is designed to isolate a specific failure mode: **exception chain collapse** in LLM rule evaluation.

**Design principles:**

1. **Adversarial toward LLM reasoning.** Scenarios are constructed to trigger confident incorrect answers, not to be representative of typical case distributions. Edge cases, boundary conditions, and exception-to-exception paths are overrepresented.

2. **Controlled exception depth.** Domains span exception chain depths from 1 through 5 to measure how accuracy degrades as nesting increases.

3. **Deterministic ground truth.** Every scenario has exactly one correct answer derivable from the rule specification. There are no ambiguous cases.

4. **Mixed provenance.** Two paper-scope domains (Life in the UK, English Language) use real UK immigration law. Two paper-scope domains (Spacecraft Crew Certification, Construction All Risks) use synthetic rules designed to stress-test exception chains without domain familiarity bias. The out-of-scope Benefits Entitlement domain uses synthetic rules modelled on UC Regulations 2013.

**Scenario construction process:**

- For each domain, the complete exception chain structure was mapped
- Scenarios were authored to cover: baseline paths, each exception level in isolation, combinations of exceptions, boundary values, adversarial pairings (minimal input changes that flip the outcome), negation stacking (double/triple negation reasoning), multi-failure stacking (multiple simultaneous disqualifiers), contradictory surface cues (appearance vs reality), and cross-clause interaction (parallel constraint threads)
- All scenarios were validated against a formal rule engine to confirm ground truth

## Limitations

- **Narrow task scope.** This benchmark tests one specific class of reasoning: evaluating nested exception chains in structured rule sets. It does not measure general legal reasoning, document comprehension, or open-ended analysis.
- **Synthetic domains.** The Spacecraft and Construction domains use synthetic rule specifications. Performance on these may not generalise to real regulations of equivalent complexity.
- **Binary outcomes only.** All scenarios produce `eligible` or `not_eligible`. The benchmark does not test partial satisfaction, pending states, or multi-outcome rules.
- **No free-text inputs.** All fields are typed (bool/int/enum). The benchmark does not test information extraction from natural language documents.
- **English only.** All rule specifications and scenarios are in English.

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

This dataset is released under [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/).
