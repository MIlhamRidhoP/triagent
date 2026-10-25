"""Dedup keeps every finding (I-01), is order independent and uses CWE families."""

from __future__ import annotations

import itertools
import random

import pytest

from conftest import make_finding
from triagent.audit import AuditLog
from triagent.models import Lifecycle
from triagent.normalize import dedup, enrich_family, normalize_findings


def mk(
    i, rule="r.a", cwe=("CWE-79",), start=10, end=None, file="a.js", sev="warning", tool="semgrep"
):
    return make_finding(
        id=f"f-{i}",
        rule_id=rule,
        cwe=list(cwe),
        source_tool=tool,
        location={"file": file, "start_line": start, "end_line": end or start},
        severity_scanner=sev,
    )


def run(findings, tmp_path, **kw):
    return dedup(findings, log=AuditLog(tmp_path / "a.jsonl"), **kw)


def dup_map(out):
    return {f.id: f.duplicate_of for f in out}


def test_different_rules_same_cwe_same_line_are_duplicates(tmp_path):
    out = run([mk(1, "r.a", sev="warning"), mk(2, "r.b", sev="error")], tmp_path)
    assert dup_map(out) == {"f-1": "f-2", "f-2": None}


def test_nothing_is_dropped_and_order_is_kept(tmp_path):
    fs = [mk(i, f"r.{i}", start=10 + i % 3) for i in range(30)]
    out = run(fs, tmp_path)
    assert [f.id for f in out] == [f.id for f in fs]
    assert all(f.lifecycle is Lifecycle.DEDUPED for f in out)
    assert all(f.cwe == g.cwe and f.message == g.message for f, g in zip(out, fs, strict=True))


def test_every_duplicate_points_to_an_existing_canonical(tmp_path):
    rnd = random.Random(1)
    fs = [
        mk(
            i,
            f"r.{rnd.randint(0, 4)}",
            cwe=rnd.choice([("CWE-79",), ("CWE-95",), ("CWE-89",)]),
            start=rnd.randint(1, 30),
        )
        for i in range(80)
    ]
    out = run(fs, tmp_path)
    ids = {f.id for f in out}
    canon = {f.id for f in out if f.duplicate_of is None}
    for f in out:
        if f.duplicate_of:
            assert f.duplicate_of in ids and f.duplicate_of in canon and f.duplicate_of != f.id


def test_different_cwe_family_not_duplicate(tmp_path):
    out = run([mk(1, "r.a", ("CWE-79",)), mk(2, "r.b", ("CWE-89",))], tmp_path)
    assert all(f.duplicate_of is None for f in out)


def test_loose_family_pair_862_863_is_duplicate(tmp_path):
    out = run([mk(1, "a", ("CWE-862",), start=30), mk(2, "b", ("CWE-863",), start=31)], tmp_path)
    assert dup_map(out) == {"f-1": None, "f-2": "f-1"}


def test_different_file_or_far_lines_not_duplicate(tmp_path):
    out = run([mk(1, "a"), mk(2, "b", file="b.js"), mk(3, "c", start=40)], tmp_path)
    assert all(f.duplicate_of is None for f in out)


def test_line_window_boundary(tmp_path):
    near = [mk(1, "a", start=10), mk(2, "b", start=12)]
    assert dup_map(run(near, tmp_path, line_window=2))["f-2"] == "f-1"
    assert dup_map(run(near, tmp_path, line_window=1))["f-2"] is None


def test_same_rule_adjacent_lines_are_distinct_but_overlap_is_duplicate(tmp_path):
    adjacent = run([mk(1, "r", start=50), mk(2, "r", start=51)], tmp_path)
    assert all(f.duplicate_of is None for f in adjacent)
    overlap = run([mk(1, "r", start=50, end=52), mk(2, "r", start=51)], tmp_path)
    assert sum(1 for f in overlap if f.duplicate_of) == 1


def test_no_cwe_only_same_rule_overlap_merges(tmp_path):
    out = run(
        [mk(1, "x", cwe=(), start=70), mk(2, "y", cwe=(), start=70), mk(3, "x", cwe=(), start=70)],
        tmp_path,
    )
    assert out[1].duplicate_of is None
    assert (out[0].duplicate_of, out[2].duplicate_of).count(None) == 1


def test_one_side_without_cwe_does_not_merge_different_rules(tmp_path):
    out = run([mk(1, "x", cwe=()), mk(2, "y", cwe=("CWE-79",))], tmp_path)
    assert all(f.duplicate_of is None for f in out)


def test_multi_cwe_overlap_merges_and_keeps_all_cwes(tmp_path):
    a = mk(1, "m", ("CWE-89", "CWE-79"), start=90)
    b = mk(2, "n", ("CWE-79",), start=91)
    out = run([a, b], tmp_path)
    assert dup_map(out) == {"f-1": None, "f-2": "f-1"}
    assert out[0].cwe == ["CWE-89", "CWE-79"]


def test_cross_tool_duplicates(tmp_path):
    out = run([mk(1, "r", tool="semgrep"), mk(2, "q", tool="codeql", sev="error")], tmp_path)
    assert dup_map(out) == {"f-1": "f-2", "f-2": None}


def test_unknown_location_never_merged(tmp_path):
    out = run(
        [mk(1, "a", file="<unknown>", start=1), mk(2, "b", file="<unknown>", start=1)], tmp_path
    )
    assert all(f.duplicate_of is None for f in out)


def test_no_chains_far_ends_of_a_line_run_stay_separate(tmp_path):
    fs = [mk(i, f"r.{i}", start=10 + 2 * i) for i in range(6)]  # 10,12,...,20
    out = run(fs, tmp_path)
    canon = [f for f in out if f.duplicate_of is None]
    assert len(canon) >= 2  # window 2 from a canonical cannot reach everything


@pytest.mark.parametrize("seed", range(5))
def test_result_independent_of_input_order(tmp_path, seed):
    fs = [
        mk(
            i,
            f"r.{i % 5}",
            cwe=[("CWE-79",), ("CWE-95",), ("CWE-862",), ("CWE-863",)][i % 4],
            start=5 + (i * 3) % 17,
            sev=["error", "warning", "note", None][i % 4],
        )
        for i in range(40)
    ]
    base = dup_map(run(fs, tmp_path))
    shuffled = fs[:]
    random.Random(seed).shuffle(shuffled)
    assert dup_map(run(shuffled, tmp_path)) == base


def test_every_transition_is_audited_once(tmp_path):
    log = AuditLog(tmp_path / "a.jsonl")
    fs = [mk(1, "a"), mk(2, "b"), mk(3, "c", ("CWE-89",))]
    dedup(fs, log=log)
    entries = [e for e in log.entries() if e["type"] == "status_change"]
    assert sorted(e["data"]["finding_id"] for e in entries) == ["f-1", "f-2", "f-3"]
    assert all(e["data"]["from"] == "raw" and e["data"]["to"] == "deduped" for e in entries)
    assert log.verify().ok


def test_rejects_non_raw_duplicate_ids_and_bad_window(tmp_path):
    log = AuditLog(tmp_path / "a.jsonl")
    done = dedup([mk(1)], log=log)
    with pytest.raises(ValueError):
        dedup(done, log=log)
    with pytest.raises(ValueError):
        dedup([mk(1), mk(1, "b")], log=log)
    with pytest.raises(ValueError):
        dedup([mk(1)], log=log, line_window=-1)
    assert dedup([], log=log) == []


def test_normalize_fills_family_from_first_cwe(tmp_path):
    out = normalize_findings(
        [mk(1, "a", ("CWE-89", "CWE-79")), mk(2, "b", ())], log=AuditLog(tmp_path / "a.jsonl")
    )
    assert out[0].cwe_family == "CWE-943" and out[1].cwe_family is None
    kept = enrich_family(mk(3).model_copy(update={"cwe_family": "CWE-1"}))
    assert kept.cwe_family == "CWE-1"


def test_no_finding_is_ever_suppressed_by_dedup(tmp_path):
    out = run([mk(i, f"r.{i}") for i in range(10)], tmp_path)
    assert all(f.lifecycle is not Lifecycle.SUPPRESSED and f.human_decision is None for f in out)
    assert len(list(itertools.chain(out))) == 10
