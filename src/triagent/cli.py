"""Command line entry point."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from triagent import __version__
from triagent.audit import AuditLog
from triagent.config import ConfigError, load_config
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
