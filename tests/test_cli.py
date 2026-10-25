from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from typer.testing import CliRunner

from triagent import __version__
from triagent.audit import AuditLog
from triagent.cli import app

runner = CliRunner()
SRC = Path(__file__).resolve().parent.parent / "src"


def test_help_lists_commands():
    res = runner.invoke(app, ["--help"])
    assert res.exit_code == 0
    for name in ("check-config", "verify-audit", "export-schema"):
        assert name in res.output


def test_version():
    res = runner.invoke(app, ["--version"])
    assert res.exit_code == 0 and __version__ in res.output


def test_module_entry_point_runs():
    env = {**os.environ, "PYTHONPATH": str(SRC), "PYTHONIOENCODING": "utf-8"}
    out = subprocess.run(
        [sys.executable, "-m", "triagent", "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        env=env,
    )
    assert out.returncode == 0 and "triagent" in out.stdout.lower()


def test_check_config(tmp_path):
    good = tmp_path / "good.yml"
    good.write_text("models: [a]\n", encoding="utf-8")
    bad = tmp_path / "bad.yml"
    bad.write_text("models: []\n", encoding="utf-8")
    assert runner.invoke(app, ["check-config", str(good)]).exit_code == 0
    assert runner.invoke(app, ["check-config", str(bad)]).exit_code == 1
    assert runner.invoke(app, ["check-config", str(tmp_path / "none.yml")]).exit_code == 1


def test_verify_audit_exit_codes(tmp_path):
    log = AuditLog(tmp_path / "a.jsonl")
    for i in range(3):
        log.append("n", {"i": i})
    assert runner.invoke(app, ["verify-audit", str(log.path)]).exit_code == 0
    lines = log.path.read_text(encoding="utf-8").splitlines()
    log.path.write_text("\n".join(lines[:2]) + "\n", encoding="utf-8", newline="\n")
    assert runner.invoke(app, ["verify-audit", str(log.path)]).exit_code == 1


def test_export_schema_and_check(tmp_path):
    assert runner.invoke(app, ["export-schema", "--out", str(tmp_path)]).exit_code == 0
    assert runner.invoke(app, ["export-schema", "--check", "--out", str(tmp_path)]).exit_code == 0
    (tmp_path / "finding.schema.json").write_text("{}\n", encoding="utf-8")
    assert runner.invoke(app, ["export-schema", "--check", "--out", str(tmp_path)]).exit_code == 1
