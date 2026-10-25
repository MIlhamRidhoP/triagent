"""Data model: Finding, LlmCall and their parts (SPEC section 5, resolution R-01..R-03, R-07).

Invariants enforced here:
- I-01: a finding can only be ``suppressed`` with a recorded human decision or an explicit rule.
  Model verdicts are annotations and carry no lifecycle power.
- I-02: ``verification.result == exploitable`` needs sandbox evidence. There is no ``verified``
  lifecycle value; ``Finding.verified`` is derived and never accepted as input.
- I-06: ``LlmCall`` has every field the invariant requires, including failed calls.

JSON Schema cannot express the cross-field rules below; they are enforced by the pydantic
validators, and the schema only covers shape and enums.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, model_validator

CWE_PATTERN = r"^CWE-[1-9][0-9]*$"
SHA256_PATTERN = r"^[0-9a-f]{64}$"
CweId = Annotated[str, StringConstraints(pattern=CWE_PATTERN)]


class Strict(BaseModel):
    """Base class: unknown fields are errors, so nothing can smuggle in e.g. a ``verified`` flag.

    Models are immutable (frozen) so cross-field rules cannot be bypassed by assignment.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    @classmethod
    def model_construct(cls, *args: Any, **kwargs: Any) -> Any:
        """Disabled: it skips validation and would bypass I-01 and I-02."""
        raise TypeError(f"{cls.__name__}: unvalidated construction is not allowed")

    def model_copy(self, *, update: Mapping[str, Any] | None = None, deep: bool = False) -> Any:
        """Copy; any ``update`` is validated again so cross-field rules still hold."""
        if not update:
            return super().model_copy(deep=deep)
        return type(self).model_validate({**self.model_dump(), **update})


class Lifecycle(StrEnum):
    RAW = "raw"
    DEDUPED = "deduped"
    TRIAGED = "triaged"
    FIX_PROPOSED = "fix_proposed"
    FIX_VALIDATED = "fix_validated"
    SUPPRESSED = "suppressed"


class Verdict(StrEnum):
    LIKELY_TP = "likely_tp"
    LIKELY_FP = "likely_fp"
    UNCERTAIN = "uncertain"


class VerificationResult(StrEnum):
    EXPLOITABLE = "exploitable"
    NOT_REPRODUCED = "not_reproduced"
    NOT_ATTEMPTED = "not_attempted"


class DecisionKind(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPPRESSED = "suppressed"


class Location(Strict):
    file: str = Field(min_length=1)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)

    @model_validator(mode="after")
    def _ordered(self) -> Location:
        if self.end_line < self.start_line:
            raise ValueError("end_line must be >= start_line")
        return self


class TriageVerdict(Strict):
    """Annotation from one model. Telemetry lives in the LlmCall referenced by ``call_id``."""

    model_id: str = Field(min_length=1)
    verdict: Verdict
    reason: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    call_id: str = Field(min_length=1)


class Verification(Strict):
    result: VerificationResult = VerificationResult.NOT_ATTEMPTED
    evidence_path: str | None = Field(default=None, min_length=1)
    sandbox_run_id: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _evidence_rules(self) -> Verification:
        if self.result is VerificationResult.EXPLOITABLE and not (
            self.evidence_path and self.sandbox_run_id
        ):
            raise ValueError("exploitable requires evidence_path and sandbox_run_id (I-02)")
        if self.result is VerificationResult.NOT_ATTEMPTED and (
            self.evidence_path or self.sandbox_run_id
        ):
            raise ValueError("not_attempted must not carry evidence or a sandbox run")
        return self


class Fix(Strict):
    patch_path: str = Field(min_length=1)
    tests_passed: bool | None = None
    rescan_clean: bool | None = None
    new_findings: int | None = Field(default=None, ge=0)


class HumanDecision(Strict):
    decision: DecisionKind
    actor: Literal["human", "rule"] = "human"
    rule_id: str | None = Field(default=None, min_length=1)
    reason: str = Field(min_length=1)
    decided_at: AwareDatetime

    @model_validator(mode="after")
    def _rule_needs_id(self) -> HumanDecision:
        if self.actor == "rule" and not self.rule_id:
            raise ValueError("actor 'rule' requires rule_id")
        return self


class Finding(Strict):
    id: str = Field(min_length=1)
    source_tool: str = Field(min_length=1)
    rule_id: str = Field(min_length=1)
    cwe: list[CweId] = Field(default_factory=list)
    cwe_family: str | None = Field(default=None, min_length=1)
    owasp_category: str | None = Field(default=None, min_length=1)
    location: Location
    message: str
    severity_scanner: Literal["none", "note", "warning", "error"] | None = None
    lifecycle: Lifecycle = Lifecycle.RAW
    duplicate_of: str | None = Field(default=None, min_length=1)
    triage: list[TriageVerdict] = Field(default_factory=list)
    verification: Verification = Field(default_factory=Verification)
    fix: Fix | None = None
    human_decision: HumanDecision | None = None

    @model_validator(mode="after")
    def _consistency(self) -> Finding:
        if self.duplicate_of == self.id:
            raise ValueError("duplicate_of must not point to itself")

        suppressed = self.lifecycle is Lifecycle.SUPPRESSED
        decided = (
            self.human_decision is not None
            and self.human_decision.decision is DecisionKind.SUPPRESSED
        )
        if suppressed and not decided:
            raise ValueError("suppressed requires a human or rule decision (I-01)")
        if decided and not suppressed:
            raise ValueError("a suppress decision requires lifecycle 'suppressed'")

        if self.lifecycle in (Lifecycle.FIX_PROPOSED, Lifecycle.FIX_VALIDATED) and self.fix is None:
            raise ValueError(f"{self.lifecycle.value} requires a fix record")
        if self.lifecycle is Lifecycle.FIX_VALIDATED:
            f = self.fix
            if not (
                f and f.tests_passed is True and f.rescan_clean is True and f.new_findings == 0
            ):
                raise ValueError(
                    "fix_validated requires tests_passed, rescan_clean and new_findings == 0"
                )
        return self

    @property
    def verified(self) -> bool:
        """Derived from sandbox evidence only (I-02). Never an input, never model opinion."""
        return self.verification.result is VerificationResult.EXPLOITABLE


class LlmCall(Strict):
    """One LLM call, successful or not (I-06, R-03)."""

    call_id: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    called_at: AwareDatetime
    params: dict[str, Any]
    prompt_id: str = Field(min_length=1)
    prompt_hash: str = Field(pattern=SHA256_PATTERN)
    tokens_in: int = Field(ge=0)
    tokens_out: int = Field(ge=0)
    cost_usd: float = Field(ge=0.0)
    latency_ms: float = Field(ge=0.0)
    status: Literal["ok", "error", "timeout", "schema_invalid"]
    error: str | None = None

    @model_validator(mode="after")
    def _error_text(self) -> LlmCall:
        if self.status != "ok" and not self.error:
            raise ValueError("a failed call must record an error description")
        return self
