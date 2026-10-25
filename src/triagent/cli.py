"""Command line entry point."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from triagent import __version__
from triagent.audit import AuditLog
from triagent.config import ConfigError, load_config
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
