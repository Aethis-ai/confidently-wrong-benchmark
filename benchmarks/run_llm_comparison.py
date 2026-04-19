#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6.0", "aiohttp>=3.9", "rich>=13.0", "openai>=1.0", "anthropic>=0.40"]
# ///
"""
Compare frontier LLM answers vs deterministic engine on the same test cases.

Tests multiple models across providers. Optionally runs each test multiple
times to measure consistency -- LLMs may give different answers on retry,
the engine never does.

Parallelised: scenarios run concurrently per model, models run concurrently.
Runs within a scenario stay sequential to measure consistency fairly.

The project name is inferred from the dataset directory name:
    dataset/construction-all-risks/ -> project "construction-all-risks"

Usage:
    uv run run_llm_comparison.py ../dataset/construction-all-risks/
    uv run run_llm_comparison.py ../dataset/construction-all-risks/ --runs 3
    uv run run_llm_comparison.py ../dataset/construction-all-risks/ --models gpt-5.4 claude-sonnet-4-6
    uv run run_llm_comparison.py ../dataset/construction-all-risks/ --concurrency 10
    uv run run_llm_comparison.py ../dataset/construction-all-risks/ --shuffle  # randomise field order per run
    uv run run_llm_comparison.py ../dataset/construction-all-risks/ --sequential

Requires OPENAI_API_KEY and/or ANTHROPIC_API_KEY in environment.
"""

import argparse
import asyncio
import os
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Optional

import aiohttp
import yaml
from rich.console import Console
from rich.table import Table

console = Console()
DEFAULT_API_URL = "https://api.aethis.ai"
DEFAULT_CONCURRENCY = 10

DEFAULT_MODELS = ["gpt-5.4", "gpt-5-mini", "claude-opus-4-6", "claude-sonnet-4-6"]

_ANTHROPIC_PREFIXES = ("claude-",)
_OPENAI_REASONING = ("gpt-5", "o3", "o4")


def _is_anthropic(model: str) -> bool:
    return any(model.startswith(p) for p in _ANTHROPIC_PREFIXES)


def _is_openai_reasoning(model: str) -> bool:
    return any(model.startswith(p) for p in _OPENAI_REASONING)


def infer_project_name(example_dir: Path) -> str:
    return example_dir.name


def load_tests(example_dir: Path) -> list:
    path = example_dir / "scenarios.yaml"
    if not path.exists():
        path = example_dir / "tests" / "scenarios.yaml"
    if not path.exists():
        console.print("[red]ERROR:[/red] No test file found (tried scenarios.yaml and tests/scenarios.yaml)")
        sys.exit(1)
    with open(path) as f:
        return yaml.safe_load(f).get("tests", [])


def load_source(example_dir: Path) -> str:
    path = example_dir / "source.md"
    if not path.exists():
        path = example_dir / "sources" / "source.md"
    if not path.exists():
        console.print("[red]ERROR:[/red] No source file found (tried source.md and sources/source.md)")
        sys.exit(1)
    with open(path) as f:
        return f.read()


async def discover_bundle(api_url: str, project_name: str, api_key: Optional[str] = None) -> str:
    headers: dict = {}
    if api_key:
        headers["X-API-Key"] = api_key
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{api_url}/api/v1/public/bundles",
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=15),
        ) as resp:
            resp.raise_for_status()
            bundles = await resp.json()
    normalized = project_name.replace("-", "_").lower()
    for b in bundles:
        section = b["section_id"].replace("-", "_").lower()
        if normalized in section or section in normalized:
            return b["bundle_id"]
    return ""


def _build_prompt(source_text: str, test: dict, *, shuffle: bool = False) -> str:
    """Build evaluation prompt with full source text -- no truncation."""
    items = list(test["inputs"].items())
    if shuffle:
        random.shuffle(items)

    facts = []
    for field, value in items:
        short = field.split(".")[-1].replace("_", " ")
        if isinstance(value, bool):
            facts.append(f"- {short}: {'yes' if value else 'no'}")
        else:
            facts.append(f"- {short}: {value}")
    facts_text = "\n".join(facts)

    return (
        "You are evaluating eligibility based on the following regulation.\n\n"
        f"--- REGULATION ---\n{source_text}\n--- END REGULATION ---\n\n"
        f"Given these facts:\n{facts_text}\n\n"
        "Based ONLY on the regulation above, is the applicant eligible?\n"
        "Answer with exactly one word: eligible, not_eligible, or undetermined.\n"
        "Do not explain. Just the answer."
    )


def _parse_answer(raw: str) -> str:
    raw = raw.strip().lower()
    for label in ("not_eligible", "eligible", "undetermined"):
        if label in raw:
            return label
    return f"parse_error ({raw[:20]})"


async def ask_openai(model: str, prompt: str, semaphore: asyncio.Semaphore) -> str:
    from openai import AsyncOpenAI
    async with semaphore:
        for attempt in range(5):
            try:
                client = AsyncOpenAI()
                kwargs: dict = {"model": model, "messages": [{"role": "user", "content": prompt}]}
                if _is_openai_reasoning(model):
                    kwargs["max_completion_tokens"] = 2000
                else:
                    kwargs["max_tokens"] = 50
                    kwargs["temperature"] = 0
                response = await client.chat.completions.create(**kwargs)
                return _parse_answer(response.choices[0].message.content or "")
            except Exception as e:
                if "429" in str(e) or "rate" in str(e).lower():
                    await asyncio.sleep(min(2 ** attempt, 30))
                    continue
                return f"error ({str(e)[:40]})"
        return "error (429 after retries)"


async def ask_anthropic(model: str, prompt: str, semaphore: asyncio.Semaphore) -> str:
    import anthropic
    async with semaphore:
        for attempt in range(5):
            try:
                client = anthropic.AsyncAnthropic()
                response = await client.messages.create(
                    model=model,
                    max_tokens=50,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = response.content[0].text if response.content else ""
                return _parse_answer(text)
            except Exception as e:
                if "429" in str(e) or "rate" in str(e).lower():
                    await asyncio.sleep(min(2 ** attempt, 30))
                    continue
                return f"error ({str(e)[:40]})"
        return "error (429 after retries)"


async def ask_llm(model: str, source_text: str, test: dict, semaphore: asyncio.Semaphore, *, shuffle: bool = False) -> str:
    prompt = _build_prompt(source_text, test, shuffle=shuffle)
    if _is_anthropic(model):
        return await ask_anthropic(model, prompt, semaphore)
    return await ask_openai(model, prompt, semaphore)


async def ask_engine(api_url: str, bundle_id: str, test: dict, api_key: Optional[str] = None) -> str:
    headers: dict = {}
    if api_key:
        headers["X-API-Key"] = api_key
    async with aiohttp.ClientSession() as session:
        for attempt in range(5):
            async with session.post(
                f"{api_url}/api/v1/public/decide",
                json={"bundle_id": bundle_id, "field_values": test["inputs"]},
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status == 429:
                    await asyncio.sleep(min(2 ** attempt, 30))
                    continue
                if resp.status != 200:
                    return f"error ({resp.status})"
                data = await resp.json()
                return data["decision"]
    return "error (429 after retries)"


def _check_keys(models: list[str]) -> Optional[str]:
    needs_openai = any(not _is_anthropic(m) for m in models)
    needs_anthropic = any(_is_anthropic(m) for m in models)
    missing = []
    if needs_openai and not os.environ.get("OPENAI_API_KEY"):
        missing.append("OPENAI_API_KEY")
    if needs_anthropic and not os.environ.get("ANTHROPIC_API_KEY"):
        missing.append("ANTHROPIC_API_KEY")
    if missing:
        return f"Set {' and '.join(missing)} to run this comparison."
    return None


def _style_answer(answer: str, correct: bool) -> str:
    if correct:
        return f"[green]{answer}[/green]"
    return f"[bold red]{answer}[/bold red]"


def _style_consistency(answers: list[str], expected: str) -> str:
    counts = Counter(answers)
    n = len(answers)
    correct = sum(1 for a in answers if a == expected)

    if len(counts) == 1:
        answer = answers[0]
        if answer == expected:
            return f"[green]{correct}/{n} {answer}[/green]"
        return f"[bold red]0/{n} {answer}[/bold red]"

    parts = []
    for ans, count in counts.most_common():
        style = "green" if ans == expected else "red"
        parts.append(f"[{style}]{count}x{ans}[/{style}]")
    return f"[yellow]{correct}/{n}[/yellow] {' '.join(parts)}"


async def evaluate_model_on_test(
    model: str,
    source_text: str,
    test: dict,
    n_runs: int,
    semaphore: asyncio.Semaphore,
    *,
    shuffle: bool = False,
) -> list[str]:
    """Evaluate a single model on a single test for n_runs. Runs are sequential for consistency measurement."""
    answers = []
    for _ in range(n_runs):
        answer = await ask_llm(model, source_text, test, semaphore, shuffle=shuffle)
        answers.append(answer)
    return answers


async def evaluate_model_all_tests(
    model: str,
    source_text: str,
    tests: list[dict],
    n_runs: int,
    concurrency: int,
    *,
    shuffle: bool = False,
    sequential: bool = False,
) -> list[list[str]]:
    """Evaluate a model across all tests. Returns list of answer-lists (one per test)."""
    semaphore = asyncio.Semaphore(concurrency)

    if sequential:
        results = []
        for test in tests:
            answers = await evaluate_model_on_test(model, source_text, test, n_runs, semaphore, shuffle=shuffle)
            results.append(answers)
        return results

    tasks = [
        evaluate_model_on_test(model, source_text, test, n_runs, semaphore, shuffle=shuffle)
        for test in tests
    ]
    return await asyncio.gather(*tasks)


async def async_main():
    parser = argparse.ArgumentParser(description="Compare frontier LLMs vs deterministic engine")
    parser.add_argument("example_dir", type=Path, help="Path to dataset directory (e.g. ../dataset/construction-all-risks/)")
    parser.add_argument(
        "--models", nargs="+", default=DEFAULT_MODELS,
        help=f"Models to test (default: {' '.join(DEFAULT_MODELS)})",
    )
    parser.add_argument("--runs", type=int, default=1, help="Runs per test per model (default: 1, try 3 for consistency check)")
    parser.add_argument(
        "--url",
        default=os.environ.get("AETHIS_API_URL", DEFAULT_API_URL),
        help=f"API base URL (default: $AETHIS_API_URL or {DEFAULT_API_URL})",
    )
    parser.add_argument("--project", help="Override project name (default: inferred from directory name)")
    parser.add_argument("--bundle-id", help="Skip auto-discovery")
    parser.add_argument("--api-key", default=os.environ.get("AETHIS_API_KEY"), help="API key for engine (or set AETHIS_API_KEY)")
    parser.add_argument(
        "--concurrency", "-c",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help=f"Max concurrent LLM requests per model (default: {DEFAULT_CONCURRENCY})",
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Run tests sequentially instead of in parallel",
    )
    parser.add_argument(
        "--shuffle",
        action="store_true",
        help="Randomise field order in prompts per run (tests ordering sensitivity)",
    )
    args = parser.parse_args()

    key_err = _check_keys(args.models)
    if key_err:
        console.print(f"[red]ERROR:[/red] {key_err}")
        sys.exit(1)

    example_dir = args.example_dir.resolve()
    if not example_dir.is_dir():
        console.print(f"[red]ERROR:[/red] {example_dir} is not a directory")
        sys.exit(1)

    project_name = args.project or infer_project_name(example_dir)
    tests = load_tests(example_dir)
    source_text = load_source(example_dir)
    bundle_id = args.bundle_id or await discover_bundle(args.url, project_name, args.api_key)
    n_runs = args.runs

    # Header
    console.print()
    console.print(f"  [bold]Frontier LLMs vs Aethis Engine[/bold]")
    console.print(f"  [dim]Project: {project_name}[/dim]")
    mode = "sequential" if args.sequential else f"parallel ({args.concurrency} concurrent per model)"
    console.print(f"  [dim]{len(args.models)} models | {len(tests)} tests | {n_runs} run{'s' if n_runs > 1 else ''} per test | {mode}[/dim]")
    if args.shuffle:
        console.print(f"  [dim]Field order: shuffled per run[/dim]")
    if bundle_id:
        console.print(f"  [dim]Bundle: {bundle_id}[/dim]")
    console.print()

    # Evaluate all models in parallel (each model's tests also parallelised)
    console.print(f"  [dim]Evaluating {len(args.models)} models across {len(tests)} tests...[/dim]")

    model_tasks = [
        evaluate_model_all_tests(
            model, source_text, tests, n_runs, args.concurrency,
            shuffle=args.shuffle, sequential=args.sequential,
        )
        for model in args.models
    ]
    all_model_results = await asyncio.gather(*model_tasks)
    # all_model_results[i][j] = list of answers for model i, test j

    # Engine results (parallel across tests)
    engine_results = []
    if bundle_id:
        engine_tasks = [ask_engine(args.url, bundle_id, test, args.api_key) for test in tests]
        engine_results = await asyncio.gather(*engine_tasks)
    else:
        engine_results = ["no bundle"] * len(tests)

    # Build results table
    table = Table(show_lines=True, title="Results (full source text provided to all models)")
    table.add_column("Test", style="bold", max_width=40)
    table.add_column("Expected", justify="center", width=13)
    for model in args.models:
        short = model.split("/")[-1][:15]
        table.add_column(short, justify="center", width=15)
    table.add_column("Engine", justify="center", width=13)

    # Track scores and consistency
    scores = {m: 0 for m in args.models}
    consistent = {m: 0 for m in args.models}
    engine_correct = 0

    for j, test in enumerate(tests):
        name = test["name"]
        expected = test["expect"]["outcome"]

        row = [name[:40], expected]

        for i, model in enumerate(args.models):
            answers = all_model_results[i][j]

            if n_runs == 1:
                ok = answers[0] == expected
                scores[model] += int(ok)
                consistent[model] += 1
                row.append(_style_answer(answers[0], ok))
            else:
                correct_count = sum(1 for a in answers if a == expected)
                scores[model] += int(correct_count == n_runs)
                all_same = len(set(answers)) == 1
                consistent[model] += int(all_same)
                row.append(_style_consistency(answers, expected))

        # Engine
        engine_answer = engine_results[j]
        engine_ok = engine_answer == expected
        engine_correct += int(engine_ok)
        row.append(_style_answer(engine_answer, engine_ok))

        table.add_row(*row)

    console.print(table)
    console.print()

    # Summary table
    total = len(tests)
    summary = Table(title="Summary", show_lines=True)
    summary.add_column("Model", style="bold")
    summary.add_column("Correct", justify="center")
    summary.add_column("Accuracy", justify="center")
    if n_runs > 1:
        summary.add_column("Consistent", justify="center", width=12)

    for model in args.models:
        pct = 100 * scores[model] / total
        style = "green" if pct == 100 else "yellow" if pct >= 80 else "red"
        row = [model, f"{scores[model]}/{total}", f"[{style}]{pct:.0f}%[/{style}]"]
        if n_runs > 1:
            cons_pct = 100 * consistent[model] / total
            cons_style = "green" if cons_pct == 100 else "yellow" if cons_pct >= 80 else "red"
            row.append(f"[{cons_style}]{cons_pct:.0f}%[/{cons_style}]")
        summary.add_row(*row)

    engine_row = [
        "[bold]Aethis Engine[/bold]",
        f"[bold]{engine_correct}/{total}[/bold]",
        f"[bold green]{100 * engine_correct / total:.0f}%[/bold green]",
    ]
    if n_runs > 1:
        engine_row.append("[bold green]100%[/bold green]")
    summary.add_row(*engine_row)

    console.print(summary)
    console.print()

    if n_runs > 1:
        inconsistent_models = [m for m in args.models if consistent[m] < total]
        if inconsistent_models:
            console.print(f"  [yellow]Inconsistent models (gave different answers on retry):[/yellow]")
            for m in inconsistent_models:
                console.print(f"    {m}: consistent on {consistent[m]}/{total} tests")
            console.print()
            console.print(f"  [dim]The engine gives the same answer every time -- deterministic by design.[/dim]")
            console.print()


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
