"""Duplicate marking (R-02, I-01).

A duplicate is kept in the output with ``duplicate_of`` pointing at a canonical finding. Output
has the same length and order as the input. Every finding moves raw -> deduped through
``transition`` so the audit log gets one entry each.

Two findings are duplicates when all of these hold:
- same file (findings without a known location are never merged);
- line ranges overlap once widened by ``line_window`` lines, except that two hits of the *same
  tool and rule* must overlap exactly (adjacent hits of one rule are distinct occurrences);
- they share a CWE family (loose match), or, when either has no CWE, they are the same tool and
  rule.

The canonical finding is picked per cluster in a fixed order (higher scanner severity, earlier
line, rule id, id), and each duplicate is compared with canonical findings only, so there are no
chains and the result does not depend on input order.
"""

from __future__ import annotations

from collections.abc import Sequence

from triagent.audit import AuditLog
from triagent.lifecycle import transition
from triagent.models import Finding, Lifecycle
from triagent.normalize.cwe import families_of, family_of

DEFAULT_LINE_WINDOW = 2
UNKNOWN_FILE = "<unknown>"
_SEVERITY = {"error": 3, "warning": 2, "note": 1, "none": 0, None: -1}


def enrich_family(finding: Finding) -> Finding:
    """Set ``cwe_family`` from the first CWE when it is missing."""
    if finding.cwe_family or not finding.cwe:
        return finding
    return finding.model_copy(update={"cwe_family": family_of(finding.cwe[0])})


def _priority(f: Finding) -> tuple[int, int, str, str]:
    return (-_SEVERITY[f.severity_scanner], f.location.start_line, f.rule_id, f.id)


def _is_duplicate(a: Finding, b: Finding, window: int) -> bool:
    if a.location.file != b.location.file or a.location.file == UNKNOWN_FILE:
        return False
    same_rule = a.source_tool == b.source_tool and a.rule_id == b.rule_id
    w = 0 if same_rule else window
    la, lb = a.location, b.location
    if not (la.start_line <= lb.end_line + w and lb.start_line <= la.end_line + w):
        return False
    if a.cwe and b.cwe:
        return bool(families_of(a.cwe) & families_of(b.cwe))
    return same_rule


def dedup(
    findings: Sequence[Finding], *, log: AuditLog, line_window: int = DEFAULT_LINE_WINDOW
) -> list[Finding]:
    if line_window < 0:
        raise ValueError("line_window must be >= 0")
    if any(f.lifecycle is not Lifecycle.RAW for f in findings):
        raise ValueError("dedup expects raw findings")
    if len({f.id for f in findings}) != len(findings):
        raise ValueError("finding ids must be unique")

    canonical: list[Finding] = []
    parent: dict[str, str] = {}
    for f in sorted(findings, key=_priority):
        hit = next((c for c in canonical if _is_duplicate(c, f, line_window)), None)
        if hit is None:
            canonical.append(f)
        else:
            parent[f.id] = hit.id

    out: list[Finding] = []
    for f in findings:
        pid = parent.get(f.id)
        marked = f.model_copy(update={"duplicate_of": pid}) if pid else f
        reason = f"deduplicated: duplicate of {pid}" if pid else "deduplicated: canonical"
        out.append(transition(marked, Lifecycle.DEDUPED, log=log, actor="system", reason=reason))
    return out
