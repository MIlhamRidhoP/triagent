"""Command line entry point."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from triagent import __version__
from triagent.audit import AuditLog
from triagent.benchmark.groundtruth import validate_root
from triagent.benchmark.hints import check_names
from triagent.benchmark.mutate import MutationError, mutate_root, parse_ops
from triagent.benchmark.poc import DockerError, run_poc_suite, run_selftest
from triagent.config import ConfigError, load_config
from triagent.eval.metrics import EvalError
from triagent.eval.metrics import score as eval_score
from triagent.eval.run import load_findings, load_gt, load_verdicts, run_recorded
from triagent.ingest.sarif import ParseResult, SarifError, parse_sarif
from triagent.ingest.semgrep import SemgrepError, run_semgrep
from triagent.normalize import DEFAULT_LINE_WINDOW, normalize_findings
from triagent.schema_export import check_all, export_all

app = typer.Typer(
    name="triagent",
    help="Triage SAST alerts into evidence-backed findings. Never drops a finding.",
    no_args_is_help=True,
    add_completion=False,
)


benchmark_app = typer.Typer(
    help="Benchmark tooling: ground truth, PoC runs in Docker, mutation variants.",
    no_args_is_help=True,
)
app.add_typer(benchmark_app, name="benchmark")
eval_app = typer.Typer(
    help="Triage evaluation against the benchmark (offline).", no_args_is_help=True
)
app.add_typer(eval_app, name="eval")


def _version(value: bool) -> None:
    if value:
        typer.echo(f"triagent {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version, is_eager=True, help="Show version and exit."),
    ] = False,
) -> None:
    """triagent command line."""


@app.command("check-config")
def check_config(
    path: Annotated[Path, typer.Argument(help="Path to .triagent.yml")] = Path(".triagent.yml"),
) -> None:
    """Validate a .triagent.yml file."""
    try:
        cfg = load_config(path)
    except ConfigError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"ok: {path} (mode={cfg.mode}, models={','.join(cfg.models)})")


@app.command("verify-audit")
def verify_audit(
    path: Annotated[Path, typer.Argument(help="Audit log (JSON lines)")],
    expected_head: Annotated[
        str | None, typer.Option(help="Head hash stored elsewhere, e.g. in run metadata.")
    ] = None,
) -> None:
    """Verify the hash chain and head of an audit log. Exit 1 if broken."""
    report = AuditLog(path).verify(expected_head=expected_head)
    if report.ok:
        typer.echo(f"ok: {report.count} entries, head {report.head}")
        return
    for err in report.errors:
        typer.echo(f"error: {err}", err=True)
    raise typer.Exit(1)


@app.command("export-schema")
def export_schema(
    out: Annotated[Path, typer.Option(help="Output directory")] = Path("schemas"),
    check: Annotated[
        bool, typer.Option("--check", help="Do not write; fail if files differ from the models.")
    ] = False,
) -> None:
    """Export (or check) the JSON Schemas of the data model."""
    if check:
        problems = check_all(out)
        if problems:
            for p in problems:
                typer.echo(f"error: {p}", err=True)
            raise typer.Exit(1)
        typer.echo("ok: schemas match the models")
        return
    for p in export_all(out):
        typer.echo(f"wrote {p}")


@app.command("ingest")
def ingest(
    sarif: Annotated[Path | None, typer.Argument(help="SARIF 2.1.x file to ingest.")] = None,
    run_semgrep_on: Annotated[
        Path | None,
        typer.Option("--run-semgrep", help="Scan this directory with the pinned Semgrep image."),
    ] = None,
    out: Annotated[
        Path | None, typer.Option(help="Write findings JSON here (default: stdout).")
    ] = None,
    audit_log: Annotated[Path, typer.Option(help="Audit log for status changes.")] = Path(
        ".triagent/audit.jsonl"
    ),
    strip_prefix: Annotated[
        list[str] | None, typer.Option(help="Path prefix to remove from file URIs. Repeatable.")
    ] = None,
    line_window: Annotated[
        int, typer.Option(min=0, help="Line distance for duplicate detection.")
    ] = DEFAULT_LINE_WINDOW,
    no_dedup: Annotated[
        bool, typer.Option("--no-dedup", help="Keep findings raw; skip normalization.")
    ] = False,
) -> None:
    """Parse scanner output into findings, fill CWE families and mark duplicates (none dropped)."""
    if (sarif is None) == (run_semgrep_on is None):
        typer.echo("error: give exactly one of SARIF or --run-semgrep", err=True)
        raise typer.Exit(2)
    try:
        if sarif is not None:
            parsed: ParseResult = parse_sarif(sarif, strip_prefixes=tuple(strip_prefix or ()))
        else:
            assert run_semgrep_on is not None
            parsed = run_semgrep(run_semgrep_on)
    except (SarifError, SemgrepError, ValueError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc

    findings = parsed.findings
    if not no_dedup:
        findings = normalize_findings(findings, log=AuditLog(audit_log), line_window=line_window)
    doc = {
        "tool_versions": parsed.tool_versions,
        "findings": [f.model_dump(mode="json") for f in findings],
        "warnings": parsed.warnings,
        "skipped": parsed.skipped,
    }
    text = json.dumps(doc, indent=2, ensure_ascii=True) + "\n"
    if out is None:
        typer.echo(text, nl=False)
    else:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8", newline="\n")
    dups = sum(1 for f in findings if f.duplicate_of)
    typer.echo(
        f"ingested {len(findings)} findings ({dups} duplicates kept), "
        f"{len(parsed.warnings)} warnings, {len(parsed.skipped)} skipped",
        err=True,
    )
    for w in parsed.warnings:
        typer.echo(f"warning: {w}", err=True)
    if parsed.skipped:
        raise typer.Exit(2)


DEFAULT_BENCHMARK_ROOT = Path("benchmark")


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline=chr(10)) as fh:
        fh.write(json.dumps(data, indent=2) + chr(10))


@benchmark_app.command("validate")
def benchmark_validate(
    root: Annotated[Path, typer.Option(help="Benchmark root (app/, poc/, ground-truth.yaml).")] = (
        DEFAULT_BENCHMARK_ROOT
    ),
    gt: Annotated[
        Path | None, typer.Option(help="Ground truth file (default: ROOT/ground-truth.yaml).")
    ] = None,
) -> None:
    """Check ground truth shape, files, line ranges, anchors and PoC scripts. Exit 1 if invalid."""
    problems = validate_root(root, gt)
    if problems:
        for line in problems:
            typer.echo(line)
        raise typer.Exit(1)
    typer.echo(f"ok: {root} ground truth is valid")


@benchmark_app.command("check-names")
def benchmark_check_names(
    root: Annotated[Path, typer.Option(help="Benchmark root to check.")] = DEFAULT_BENCHMARK_ROOT,
) -> None:
    """Fail when a name, string literal or file name hints at a label (pitfall P5)."""
    problems = check_names(root)
    if problems:
        for line in problems:
            typer.echo(line)
        raise typer.Exit(1)
    typer.echo(f"ok: {root} has no label hints in names")


@benchmark_app.command("mutate")
def benchmark_mutate(
    out: Annotated[
        Path, typer.Option(help="New directory for the variant (a full benchmark root).")
    ],
    root: Annotated[Path, typer.Option(help="Benchmark root to mutate.")] = DEFAULT_BENCHMARK_ROOT,
    seed: Annotated[
        int, typer.Option(help="Seed: same seed and ops give an identical variant.")
    ] = 1,
    ops: Annotated[
        str, typer.Option(help="Comma separated: rename, strip-comments, style.")
    ] = "rename,strip-comments",
) -> None:
    """Write a semantics-preserving variant with its ground truth shifted and validated."""
    try:
        record = mutate_root(root, out, seed=seed, ops=parse_ops(ops))
    except MutationError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"ok: wrote {out} (ops={','.join(record['ops'])}, {len(record['renames'])} renames)")


@benchmark_app.command("poc")
def benchmark_poc(
    out: Annotated[Path, typer.Option(help="Write the result JSON here.")],
    root: Annotated[Path, typer.Option(help="Benchmark root to run.")] = DEFAULT_BENCHMARK_ROOT,
    items: Annotated[
        str | None, typer.Option(help="Comma separated item ids (default: all).")
    ] = None,
) -> None:
    """Run each item's PoC in the isolated Docker stack. Exit 1 if an item contradicts its label."""
    wanted = [x.strip() for x in items.split(",") if x.strip()] if items else None
    try:
        result = run_poc_suite(root, items=wanted)
    except DockerError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(2) from exc
    _write_json(out, result)
    for r in result["items"]:
        mark = "ok  " if r["ok"] else "FAIL"
        typer.echo(f"{mark} {r['id']} {r['label']:<7} exit={r['exit_code']} {r['evidence'][:90]}")
    if not result["network"]["internal"]:
        typer.echo("error: the benchmark network is not internal", err=True)
    if not result["ok"]:
        raise typer.Exit(1)


@benchmark_app.command("selftest")
def benchmark_selftest(
    out: Annotated[Path, typer.Option(help="Write the result JSON here.")],
) -> None:
    """Prove the isolation (no egress, non-root, read-only) from inside the PoC container."""
    try:
        result = run_selftest()
    except DockerError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(2) from exc
    _write_json(out, result)
    for name, res in result["containers"].items():
        for key, value in sorted(res.items()):
            typer.echo(f"{name}.{key}: {value}")
    typer.echo(f"network_internal: {result['network_internal']}")
    if not result["ok"]:
        raise typer.Exit(1)


@eval_app.command("score")
def eval_score_cmd(
    ground_truth: Annotated[Path, typer.Option(help="ground-truth.yaml")],
    findings: Annotated[Path, typer.Option(help="Findings JSON from `triagent ingest`.")],
    out: Annotated[Path, typer.Option(help="Write the metrics JSON here.")],
    verdicts: Annotated[
        Path | None, typer.Option(help="Verdicts JSON. Omit for the scanner-only baseline.")
    ] = None,
    line_tolerance: Annotated[int, typer.Option(min=0, help="Lines of slack for matching.")] = 2,
    strip_prefix: Annotated[
        list[str] | None, typer.Option(help="Path prefix to strip from finding paths. Repeatable.")
    ] = None,
) -> None:
    """Compute precision, recall, F1, FPR and TP retention (strict and loose CWE)."""
    try:
        gt = load_gt(ground_truth)
        result = eval_score(
            gt,
            load_findings(findings),
            load_verdicts(verdicts) if verdicts else None,
            line_tolerance=line_tolerance,
            strip_prefixes=tuple(strip_prefix or ()),
        )
    except EvalError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc
    for w in result["warnings"]:
        typer.echo(f"warning: {w}", err=True)
    _write_json(out, result)
    typer.echo(f"ok: wrote {out}")


@eval_app.command("run")
def eval_run_cmd(
    ground_truth: Annotated[Path, typer.Option(help="ground-truth.yaml")],
    findings: Annotated[Path, typer.Option(help="Findings JSON from `triagent ingest`.")],
    recording: Annotated[Path, typer.Option(help="Recorded triage calls (no network, I-10).")],
    out_dir: Annotated[Path, typer.Option(help="Directory for report.json and report.md.")],
    line_tolerance: Annotated[int, typer.Option(min=0, help="Lines of slack for matching.")] = 2,
    strip_prefix: Annotated[
        list[str] | None, typer.Option(help="Path prefix to strip from finding paths. Repeatable.")
    ] = None,
) -> None:
    """Replay a recorded triage run and write the report."""
    try:
        report = run_recorded(
            ground_truth,
            findings,
            recording,
            out_dir,
            line_tolerance=line_tolerance,
            strip_prefixes=tuple(strip_prefix or ()),
        )
    except EvalError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc
    for w in report["results"]["warnings"]:
        typer.echo(f"warning: {w}", err=True)
    typer.echo(f"ok: wrote {out_dir} ({report['cost']['calls']} calls)")
