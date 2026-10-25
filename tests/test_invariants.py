"""I-01 (never drop or auto-suppress) and I-02 (evidence decides) enforced in the model."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from conftest import make_finding
from triagent.lifecycle import ALLOWED, TransitionError, transition
from triagent.models import Lifecycle, Verdict, VerificationResult

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _verdict(v: str) -> dict:
    return {
        "model_id": "m",
        "verdict": v,
        "reason": "because",
        "confidence": 0.9,
        "call_id": "c-1",
    }


# ---- I-01 -----------------------------------------------------------------------------------


def test_i01_suppressed_without_decision_is_rejected():
    with pytest.raises(ValidationError):
        make_finding(lifecycle="suppressed")


def test_i01_suppress_decision_requires_suppressed_lifecycle():
    decision = {"decision": "suppressed", "reason": "r", "decided_at": NOW.isoformat()}
    with pytest.raises(ValidationError):
        make_finding(lifecycle="triaged", human_decision=decision)


def test_i01_rule_suppression_requires_rule_id():
    decision = {"decision": "suppressed", "actor": "rule", "reason": "r", "decided_at": NOW}
    with pytest.raises(ValidationError):
        make_finding(lifecycle="suppressed", human_decision=decision)


def test_i01_likely_fp_verdict_keeps_the_finding_unsuppressed(log):
    f = make_finding(lifecycle="deduped", triage=[_verdict("likely_fp")])
    f = transition(f, Lifecycle.TRIAGED, log=log, actor="model", reason="triaged")
    assert f.lifecycle is Lifecycle.TRIAGED
    assert f.triage[0].verdict is Verdict.LIKELY_FP


@pytest.mark.parametrize("actor", ["model", "system"])
def test_i01_model_or_system_cannot_suppress(log, actor):
    f = make_finding(lifecycle="triaged")
    with pytest.raises(TransitionError):
        transition(f, Lifecycle.SUPPRESSED, log=log, actor=actor, reason="looks fake")
    assert log.entries() == []


def test_i01_rule_without_id_cannot_suppress(log):
    f = make_finding(lifecycle="triaged")
    with pytest.raises(TransitionError):
        transition(f, Lifecycle.SUPPRESSED, log=log, actor="rule", reason="r")
    assert log.entries() == []


def test_i01_human_suppression_is_recorded_in_audit_log(log):
    f = make_finding(lifecycle="triaged")
    out = transition(
        f, Lifecycle.SUPPRESSED, log=log, actor="human", reason="accepted risk", now=NOW
    )
    assert out.lifecycle is Lifecycle.SUPPRESSED
    assert out.human_decision is not None and out.human_decision.actor == "human"
    (entry,) = log.entries()
    assert entry["type"] == "status_change"
    assert entry["data"]["to"] == "suppressed" and entry["data"]["actor"] == "human"


def test_i01_rule_suppression_is_recorded_with_rule_id(log):
    f = make_finding(lifecycle="deduped")
    out = transition(
        f, Lifecycle.SUPPRESSED, log=log, actor="rule", rule_id="ignore-tests", reason="test dir"
    )
    assert out.human_decision is not None and out.human_decision.rule_id == "ignore-tests"
    assert log.entries()[0]["data"]["rule_id"] == "ignore-tests"


def test_i01_only_human_lifts_suppression(log):
    f = transition(make_finding(), Lifecycle.SUPPRESSED, log=log, actor="human", reason="r")
    with pytest.raises(TransitionError):
        transition(f, Lifecycle.DEDUPED, log=log, actor="model", reason="r")
    lifted = transition(f, Lifecycle.DEDUPED, log=log, actor="human", reason="reopen")
    assert lifted.lifecycle is Lifecycle.DEDUPED and lifted.human_decision is None


def test_i01_no_lifecycle_value_means_deleted():
    assert {m.value for m in Lifecycle} == {
        "raw",
        "deduped",
        "triaged",
        "fix_proposed",
        "fix_validated",
        "suppressed",
    }


def test_i01_duplicate_is_kept_with_pointer_not_dropped():
    dup = make_finding(id="f-002", duplicate_of="f-001", lifecycle="deduped")
    assert dup.duplicate_of == "f-001"
    with pytest.raises(ValidationError):
        make_finding(duplicate_of="f-001")  # points to itself


def test_i01_transition_table_has_no_automatic_edge_into_suppressed_for_models():
    # every state may reach suppressed (humans/rules), the authority check lives in transition()
    for state, targets in ALLOWED.items():
        if state is not Lifecycle.SUPPRESSED:
            assert Lifecycle.SUPPRESSED in targets


def test_i01_invalid_transition_is_rejected_and_not_logged(log):
    with pytest.raises(TransitionError):
        transition(make_finding(), Lifecycle.FIX_VALIDATED, log=log, actor="system", reason="r")
    assert log.entries() == []


# ---- I-02 -----------------------------------------------------------------------------------


def test_i02_exploitable_requires_evidence_and_sandbox_run():
    for v in ({}, {"evidence_path": "e.json"}, {"sandbox_run_id": "run-1"}):
        with pytest.raises(ValidationError):
            make_finding(verification={"result": "exploitable", **v})


def test_i02_exploitable_with_evidence_is_verified():
    f = make_finding(
        verification={"result": "exploitable", "evidence_path": "e.json", "sandbox_run_id": "r1"}
    )
    assert f.verified is True


def test_i02_model_opinion_cannot_verify():
    assert make_finding(triage=[_verdict("likely_tp")]).verified is False
    with pytest.raises(ValidationError):
        make_finding(verified=True)
    with pytest.raises(ValidationError):
        make_finding(lifecycle="verified")
    with pytest.raises(ValidationError):
        make_finding(triage=[{**_verdict("likely_tp"), "verified": True}])


def test_i02_not_reproduced_is_not_verified_and_keeps_lifecycle(log):
    f = make_finding(
        lifecycle="triaged",
        verification={
            "result": "not_reproduced",
            "evidence_path": "e.json",
            "sandbox_run_id": "r1",
        },
    )
    assert f.verified is False
    assert f.verification.result is VerificationResult.NOT_REPRODUCED
    assert f.lifecycle is Lifecycle.TRIAGED


def test_i02_not_attempted_cannot_carry_evidence():
    with pytest.raises(ValidationError):
        make_finding(verification={"result": "not_attempted", "evidence_path": "e.json"})


def test_i02_fix_can_follow_triage_without_verification(log):
    f = make_finding(lifecycle="triaged", fix={"patch_path": "p.diff"})
    out = transition(f, Lifecycle.FIX_PROPOSED, log=log, actor="system", reason="patch")
    assert out.lifecycle is Lifecycle.FIX_PROPOSED and out.verified is False


def test_fix_validated_requires_green_checks():
    base = {"patch_path": "p.diff", "tests_passed": True, "rescan_clean": True, "new_findings": 0}
    assert make_finding(lifecycle="fix_validated", fix=base).lifecycle is Lifecycle.FIX_VALIDATED
    for broken in ({"tests_passed": False}, {"rescan_clean": None}, {"new_findings": 1}):
        with pytest.raises(ValidationError):
            make_finding(lifecycle="fix_validated", fix={**base, **broken})


# ---- bypass attempts (R-01, R-05): immutability, construct, copy, tampering ------------------

_DECISION = {"decision": "suppressed", "reason": "r", "decided_at": NOW.isoformat()}


def test_assigning_lifecycle_is_rejected():
    f = make_finding()
    with pytest.raises(ValidationError):
        f.lifecycle = Lifecycle.SUPPRESSED
    assert f.lifecycle is Lifecycle.RAW


def test_assigning_human_decision_is_rejected():
    f = make_finding()
    with pytest.raises(ValidationError):
        f.human_decision = None
    with pytest.raises(ValidationError):
        f.human_decision = make_finding(
            lifecycle="suppressed", human_decision=_DECISION
        ).human_decision


def test_assigning_verification_result_is_rejected():
    f = make_finding()
    with pytest.raises(ValidationError):
        f.verification.result = VerificationResult.EXPLOITABLE
    assert f.verified is False


def test_assigning_fix_flags_is_rejected():
    f = make_finding(
        lifecycle="fix_proposed",
        fix={"patch_path": "p.diff"},
    )
    with pytest.raises(ValidationError):
        f.fix.tests_passed = True


def test_model_construct_is_disabled_on_every_model():
    from triagent.models import Finding, Fix, HumanDecision, LlmCall, Verification

    for cls in (Finding, Verification, Fix, HumanDecision, LlmCall):
        with pytest.raises(TypeError):
            cls.model_construct()
    with pytest.raises(TypeError):
        Finding.model_construct(id="b", lifecycle=Lifecycle.SUPPRESSED)


def test_model_copy_update_is_revalidated():
    f = make_finding()
    with pytest.raises(ValidationError):
        f.model_copy(update={"lifecycle": "suppressed"})
    with pytest.raises(ValidationError):
        f.model_copy(update={"verification": {"result": "exploitable"}})


def test_model_copy_update_with_valid_values_works():
    f = make_finding()
    g = f.model_copy(update={"message": "changed"})
    assert g.message == "changed" and f.message == "possible XSS"
    assert f.model_copy().message == f.message


def test_transition_rejects_finding_tampered_via_setattr(log):
    f = make_finding(lifecycle="triaged")
    object.__setattr__(f, "lifecycle", Lifecycle.SUPPRESSED)  # simulated tampering
    with pytest.raises(TransitionError):
        transition(f, Lifecycle.DEDUPED, log=log, actor="human", reason="lift")
    assert log.entries() == []


def test_transition_rejects_tampered_verification(log):
    f = make_finding(lifecycle="triaged")
    object.__setattr__(f.verification, "result", VerificationResult.EXPLOITABLE)
    with pytest.raises(TransitionError):
        transition(f, Lifecycle.FIX_PROPOSED, log=log, actor="system", reason="x")
    assert log.entries() == []


def test_unknown_actor_is_rejected_without_audit_entry(log):
    f = make_finding(lifecycle="triaged")
    with pytest.raises(TransitionError):
        transition(f, Lifecycle.SUPPRESSED, log=log, actor="admin", reason="x")  # type: ignore[arg-type]
    with pytest.raises(TransitionError):
        transition(f, Lifecycle.FIX_PROPOSED, log=log, actor="admin", reason="x")  # type: ignore[arg-type]
    assert log.entries() == []
