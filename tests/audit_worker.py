"""Worker for the multi-process audit test (spawn-safe, importable by name)."""

from __future__ import annotations

from triagent.audit import AuditLog


def append_many(path: str, worker: int, n: int) -> None:
    log = AuditLog(path)
    for i in range(n):
        log.append("note", {"worker": worker, "i": i})
