"""Metrics on a hand computed case (same case as the phase 3 gate) and the recorded run.

GT: BM-001 tp xss 79 a.js 10-12 | BM-002 tp authz 862 a.js 30-32 | BM-003 tp sqli 89 a.js 50 |
BM-004 tp path 22 b.js 5-8 | BM-005 trap sqli 89 a.js 70-72 | BM-006 trap xss 79 b.js 20-22 |
BM-007 trap cmdi 78 b.js 40 | BM-008 tp redirect 601 c.js 3.
Findings: f1 79 a:10 tp | f2 863 a:31 uncertain | f3 89 a:52 tp | f4 89 a:71 fp | f5 79 b:21 tp |
f6 78 b:40 uncertain | f7 601 c:3 fp | f8 798 d:1 tp.
Hand results (tolerance 2, loose, uncertain positive): tp 3 (001,002,003), fp 2 (006,007),
tn 1 (005), fn 2 (004 missed, 008 lost): precision 3/5, recall 3/5, f1 6/10, fpr 2/3,
retention 3/4. Other variants are in the asserts below, derived the same way by hand.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from triagent.benchmark.groundtruth import GroundTruth
from triagent.eval import EvalError, run_recorded, score
from triagent.models import Finding


def item(n: int, cwe: str, cat: str, label: str, f: str, a: int, b: int) -> dict[str, Any]:
    return {
        "id": f"BM-00{n}",
        "title": f"hand {n}",
        "cwe": [cwe],
        "category": cat,
        "label": label,
        "file": f,
        "start_line": a,
        "end_line": b,
        "anchor": "anchor",
        "poc": f"poc/BM-00{n}.js",
        "trap_kind": None if label == "tp" else "allowlist",
        "notes": "hand case",
    }


GT = GroundTruth.model_validate(
    {
        "schema_version": 1,
        "app": "hand",
        "corpus_date": "2026-10-01",
        "label_source": "poc",
        "labeled_by": "test",
        "items": [
            item(1, "CWE-79", "xss", "tp", "a.js", 10, 12),
            item(2, "CWE-862", "authz", "tp", "a.js", 30, 32),
            item(3, "CWE-89", "sqli", "tp", "a.js", 50, 50),
            item(4, "CWE-22", "path-traversal", "tp", "b.js", 5, 8),
            item(5, "CWE-89", "sqli", "fp-trap", "a.js", 70, 72),
            item(6, "CWE-79", "xss", "fp-trap", "b.js", 20, 22),
            item(7, "CWE-78", "command-injection", "fp-trap", "b.js", 40, 40),
            item(8, "CWE-601", "open-redirect", "tp", "c.js", 3, 3),
        ],
    }
)
RAW = [
    ("f1", "CWE-79", "a.js", 10, "likely_tp"),
    ("f2", "CWE-863", "a.js", 31, "uncertain"),
    ("f3", "CWE-89", "a.js", 52, "likely_tp"),
    ("f4", "CWE-89", "a.js", 71, "likely_fp"),
    ("f5", "CWE-79", "b.js", 21, "likely_tp"),
    ("f6", "CWE-78", "b.js", 40, "uncertain"),
    ("f7", "CWE-601", "c.js", 3, "likely_fp"),
    ("f8", "CWE-798", "d.js", 1, "likely_tp"),
]
FINDINGS = [
    Finding.model_validate(
        {
            "id": fid,
            "source_tool": "semgrep",
            "rule_id": f"r.{fid}",
            "cwe": [cwe],
            "location": {"file": f, "start_line": n, "end_line": n},
            "message": fid,
            "severity_scanner": "warning",
        }
    )
    for fid, cwe, f, n, _ in RAW
]
VERDICTS = {fid: v for fid, *_, v in RAW}


def close(a: float | None, b: float | None) -> bool:
    return a is None if b is None else a is not None and abs(a - b) < 1e-9


def check(v: dict[str, Any], tp, fp, tn, fn, p, r, f1, fpr, ret) -> None:  # noqa: ANN001
    assert (v["tp"], v["fp"], v["tn"], v["fn"]) == (tp, fp, tn, fn)
    for key, want in (
        ("precision", p),
        ("recall", r),
        ("f1", f1),
        ("fpr", fpr),
        ("tp_retention", ret),
    ):
        assert close(v[key], want), (key, v[key], want)


def test_loose_uncertain_positive_tolerance_two() -> None:
    res = score(GT, FINDINGS, VERDICTS, line_tolerance=2)["variants"]["cwe_loose"]
    v = res["uncertain_positive"]
    check(v, 3, 2, 1, 2, 0.6, 0.6, 0.6, 2 / 3, 0.75)
    outcomes = {i["id"]: i["outcome"] for i in v["items"]}
    assert outcomes == {
        "BM-001": "tp", "BM-002": "tp", "BM-003": "tp", "BM-004": "fn_missed",
        "BM-005": "tn", "BM-006": "fp", "BM-007": "fp", "BM-008": "fn_lost",
    }  # fmt: skip
    assert v["unlabeled_findings"] == ["f8"]
    pc = v["per_category"]
    assert pc["open-redirect"]["tp_retention"] == 0.0
    assert pc["path-traversal"]["tp_retention"] is None and pc["path-traversal"]["detected"] == 0
    assert pc["xss"] == {"tp_items": 1, "detected": 1, "retained": 1, "tp_retention": 1.0}
    # uncertain as negative: BM-002 lost, BM-007 becomes tn
    check(res["uncertain_negative"], 2, 1, 2, 3, 2 / 3, 0.4, 0.5, 1 / 3, 0.5)


def test_strict_cwe_drops_the_862_863_pair() -> None:
    res = score(GT, FINDINGS, VERDICTS, line_tolerance=2)["variants"]["cwe_strict"]
    check(res["uncertain_positive"], 2, 2, 1, 3, 0.5, 0.4, 4 / 9, 2 / 3, 2 / 3)
    check(res["uncertain_negative"], 2, 1, 2, 3, 2 / 3, 0.4, 0.5, 1 / 3, 2 / 3)
    assert res["uncertain_positive"]["unlabeled_findings"] == ["f2", "f8"]


def test_zero_tolerance_misses_the_offset_finding() -> None:
    res = score(GT, FINDINGS, VERDICTS, line_tolerance=0)["variants"]["cwe_loose"]
    check(res["uncertain_positive"], 2, 2, 1, 3, 0.5, 0.4, 4 / 9, 2 / 3, 2 / 3)
    assert res["uncertain_positive"]["unlabeled_findings"] == ["f3", "f8"]


def test_scanner_only_baseline_and_empty_denominators() -> None:
    base = score(GT, FINDINGS, None, line_tolerance=2)["variants"]["cwe_loose"]
    for unc in base.values():
        check(unc, 4, 3, 0, 1, 4 / 7, 0.8, 8 / 12, 1.0, 1.0)
    allfp = {k: "likely_fp" for k in VERDICTS}
    z = score(GT, FINDINGS, allfp, line_tolerance=2)["variants"]["cwe_loose"]["uncertain_positive"]
    check(z, 0, 0, 3, 5, None, 0.0, 0.0, 0.0, 0.0)


def test_bad_inputs_are_rejected() -> None:
    with pytest.raises(EvalError):
        score(GT, FINDINGS, {"f1": "likely_tp"}, line_tolerance=2)  # missing verdicts
    with pytest.raises(EvalError):
        score(GT, FINDINGS, {**VERDICTS, "f1": "maybe"}, line_tolerance=2)
    with pytest.raises(EvalError):
        score(GT, FINDINGS, {**VERDICTS, "ghost": "likely_tp"}, line_tolerance=2)
    with pytest.raises(EvalError):
        score(GT, FINDINGS, VERDICTS, line_tolerance=-1)


# ---- recorded run ---------------------------------------------------------------------------


def write_inputs(
    tmp: Path, meta_drop: str | None = None, drop_call: bool = False
) -> dict[str, Path]:
    import yaml

    gt_path = tmp / "gt.yaml"
    gt_path.write_text(
        yaml.safe_dump(GT.model_dump(mode="json"), sort_keys=False), encoding="utf-8"
    )
    fpath = tmp / "findings.json"
    fpath.write_text(json.dumps({"findings": [f.model_dump(mode="json") for f in FINDINGS]}))
    meta = {
        "model_id": "fake", "model_snapshot": "fake-1", "api_route": "api", "scanner": "semgrep",
        "scanner_version": "1.181.1", "ruleset": "p/javascript", "prompt_hash": "a" * 64,
        "temperature": 0.0, "context_limit_tokens": 8000, "corpus_date": "2026-10-01",
    }  # fmt: skip
    if meta_drop:
        meta.pop(meta_drop)
    calls = [
        {"finding_id": fid, "verdict": v, "cost_usd": 0.01 * (i + 1), "latency_ms": 100 * (i + 1),
         "truncated": i == 7}
        for i, (fid, *_, v) in enumerate(RAW)
    ]  # fmt: skip
    if drop_call:
        calls.pop()
    rpath = tmp / "rec.json"
    rpath.write_text(json.dumps({"meta": meta, "calls": calls}))
    return {"gt": gt_path, "findings": fpath, "rec": rpath}


def test_recorded_run_report_is_complete_and_deterministic(tmp_path: Path) -> None:
    p = write_inputs(tmp_path)
    r1 = run_recorded(p["gt"], p["findings"], p["rec"], tmp_path / "o1")
    run_recorded(p["gt"], p["findings"], p["rec"], tmp_path / "o2")
    assert (tmp_path / "o1" / "report.json").read_bytes() == (
        tmp_path / "o2" / "report.json"
    ).read_bytes()
    assert abs(r1["cost"]["usd_total"] - 0.36) < 1e-9 and r1["cost"]["calls"] == 8
    assert r1["latency"]["ms_total"] == 3600 and r1["latency"]["ms_mean"] == 450.0
    assert r1["metadata"]["context_truncated_calls"] == 1
    assert r1["metadata"]["label_source"] == "poc" and r1["metadata"]["mode"] == "recorded"
    md = (tmp_path / "o1" / "report.md").read_text(encoding="utf-8")
    assert all(f"BM-00{n}" in md for n in range(1, 9))


@pytest.mark.parametrize("drop", ["model_snapshot", "prompt_hash", "scanner_version"])
def test_recording_without_identification_is_rejected(tmp_path: Path, drop: str) -> None:
    p = write_inputs(tmp_path, meta_drop=drop)
    with pytest.raises(EvalError):
        run_recorded(p["gt"], p["findings"], p["rec"], tmp_path / "o")


def test_recording_with_missing_call_is_rejected(tmp_path: Path) -> None:
    p = write_inputs(tmp_path, drop_call=True)
    with pytest.raises(EvalError):
        run_recorded(p["gt"], p["findings"], p["rec"], tmp_path / "o")


# ---- review cycle 1: one-to-one matching, prefixes, duplicates, meta whitelist --------------


def one_finding(cwe: str, f: str, a: int, b: int, **extra: Any) -> Finding:
    return Finding.model_validate(
        {
            "id": extra.pop("id", "g1"),
            "source_tool": "semgrep",
            "rule_id": "r",
            "cwe": [cwe],
            "location": {"file": f, "start_line": a, "end_line": b},
            "message": "m",
            "severity_scanner": "warning",
            **extra,
        }
    )


def adjacent_gt(order: tuple[int, int] = (0, 1)) -> GroundTruth:
    x = item(1, "CWE-798", "hardcoded-secret", "tp", "c.js", 7, 7)
    y = item(2, "CWE-798", "hardcoded-secret", "fp-trap", "c.js", 8, 8)
    y["trap_kind"] = "placeholder"
    items = [x, y]
    return GroundTruth.model_validate(
        {
            "schema_version": 1, "app": "t", "corpus_date": "2026-10-01", "label_source": "poc",
            "labeled_by": "t", "items": [items[order[0]], items[order[1]]],
        }
    )  # fmt: skip


def outcomes(gt: GroundTruth, f: Finding, verdict: str) -> dict[str, str]:
    res = score(gt, [f], {f.id: verdict}, line_tolerance=2)
    v = res["variants"]["cwe_loose"]["uncertain_positive"]
    return {i["id"]: i["outcome"] for i in v["items"]}


def test_one_to_one_nearest_item_wins() -> None:
    gt = adjacent_gt()
    # finding on line 8 (distance 0 to BM-002, 1 to BM-001), judged false positive
    assert outcomes(gt, one_finding("CWE-798", "c.js", 8, 8), "likely_fp") == {
        "BM-001": "fn_missed",
        "BM-002": "tn",
    }
    # finding on line 7, judged true positive
    assert outcomes(gt, one_finding("CWE-798", "c.js", 7, 7), "likely_tp") == {
        "BM-001": "tp",
        "BM-002": "not_flagged",
    }


def test_one_to_one_tie_is_broken_by_item_id_regardless_of_gt_order() -> None:
    f = one_finding("CWE-798", "c.js", 7, 8)  # distance 0 to both
    for order in ((0, 1), (1, 0)):
        assert outcomes(adjacent_gt(order), f, "likely_tp") == {
            "BM-001": "tp",
            "BM-002": "not_flagged",
        }


def test_one_to_one_prefers_exact_cwe_over_family_match() -> None:
    gt = GroundTruth.model_validate(
        {
            "schema_version": 1, "app": "t", "corpus_date": "2026-10-01", "label_source": "poc",
            "labeled_by": "t",
            "items": [
                item(1, "CWE-863", "authz", "tp", "a.js", 10, 10),
                {
                    **item(2, "CWE-862", "authz", "fp-trap", "a.js", 10, 10),
                    "trap_kind": "authz-check",
                },
            ],
        }
    )  # fmt: skip
    assert outcomes(gt, one_finding("CWE-862", "a.js", 10, 10), "likely_tp") == {
        "BM-001": "fn_missed",
        "BM-002": "fp",
    }


def test_strip_prefix_duplicates_and_zero_match_warning() -> None:
    gt = adjacent_gt()
    real = one_finding("CWE-798", "benchmark/app/c.js", 7, 7, id="g1")
    dup = one_finding("CWE-798", "benchmark/app/c.js", 8, 8, id="g2", duplicate_of="g1")
    res = score(
        gt, [real, dup], {"g1": "likely_tp"}, line_tolerance=2,
        strip_prefixes=("nomatch/", "benchmark/app/"),
    )  # fmt: skip
    v = res["variants"]["cwe_loose"]["uncertain_positive"]
    assert (v["tp"], v["fp"], v["tn"], v["fn"]) == (1, 0, 0, 0)
    assert v["matched_findings_total"] == 1 and v["unlabeled_findings"] == []
    assert res["duplicates_skipped"] == 1 and res["warnings"] == []
    none = score(gt, [real, dup], {"g1": "likely_tp"}, line_tolerance=2)
    assert none["variants"]["cwe_loose"]["uncertain_positive"]["matched_findings_total"] == 0
    assert none["warnings"] and "strip-prefix" in none["warnings"][0]


def test_unknown_meta_keys_are_dropped_and_never_written(tmp_path: Path) -> None:
    p = write_inputs(tmp_path)
    rec = json.loads(p["rec"].read_text())
    rec["meta"]["api_key"] = "sk-test-LEAKVALUE"
    rec["meta"]["recorded_at"] = "2026-10-26T00:00:00Z"
    p["rec"].write_text(json.dumps(rec))
    report = run_recorded(p["gt"], p["findings"], p["rec"], tmp_path / "o")
    text = (tmp_path / "o" / "report.json").read_text(encoding="utf-8")
    assert "sk-test-LEAKVALUE" not in text
    assert report["metadata"]["dropped_meta_keys"] == ["api_key"]
    assert report["metadata"]["recorded_at"] == "2026-10-26T00:00:00Z"
