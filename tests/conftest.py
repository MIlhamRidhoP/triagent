"""Shared fixtures. Tests are offline (I-10): sockets are blocked for every test."""

from __future__ import annotations

import socket
from datetime import UTC, datetime
from typing import Any

import pytest

from triagent.audit import AuditLog
from triagent.models import Finding


@pytest.fixture(autouse=True)
def _offline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRIAGENT_OFFLINE", "1")

    def blocked(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("network access is blocked in tests (I-10)")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


def make_finding(**overrides: Any) -> Finding:
    data: dict[str, Any] = {
        "id": "f-001",
        "source_tool": "semgrep",
        "rule_id": "javascript.express.security.xss",
        "cwe": ["CWE-79"],
        "location": {"file": "src/app.js", "start_line": 10, "end_line": 12},
        "message": "possible XSS",
        "severity_scanner": "warning",
    }
    data.update(overrides)
    return Finding.model_validate(data)


def llm_call_data(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "call_id": "c-1",
        "model_id": "model-x",
        "called_at": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
        "params": {"temperature": 0, "max_tokens": 512},
        "prompt_id": "triage-v1",
        "prompt_hash": "a" * 64,
        "tokens_in": 100,
        "tokens_out": 20,
        "cost_usd": 0.002,
        "latency_ms": 840.5,
        "status": "ok",
    }
    data.update(overrides)
    return data


@pytest.fixture
def log(tmp_path):
    return AuditLog(tmp_path / "audit.jsonl")
