"""`triagent ingest` end to end, golden output on the real Semgrep SARIF."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from triagent.cli import app

FIX = Path(__file__).parent / "fixtures"
REAL = FIX / "sarif" / "semgrep-1.181.1-js-sample.sarif"
GOLDEN = FIX / "golden" / "semgrep-1.181.1-js-sample.findings.json"
runner = CliRunner()


def ingest(tmp_path, sarif=REAL, *extra, name="out.json"):
    out = tmp_path / name
    res = runner.invoke(
        app,
        ["ingest", str(sarif), "--out", str(out), "--audit-log", str(tmp_path / "a.jsonl"), *extra],
    )
    return res, out


def test_golden_matches(tmp_path):
    res, out = ingest(tmp_path, REAL, "--strip-prefix", "/src")
    assert res.exit_code == 0, res.output
    got = json.loads(out.read_text(encoding="utf-8"))
    want = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert got["findings"] == want["findings"]
    assert got["tool_versions"] == ["semgrep 1.181.1"]


def test_golden_by_hand():
    want = json.loads(GOLDEN.read_text(encoding="utf-8"))["findings"]
    by = {f["rule_id"].rsplit(".", 1)[-1]: f for f in want}
    assert len(want) == 4
    assert by["raw-html-format"]["duplicate_of"] == by["direct-response-write"]["id"]
    assert by["direct-response-write"]["duplicate_of"] is None
    assert by["code-string-concat"]["cwe"] == ["CWE-95"]
    assert by["express-open-redirect"]["cwe_family"] == "CWE-610"
    assert all(f["lifecycle"] == "deduped" for f in want)


def test_two_runs_same_ids_and_audit_verifies(tmp_path):
    r1, o1 = ingest(tmp_path, REAL, "--strip-prefix", "/src", name="1.json")
    r2, o2 = ingest(tmp_path, REAL, "--strip-prefix", "/src", name="2.json")
    assert r1.exit_code == r2.exit_code == 0
    assert o1.read_bytes() == o2.read_bytes()
    v = runner.invoke(app, ["verify-audit", str(tmp_path / "a.jsonl")])
    assert v.exit_code == 0, v.output


def test_no_dedup_keeps_raw(tmp_path):
    res, out = ingest(tmp_path, REAL, "--no-dedup")
    assert res.exit_code == 0
    fs = json.loads(out.read_text(encoding="utf-8"))["findings"]
    assert len(fs) == 4 and all(f["lifecycle"] == "raw" and f["duplicate_of"] is None for f in fs)
    assert not (tmp_path / "a.jsonl").exists()


def test_stdout_output(tmp_path):
    res = runner.invoke(
        app, ["ingest", str(REAL), "--audit-log", str(tmp_path / "a.jsonl"), "--no-dedup"]
    )
    assert res.exit_code == 0
    assert json.loads(res.stdout)["findings"]


def test_malformed_input_is_a_clean_error(tmp_path):
    bad = tmp_path / "bad.sarif"
    bad.write_text('{"version": "2.1.0", "runs": [', encoding="utf-8")
    res, _ = ingest(tmp_path, bad)
    assert res.exit_code == 1 and "error:" in res.output and "Traceback" not in res.output
    res, _ = ingest(tmp_path, tmp_path / "missing.sarif")
    assert res.exit_code == 1


def test_non_object_results_exit_2_but_output_written(tmp_path):
    p = tmp_path / "odd.sarif"
    p.write_text(
        json.dumps(
            {
                "version": "2.1.0",
                "runs": [
                    {"tool": {"driver": {"name": "x"}}, "results": [{"ruleId": "r"}, 5, None]}
                ],
            }
        ),
        encoding="utf-8",
    )
    res, out = ingest(tmp_path, p)
    assert res.exit_code == 2
    d = json.loads(out.read_text(encoding="utf-8"))
    assert len(d["findings"]) == 1 and len(d["skipped"]) == 2


def test_needs_exactly_one_source(tmp_path):
    assert runner.invoke(app, ["ingest"]).exit_code == 2
    res = runner.invoke(app, ["ingest", str(REAL), "--run-semgrep", str(tmp_path)])
    assert res.exit_code == 2


def test_run_semgrep_option_uses_adapter(tmp_path, monkeypatch):
    import triagent.cli as cli
    from triagent.ingest.sarif import parse_sarif

    monkeypatch.setattr(
        cli, "run_semgrep", lambda target: parse_sarif(REAL, strip_prefixes=("/src",))
    )
    out = tmp_path / "o.json"
    res = runner.invoke(
        app,
        [
            "ingest",
            "--run-semgrep",
            str(tmp_path),
            "--out",
            str(out),
            "--audit-log",
            str(tmp_path / "a.jsonl"),
        ],
    )
    assert res.exit_code == 0, res.output
    assert len(json.loads(out.read_text(encoding="utf-8"))["findings"]) == 4
