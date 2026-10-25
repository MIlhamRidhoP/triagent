"""Lifecycle transitions with audit logging (A-14, R-01, I-01).

Verdicts and verification results never move the lifecycle by themselves. Suppression needs a
human or an explicit rule with an id, and every transition writes one audit entry.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal, get_args

from pydantic import ValidationError

from triagent.audit import AuditLog
from triagent.models import DecisionKind, Finding, HumanDecision, Lifecycle

L = Lifecycle

ALLOWED: dict[Lifecycle, frozenset[Lifecycle]] = {
    L.RAW: frozenset({L.DEDUPED, L.SUPPRESSED}),
    L.DEDUPED: frozenset({L.TRIAGED, L.SUPPRESSED}),
    L.TRIAGED: frozenset({L.FIX_PROPOSED, L.SUPPRESSED}),
    L.FIX_PROPOSED: frozenset({L.FIX_VALIDATED, L.TRIAGED, L.SUPPRESSED}),
    L.FIX_VALIDATED: frozenset({L.SUPPRESSED}),
    L.SUPPRESSED: frozenset({L.DEDUPED}),
}

Actor = Literal["human", "rule", "model", "system"]


class TransitionError(Exception):
    """The transition is not allowed (invalid edge, or actor lacks the authority)."""


def transition(
    finding: Finding,
    target: Lifecycle,
    *,
    log: AuditLog,
    actor: Actor,
    reason: str,
    rule_id: str | None = None,
    now: datetime | None = None,
) -> Finding:
    """Return a new Finding in ``target`` and write one audit entry. Nothing is written on error."""
    try:
        # Re-validate the input: a tampered Finding must not be carried forward (I-01, I-02).
        Finding.model_validate(finding.model_dump())
    except ValidationError as exc:
        raise TransitionError("input finding violates its invariants") from exc
    if actor not in get_args(Actor):
        raise TransitionError(f"unknown actor: {actor!r}")
    if target not in ALLOWED[finding.lifecycle]:
        raise TransitionError(f"{finding.lifecycle.value} -> {target.value} is not allowed")
    if not reason.strip():
        raise TransitionError("a reason is required")

    update: dict[str, object] = {"lifecycle": target}
    if target is L.SUPPRESSED:
        if actor not in ("human", "rule"):
            raise TransitionError("only a human or an explicit rule may suppress (I-01)")
        if actor == "rule" and not rule_id:
            raise TransitionError("rule suppression requires a rule id (I-01)")
        update["human_decision"] = HumanDecision(
            decision=DecisionKind.SUPPRESSED,
            actor=actor,
            rule_id=rule_id,
            reason=reason,
            decided_at=now or datetime.now(UTC),
        )
    elif finding.lifecycle is L.SUPPRESSED:
        if actor != "human":
            raise TransitionError("only a human may lift a suppression")
        update["human_decision"] = None

    new = Finding.model_validate({**finding.model_dump(), **update})
    log.append(
        "status_change",
        {
            "finding_id": finding.id,
            "from": finding.lifecycle.value,
            "to": target.value,
            "actor": actor,
            "rule_id": rule_id,
            "reason": reason,
        },
    )
    return new
