from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from triagent.audit import GENESIS_HASH, AuditError, AuditLog, canonical_json


def _fill(log: AuditLog, n: int = 5) -> None:
    for i in range(n):
        log.append("note", {"i": i, "text": "café"})


def _rewrite(path, lines):
    path.write_text("".join(ln + "\n" for ln in lines), encoding="utf-8", newline="\n")


def test_canonical_json_is_sorted_compact_utf8():
    assert canonical_json({"b": 1, "a": "é"}) == '{"a":"é","b":1}'.encode()


def test_canonical_json_rejects_nan():
    with pytest.raises(ValueError):
        canonical_json({"x": float("nan")})


def test_chain_links_and_verifies(log):
    _fill(log)
    entries = log.entries()
    assert entries[0]["prev_hash"] == GENESIS_HASH
    for a, b in zip(entries, entries[1:], strict=False):
        assert b["prev_hash"] == a["hash"]
    rep = log.verify()
    assert rep.ok and rep.count == 5 and rep.head == entries[-1]["hash"]


def test_missing_log_fails_verification(log):
    rep = log.verify()
    assert not rep.ok and "not found" in rep.errors[0]


def test_empty_log_without_head_fails_verification(log):
    log.path.write_text("", encoding="utf-8")
    assert not log.verify().ok


def test_blank_line_inserted_is_detected_and_blocks_append(log):
    _fill(log, 3)
    lines = log.path.read_text(encoding="utf-8").splitlines()
    lines.insert(1, "")
    _rewrite(log.path, lines)
    assert not log.verify().ok
    with pytest.raises(AuditError):
        log.append("n", {})


def test_timestamp_uses_injected_clock(tmp_path):
    fixed = datetime(2026, 3, 4, 5, 6, 7, tzinfo=UTC)
    log = AuditLog(tmp_path / "a.jsonl", clock=lambda: fixed)
    assert log.append("n", {})["ts"] == "2026-03-04T05:06:07.000000Z"


def test_modified_entry_is_detected(log):
    _fill(log)
    lines = log.path.read_text(encoding="utf-8").splitlines()
    obj = json.loads(lines[2])
    obj["data"]["i"] = 99
    lines[2] = json.dumps(obj)
    _rewrite(log.path, lines)
    rep = log.verify()
    assert not rep.ok and "hash mismatch" in rep.errors[0]


def test_modified_entry_with_recomputed_hash_breaks_next_link(log):
    from triagent.audit import entry_hash

    _fill(log)
    lines = log.path.read_text(encoding="utf-8").splitlines()
    obj = json.loads(lines[2])
    obj["data"]["i"] = 99
    del obj["hash"]
    obj["hash"] = entry_hash(obj)
    lines[2] = json.dumps(obj)
    _rewrite(log.path, lines)
    rep = log.verify()
    assert not rep.ok and "prev_hash" in rep.errors[0]


def test_deleted_middle_entry_is_detected(log):
    _fill(log)
    lines = log.path.read_text(encoding="utf-8").splitlines()
    del lines[2]
    _rewrite(log.path, lines)
    assert not log.verify().ok


def test_tail_truncation_is_detected_by_head_sidecar(log):
    _fill(log)
    lines = log.path.read_text(encoding="utf-8").splitlines()
    _rewrite(log.path, lines[:3])
    rep = log.verify()
    assert not rep.ok and "truncated" in rep.errors[0]


def test_tail_truncation_with_deleted_sidecar_is_detected_by_expected_head(log):
    _fill(log)
    head = log.verify().head
    lines = log.path.read_text(encoding="utf-8").splitlines()
    _rewrite(log.path, lines[:3])
    log.head_path.unlink()
    assert not log.verify().ok  # sidecar missing
    assert not log.verify(expected_head=head).ok
    assert log.verify(expected_head=json.loads(lines[2])["hash"]).ok


def test_inserted_entry_is_detected(log):
    _fill(log)
    other = AuditLog(log.path.parent / "other.jsonl")
    _fill(other, 1)
    lines = log.path.read_text(encoding="utf-8").splitlines()
    lines.insert(2, other.path.read_text(encoding="utf-8").splitlines()[0])
    _rewrite(log.path, lines)
    assert not log.verify().ok


def test_malformed_line_is_detected(log):
    _fill(log, 2)
    with log.path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write("not json\n")
    assert not log.verify().ok


def test_unserializable_data_is_refused_and_nothing_written(log):
    with pytest.raises(AuditError):
        log.append("n", {"x": object()})
    with pytest.raises(AuditError):
        log.append("n", {"x": float("inf")})
    assert log.entries() == []


def test_append_continues_existing_chain(tmp_path):
    p = tmp_path / "a.jsonl"
    _fill(AuditLog(p), 2)
    AuditLog(p).append("note", {"i": 2})
    rep = AuditLog(p).verify()
    assert rep.ok and rep.count == 3


def test_entries_are_stored_one_canonical_line_each(log):
    _fill(log, 2)
    raw = log.path.read_bytes()
    assert raw.count(b"\n") == 2 and b"\r" not in raw
    for line in raw.decode("utf-8").splitlines():
        assert canonical_json(json.loads(line)).decode("utf-8") == line


# ---- concurrency and crash recovery (R-03) ---------------------------------------------------


def test_threads_append_without_fork(tmp_path):
    import threading

    p = tmp_path / "t.jsonl"
    errors: list[Exception] = []

    def work(w: int) -> None:
        try:
            lg = AuditLog(p)
            for i in range(15):
                lg.append("note", {"w": w, "i": i})
        except Exception as exc:  # pragma: no cover - reported below
            errors.append(exc)

    threads = [threading.Thread(target=work, args=(w,)) for w in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    rep = AuditLog(p).verify()
    assert rep.ok and rep.count == 60
    assert [e["seq"] for e in AuditLog(p).entries()] == list(range(60))


def test_four_processes_append_without_fork(tmp_path):
    import multiprocessing

    from audit_worker import append_many

    p = tmp_path / "mp.jsonl"
    ctx = multiprocessing.get_context("spawn")
    procs = [ctx.Process(target=append_many, args=(str(p), w, 25)) for w in range(4)]
    for pr in procs:
        pr.start()
    for pr in procs:
        pr.join(timeout=120)
        assert pr.exitcode == 0
    lg = AuditLog(p)
    seqs = [e["seq"] for e in lg.entries()]
    assert len(seqs) == 100 and sorted(set(seqs)) == list(range(100))
    assert lg.verify().ok


def test_crash_between_log_and_head_is_repaired_on_next_append(log, monkeypatch):
    _fill(log, 2)
    real = log._write_head

    def boom(head, count):
        raise OSError("simulated crash")

    monkeypatch.setattr(log, "_write_head", boom)
    with pytest.raises(OSError):
        log.append("note", {"i": 2})
    monkeypatch.setattr(log, "_write_head", real)
    assert not log.verify().ok  # head is stale
    log.append("note", {"i": 3})
    rep = log.verify()
    assert rep.ok and rep.count == 4


def test_crash_on_first_append_is_repaired(log, monkeypatch):
    def boom(head, count):
        raise OSError("simulated crash")

    real = log._write_head
    monkeypatch.setattr(log, "_write_head", boom)
    with pytest.raises(OSError):
        log.append("note", {"i": 0})
    monkeypatch.setattr(log, "_write_head", real)
    log.append("note", {"i": 1})
    assert log.verify().ok and log.verify().count == 2


def test_head_ahead_of_log_blocks_append(log):
    _fill(log, 3)
    lines = log.path.read_text(encoding="utf-8").splitlines()
    _rewrite(log.path, lines[:2])
    with pytest.raises(AuditError):
        log.append("note", {})
    assert len(log.entries()) == 2


def test_removed_log_with_head_present_blocks_append(log):
    _fill(log, 2)
    log.path.unlink()
    with pytest.raises(AuditError):
        log.append("note", {})
