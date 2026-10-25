"""Hash-chained audit log in JSON lines (D-17, D-25, R-09).

Each entry stores ``prev_hash`` and ``hash``. The hash is SHA-256 over the canonical JSON of the
entry without its ``hash`` field (sorted keys, no whitespace, UTF-8). A head sidecar
(``<log>.head``) stores the last hash and entry count so that truncating the tail is detected;
for stronger guarantees copy the head hash into run metadata stored elsewhere and pass it as
``expected_head`` to :meth:`AuditLog.verify`.

Writers are serialised with an OS lock on ``<log>.lock`` (threads and processes). Inside the
lock, ``append`` reconciles the head sidecar with the log before writing.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from triagent.models import SHA256_PATTERN, LlmCall

GENESIS_HASH = "0" * 64
LOCK_TIMEOUT_S = 30.0

_THREAD_LOCKS: dict[str, threading.Lock] = {}
_THREAD_LOCKS_GUARD = threading.Lock()


def _thread_lock(key: str) -> threading.Lock:
    with _THREAD_LOCKS_GUARD:
        return _THREAD_LOCKS.setdefault(key, threading.Lock())


class AuditError(Exception):
    """Raised when an entry cannot be written."""


class AuditEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seq: int = Field(ge=0)
    ts: str = Field(min_length=1)
    type: str = Field(min_length=1)
    data: dict[str, Any]
    prev_hash: str = Field(pattern=SHA256_PATTERN)
    hash: str = Field(pattern=SHA256_PATTERN)


def canonical_json(obj: Any) -> bytes:
    """Canonical JSON: sorted keys, no whitespace, UTF-8, no NaN or Infinity."""
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def entry_hash(entry_without_hash: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(entry_without_hash)).hexdigest()


@dataclass
class VerifyReport:
    ok: bool
    count: int
    head: str
    errors: list[str] = field(default_factory=list)


def _utc_now() -> datetime:
    return datetime.now(UTC)


class AuditLog:
    def __init__(
        self,
        path: str | Path,
        head_path: str | Path | None = None,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.path = Path(path)
        self.head_path = Path(head_path) if head_path else Path(str(self.path) + ".head")
        self._clock = clock

    # -- reading ---------------------------------------------------------------------------

    def _lines(self) -> list[str]:
        """Lines of the log. One trailing newline is dropped; blank lines elsewhere are kept."""
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8", newline="") as fh:
            parts = fh.read().split("\n")
        if parts and parts[-1] == "":
            parts.pop()
        return parts

    def entries(self) -> list[dict[str, Any]]:
        return [json.loads(ln) for ln in self._lines()]

    def read_head(self) -> dict[str, Any] | None:
        if not self.head_path.exists():
            return None
        try:
            return json.loads(self.head_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    # -- locking ---------------------------------------------------------------------------

    @contextmanager
    def _locked(self) -> Iterator[None]:
        """Exclusive lock across threads and processes (``<log>.lock``, never deleted)."""
        lock_path = Path(str(self.path) + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        tlock = _thread_lock(str(lock_path.resolve()))
        if not tlock.acquire(timeout=LOCK_TIMEOUT_S):
            raise AuditError("timed out waiting for the audit log lock")
        try:
            with lock_path.open("a+b") as fh:
                fd = fh.fileno()
                if sys.platform == "win32":
                    import msvcrt

                    deadline = time.monotonic() + LOCK_TIMEOUT_S
                    while True:
                        try:
                            fh.seek(0)
                            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                            break
                        except OSError:
                            if time.monotonic() > deadline:
                                raise AuditError(
                                    "timed out waiting for the audit log lock"
                                ) from None
                            time.sleep(0.01)
                    try:
                        yield
                    finally:
                        fh.seek(0)
                        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(fd, fcntl.LOCK_EX)
                    try:
                        yield
                    finally:
                        fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            tlock.release()

    # -- writing ---------------------------------------------------------------------------

    def append(self, type: str, data: dict[str, Any]) -> dict[str, Any]:
        with self._locked():
            return self._append_locked(type, data)

    def _append_locked(self, type: str, data: dict[str, Any]) -> dict[str, Any]:
        lines = self._lines()
        if any(ln == "" for ln in lines):
            raise AuditError("audit log contains a blank line; refusing to extend")
        if lines:
            try:
                last = json.loads(lines[-1])
                seq, prev = int(last["seq"]) + 1, str(last["hash"])
                last_prev = str(last["prev_hash"])
            except (ValueError, KeyError, TypeError) as exc:
                raise AuditError("last audit entry is unreadable; refusing to extend") from exc
            if seq != len(lines):
                raise AuditError("last audit entry seq does not match the line count")
        else:
            seq, prev, last_prev = 0, GENESIS_HASH, GENESIS_HASH
        self._reconcile_head(len(lines), prev, last_prev)

        body: dict[str, Any] = {
            "seq": seq,
            "ts": self._clock().astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "type": type,
            "data": data,
            "prev_hash": prev,
        }
        try:
            digest = entry_hash(body)
        except (TypeError, ValueError) as exc:
            raise AuditError(f"entry data is not canonical JSON: {exc}") from exc
        entry = {**body, "hash": digest}
        line = canonical_json(entry).decode("utf-8") + "\n"

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())
        self._write_head(digest, seq + 1)
        return entry

    def _reconcile_head(self, n: int, last_hash: str, last_prev: str) -> None:
        """Check the head sidecar against the log; repair the one crash state we can explain.

        A crash between writing the log line and the head leaves the head exactly one entry
        behind with the last entry linked to it: the head is repaired. Anything else (head
        ahead of the log, or not matching) means tampering or damage: refuse to write.
        """
        meta = self.read_head()
        if meta is None:
            head, count = GENESIS_HASH, 0
        else:
            head, count = meta.get("head"), meta.get("count")
        if count == n and head == (last_hash if n else GENESIS_HASH):
            return
        if n >= 1 and count == n - 1 and head == last_prev:
            self._write_head(last_hash, n)
            return
        raise AuditError("head metadata does not match the log; refusing to extend")

    def _write_head(self, head: str, count: int) -> None:
        tmp = self.head_path.with_name(self.head_path.name + ".tmp")
        tmp.write_text(
            json.dumps({"head": head, "count": count}, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(tmp, self.head_path)

    # -- typed helpers ---------------------------------------------------------------------

    def log_llm_call(self, call: LlmCall) -> dict[str, Any]:
        """Record an LLM call, including failed ones (I-06)."""
        return self.append("llm_call", call.model_dump(mode="json"))

    # -- verification ----------------------------------------------------------------------

    def verify(self, expected_head: str | None = None) -> VerifyReport:
        if self.path.parent.exists():
            with self._locked():
                return self._verify_locked(expected_head)
        return self._verify_locked(expected_head)

    def _verify_locked(self, expected_head: str | None) -> VerifyReport:
        errors: list[str] = []
        prev = GENESIS_HASH
        count = 0
        if not self.path.exists():
            return VerifyReport(ok=False, count=0, head=prev, errors=["audit log not found"])
        for i, line in enumerate(self._lines()):
            if line == "":
                errors.append(f"line {i + 1}: blank line")
                break
            try:
                entry = AuditEntry.model_validate_json(line)
            except ValidationError:
                errors.append(f"line {i + 1}: malformed entry")
                break
            if entry.seq != i:
                errors.append(f"line {i + 1}: seq {entry.seq} expected {i} (entry removed?)")
                break
            if entry.prev_hash != prev:
                errors.append(f"line {i + 1}: prev_hash does not link to the previous entry")
                break
            body = entry.model_dump(exclude={"hash"})
            try:
                recomputed = entry_hash(body)
            except (TypeError, ValueError):
                errors.append(f"line {i + 1}: data is not canonical JSON")
                break
            if recomputed != entry.hash:
                errors.append(f"line {i + 1}: hash mismatch (entry modified)")
                break
            prev = entry.hash
            count += 1

        if not errors:
            if expected_head is not None:
                if prev != expected_head:
                    errors.append(
                        "head hash differs from expected_head (tail truncated or changed)"
                    )
                elif count == 0:
                    errors.append("audit log has no entries")
            else:
                meta = self.read_head()
                if meta is None:
                    errors.append("head metadata missing or unreadable")
                elif meta.get("head") != prev or meta.get("count") != count:
                    errors.append("head metadata does not match the log (tail truncated?)")
        return VerifyReport(ok=not errors, count=count, head=prev, errors=errors)
