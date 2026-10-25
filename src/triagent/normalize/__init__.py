"""Normalization: CWE family enrichment and duplicate marking. Findings are never dropped."""

from __future__ import annotations

from collections.abc import Sequence

from triagent.audit import AuditLog
from triagent.models import Finding
from triagent.normalize.dedup import DEFAULT_LINE_WINDOW, dedup, enrich_family

__all__ = ["DEFAULT_LINE_WINDOW", "dedup", "enrich_family", "normalize_findings"]


def normalize_findings(
    findings: Sequence[Finding], *, log: AuditLog, line_window: int = DEFAULT_LINE_WINDOW
) -> list[Finding]:
    """Fill ``cwe_family``, then mark duplicates. Same length and order as the input (I-01)."""
    return dedup([enrich_family(f) for f in findings], log=log, line_window=line_window)
