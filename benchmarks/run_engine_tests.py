#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6.0", "aiohttp>=3.9", "rich>=13.0"]
# ///
"""
Run benchmark tests against the Aethis public API.

Tests the deterministic eligibility engine against golden test cases.
No API key needed — the public bundles endpoint is unauthenticated.

The project name is inferred from the dataset directory name:
    dataset/spacecraft-crew-certification/ -> project "spacecraft-crew-certification"

Usage:
    uv run run_engine_tests.py ../dataset/spacecraft-crew-certification/
    uv run run_engine_tests.py ../dataset/construction-all-risks/ --url http://localhost:8080
    uv run run_engine_tests.py ../dataset/ --all              # Run all domains
    uv run run_engine_tests.py ../dataset/construction-all-risks/ --concurrency 5
    uv run run_engine_tests.py ../dataset/construction-all-risks/ --sequential

Without uv:
    pip install pyyaml aiohttp rich
    python run_engine_tests.py ../dataset/spacecraft-crew-certification/
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

import aiohttp
import yaml
from rich.console import Console
from rich.table import Table

console = Console()
DEFAULT_API_URL = "https://api.aethis.ai"
DEFAULT_CONCURRENCY = 5

_DECISION_STYLE = {
    "eligible": "bold green",
    "not_eligible": "bold red",
    "undetermined": "bold yellow",
}

_GROUP_STATUS_LABEL = {
    "satisfied": ("passed", "green"),
    "not_satisfied": ("failed", "red"),
    "pending": ("pending", "yellow"),
}


def infer_project_name(example_dir: Path) -> str:
    """Infer the project name from the dataset directory name."""
    return example_dir.name


def load_tests(example_dir: Path) -> list:
    """Load test scenarios from the dataset directory."""
    path = example_dir / "scenarios.yaml"
    if not path.exists():
        path = example_dir / "tests" / "scenarios.yaml"
    if not path.exists():
        console.print("[red]ERROR:[/red] No test file found (tried scenarios.yaml and tests/scenarios.yaml)")
        sys.exit(1)
    with open(path) as f:
        data = yaml.safe_load(f)
    return data.get("tests", [])


async def discover_bundle(session: aiohttp.ClientSession, api_url: str, project_name: str, api_key: str | None = None) -> str:
    """Find the bundle_id for a project by matching section_id."""
    headers = {"X-API-Key": api_key} if api_key else {}
    async with session.get(f"{api_url}/api/v1/public/bundles", headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
        resp.raise_for_status()
        bundles = await resp.json()

    if not bundles:
        console.print("[red]ERROR:[/red] No public bundles found")
        sys.exit(1)

    normalized = project_name.replace("-", "_").lower()

    for b in bundles:
        section = b["section_id"].replace("-", "_").lower()
        if normalized in section or section in normalized:
            return b["bundle_id"]

    for b in bundles:
        if b["section_id"] == project_name:
            return b["bundle_id"]

    console.print(f"[red]ERROR:[/red] No bundle found matching project [bold]{project_name}[/bold]")
    for b in bundles:
        console.print(f"  [dim]-[/dim] {b['section_id']} [dim]({b['bundle_id']})[/dim]")
    sys.exit(1)


async def run_test(
    session: aiohttp.ClientSession,
    api_url: str,
    bundle_id: str,
    test: dict,
    *,
    no_cache: bool = False,
    semaphore: asyncio.Semaphore | None = None,
    api_key: str | None = None,
) -> dict:
    """Run a single test. Returns the full API response plus pass/fail."""
    payload = {
        "bundle_id": bundle_id,
        "field_values": test["inputs"],
        "include_explanation": True,
        "include_trace": True,
        "include_timing": True,
        "no_cache": no_cache,
    }
    headers = {"X-API-Key": api_key} if api_key else {}

    async def _do_request():
        last_error = None
        for attempt in range(5):
            try:
                async with session.post(
                    f"{api_url}/api/v1/public/decide",
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status == 429:
                        await asyncio.sleep(min(2 ** attempt, 30))
                        continue
                    resp.raise_for_status()
                    result = await resp.json()
                    actual = result["decision"]
                    expected = test["expect"]["outcome"]
                    result["passed"] = actual == expected
                    result["expected"] = expected
                    return result
            except Exception as e:
                last_error = e
                await asyncio.sleep(min(2 ** attempt, 30))
        return {"error": str(last_error or "429 after retries"), "passed": False}

    if semaphore:
        async with semaphore:
            return await _do_request()
    return await _do_request()


def print_result(name: str, result: dict) -> None:
    """Print a single test result with per-group evaluation status."""
    if "error" in result:
        console.print(f"  [white on red] FAIL [/white on red]  {name}")
        console.print(f"         [dim]API error: {result['error']}[/dim]")
        console.print()
        return

    actual = result["decision"]
    expected = result["expected"]
    passed = result["passed"]
    style = _DECISION_STYLE.get(actual, "")

    badge = "[black on green] PASS [/black on green]" if passed else "[white on red] FAIL [/white on red]"
    console.print(f"  {badge}  [bold]{name}[/bold]")

    # Decision + fields
    provided = result.get("fields_provided", 0)
    evaluated = result.get("fields_evaluated", 0)
    console.print(f"         [{style}]{actual}[/{style}] [dim]({provided}/{evaluated} fields provided)[/dim]")

    if not passed:
        console.print(f"         [dim]expected[/dim] [bold]{expected}[/bold] [dim]but got[/dim] [{style}]{actual}[/{style}]")

    # Per-group evaluation status from trace
    trace = result.get("trace") or {}
    group_statuses = trace.get("group_statuses") or {}
    if group_statuses:
        parts = []
        for group, status in group_statuses.items():
            label, color = _GROUP_STATUS_LABEL.get(status, (status.lower(), "dim"))
            parts.append(f"[{color}]{group}: {label}[/{color}]")
        console.print(f"         {' '.join(parts)}")

    # Undetermined: next question + optimal path
    if actual == "undetermined":
        nq = result.get("next_question")
        if nq:
            console.print(f"         [yellow]Next question:[/yellow] {nq['question']} [dim]({nq['field_id']})[/dim]")

        path = result.get("optimal_path")
        if path:
            remaining = [f"[dim]{p['field_id']}[/dim]" for p in path]
            console.print(f"         [yellow]Optimal path[/yellow] ({len(path)} remaining): {' [dim]->[/dim] '.join(remaining)}")

    # Missing fields for failures
    if not passed:
        missing = result.get("missing_fields")
        if missing:
            console.print(f"         [dim]Missing:[/dim] {', '.join(missing)}")

    # Timing
    timing = result.get("timing")
    if timing:
        total = timing.get("total_ms", 0)
        if timing.get("cache_hit"):
            console.print(f"         [dim]Timing:[/dim] [green]{total:.1f}ms[/green] [dim](CACHE HIT)[/dim]")
        else:
            parts = []
            compile_ms = timing.get("compilation_ms")
            eval_ms = timing.get("evaluation_ms")
            if compile_ms is not None:
                parts.append(f"compile {compile_ms:.1f}ms")
            if eval_ms is not None:
                parts.append(f"eval {eval_ms:.1f}ms")
            detail = f" [dim]({', '.join(parts)})[/dim]" if parts else ""
            console.print(f"         [dim]Timing:[/dim] {total:.1f}ms{detail}")

    console.print()


def print_provenance(results: list) -> None:
    """Print provenance summary -- inverted: source passages -> rules that cite them."""
    # Collect provenance from the first result that has trace data
    for r in results:
        trace = r.get("trace") or {}
        provenance = trace.get("provenance") or {}
        if not provenance:
            continue

        # Invert: group by source passage, list which rules cite it
        passage_to_rules: dict[str, dict] = {}
        for criterion_id, prov in provenance.items():
            for anchor in prov.get("anchors") or []:
                section = anchor.get("section_path", "")
                doc_id = anchor.get("doc_id", "")
                quote = anchor.get("quote", "")
                preview = quote.replace("\n", " ").strip()
                if len(preview) > 140:
                    preview = preview[:137] + "..."

                key = section or doc_id
                if key not in passage_to_rules:
                    passage_to_rules[key] = {"doc_id": doc_id, "preview": preview, "rules": []}
                if criterion_id not in passage_to_rules[key]["rules"]:
                    passage_to_rules[key]["rules"].append(criterion_id)

        if not passage_to_rules:
            continue

        console.print(f"  [bold]Provenance[/bold] [dim](source passages -> rules)[/dim]")
        console.print()
        for section_path, info in passage_to_rules.items():
            rules_str = ", ".join(info["rules"])
            console.print(f"    [cyan]{section_path}[/cyan]")
            if info["preview"]:
                console.print(f"      [italic dim]\"{info['preview']}\"[/italic dim]")
            console.print(f"      [dim]Rules:[/dim] {rules_str}")
            console.print()
        return

    # Fallback: check explanation for source_refs
    for r in results:
        explanation = r.get("explanation") or []
        has_refs = any(rule.get("source_refs") for rule in explanation)
        if has_refs:
            console.print(f"  [bold]Provenance[/bold] [dim](source references per rule)[/dim]")
            console.print()
            for rule in explanation:
                refs = rule.get("source_refs")
                if refs:
                    console.print(f"    [cyan]{rule.get('title', rule.get('criterion_id'))}[/cyan]")
                    console.print(f"      [dim]{', '.join(refs)}[/dim]")
            console.print()
            return


def discover_domains(dataset_root: Path) -> list[Path]:
    """Find all domain directories under the dataset root."""
    domains = []
    for child in sorted(dataset_root.iterdir()):
        if child.is_dir() and (child / "scenarios.yaml").exists():
            domains.append(child)
    return domains


async def run_domain(
    api_url: str,
    example_dir: Path,
    *,
    project_name: str | None = None,
    bundle_id: str | None = None,
    quiet: bool = False,
    no_cache: bool = False,
    concurrency: int = DEFAULT_CONCURRENCY,
    sequential: bool = False,
    api_key: str | None = None,
) -> tuple[int, int]:
    """Run all tests for a single domain. Returns (passed, failed)."""
    project = project_name or infer_project_name(example_dir)
    tests = load_tests(example_dir)

    async with aiohttp.ClientSession() as session:
        if not bundle_id:
            bundle_id = await discover_bundle(session, api_url, project, api_key)

        # Header
        console.print()
        header = Table(show_header=False, box=None, padding=(0, 1))
        header.add_column(style="dim", width=8)
        header.add_column()
        header.add_row("Project", f"[bold]{project}[/bold]")
        header.add_row("API", f"[dim]{api_url}[/dim]")
        header.add_row("Tests", str(len(tests)))
        header.add_row("Bundle", f"[dim]{bundle_id}[/dim]")
        mode = "sequential" if sequential else f"parallel ({concurrency} concurrent)"
        header.add_row("Mode", f"[dim]{mode}[/dim]")
        console.print(header)
        console.print()

        if sequential:
            # Sequential: one at a time, print as we go
            passed = 0
            failed = 0
            all_results = []
            for test in tests:
                name = test["name"]
                result = await run_test(session, api_url, bundle_id, test, no_cache=no_cache, api_key=api_key)
                all_results.append(result)

                if result.get("passed"):
                    passed += 1
                else:
                    failed += 1

                if quiet:
                    if result.get("passed"):
                        console.print(f"  [green]PASS[/green]  {name}")
                    else:
                        console.print(f"  [red]FAIL[/red]  {name}")
                else:
                    print_result(name, result)
        else:
            # Parallel: fire all requests bounded by semaphore
            semaphore = asyncio.Semaphore(concurrency)
            tasks = [
                run_test(session, api_url, bundle_id, test, no_cache=no_cache, semaphore=semaphore, api_key=api_key)
                for test in tests
            ]
            all_results = await asyncio.gather(*tasks)

            # Print results in original order
            passed = 0
            failed = 0
            for test, result in zip(tests, all_results):
                name = test["name"]
                if result.get("passed"):
                    passed += 1
                else:
                    failed += 1

                if quiet:
                    if result.get("passed"):
                        console.print(f"  [green]PASS[/green]  {name}")
                    else:
                        console.print(f"  [red]FAIL[/red]  {name}")
                else:
                    print_result(name, result)

    # Provenance summary (once, after all tests)
    if not quiet:
        print_provenance(all_results)

    # Summary
    total = passed + failed
    console.print(f"  [dim]{'---' * 20}[/dim]")
    if failed == 0:
        console.print(f"  [bold green]All {total} tests passed.[/bold green]")
    else:
        console.print(f"  [bold red]{failed}/{total} tests failed.[/bold red]")
    console.print()

    return passed, failed


async def async_main():
    parser = argparse.ArgumentParser(
        description="Run benchmark tests against the Aethis public API",
    )
    parser.add_argument("example_dir", type=Path, help="Path to dataset directory (e.g. ../dataset/construction-all-risks/) or parent with --all")
    parser.add_argument(
        "--url",
        default=os.environ.get("AETHIS_API_URL", DEFAULT_API_URL),
        help=f"API base URL (default: $AETHIS_API_URL or {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--project",
        help="Override project name (default: inferred from directory name)",
    )
    parser.add_argument(
        "--bundle-id",
        help="Skip auto-discovery and use this bundle_id directly",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Minimal output (pass/fail only, no explanations)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypass server caches to measure uncached performance",
    )
    parser.add_argument(
        "--concurrency", "-c",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help=f"Max concurrent API requests (default: {DEFAULT_CONCURRENCY})",
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Run tests sequentially instead of in parallel",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all domain directories found under example_dir",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("AETHIS_API_KEY"),
        help="API key for authenticated access (higher rate limits). Or set AETHIS_API_KEY env var.",
    )
    args = parser.parse_args()

    example_dir = args.example_dir.resolve()

    if args.all:
        # Run all domains under the given directory
        domains = discover_domains(example_dir)
        if not domains:
            console.print(f"[red]ERROR:[/red] No domain directories with scenarios.yaml found under {example_dir}")
            sys.exit(1)

        console.print(f"\n  [bold]Running all {len(domains)} domains[/bold]")
        console.print(f"  [dim]{', '.join(d.name for d in domains)}[/dim]\n")

        total_passed = 0
        total_failed = 0
        for domain_dir in domains:
            p, f = await run_domain(
                args.url, domain_dir,
                quiet=args.quiet,
                no_cache=args.no_cache,
                concurrency=args.concurrency,
                sequential=args.sequential,
                api_key=args.api_key,
            )
            total_passed += p
            total_failed += f

        # Grand total
        grand_total = total_passed + total_failed
        console.print(f"  [bold]{'=' * 60}[/bold]")
        if total_failed == 0:
            console.print(f"  [bold green]GRAND TOTAL: All {grand_total} tests passed across {len(domains)} domains.[/bold green]")
        else:
            console.print(f"  [bold red]GRAND TOTAL: {total_failed}/{grand_total} tests failed across {len(domains)} domains.[/bold red]")
        console.print()

        sys.exit(0 if total_failed == 0 else 1)
    else:
        if not example_dir.is_dir():
            console.print(f"[red]ERROR:[/red] {example_dir} is not a directory")
            sys.exit(1)

        p, f = await run_domain(
            args.url, example_dir,
            project_name=args.project,
            bundle_id=args.bundle_id,
            quiet=args.quiet,
            no_cache=args.no_cache,
            concurrency=args.concurrency,
            sequential=args.sequential,
            api_key=args.api_key,
        )
        sys.exit(0 if f == 0 else 1)


def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
