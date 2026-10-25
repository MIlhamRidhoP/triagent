from __future__ import annotations

import pytest
from pydantic import ValidationError

from conftest import llm_call_data, make_finding
from triagent.audit import AuditLog
from triagent.models import Finding, LlmCall


def test_finding_roundtrips_through_json():
    f = make_finding(cwe=["CWE-862", "CWE-863"], owasp_category="A01:2021")
    again = Finding.model_validate_json(f.model_dump_json())
    assert again == f
    assert again.cwe == ["CWE-862", "CWE-863"]


@pytest.mark.parametrize("bad", ["79", "CWE-", "CWE-0", "cwe-79", "CWE-7x"])
def test_cwe_ids_are_validated(bad):
    with pytest.raises(ValidationError):
        make_finding(cwe=[bad])


def test_multiple_cwe_are_kept():
    assert len(make_finding(cwe=["CWE-22", "CWE-23", "CWE-36"]).cwe) == 3


def test_location_line_order():
    with pytest.raises(ValidationError):
        make_finding(location={"file": "a.js", "start_line": 5, "end_line": 4})
    with pytest.raises(ValidationError):
        make_finding(location={"file": "a.js", "start_line": 0, "end_line": 1})


def test_verdict_confidence_range():
    v = {"model_id": "m", "verdict": "uncertain", "reason": "r", "call_id": "c"}
    for conf in (-0.1, 1.1):
        with pytest.raises(ValidationError):
            make_finding(triage=[{**v, "confidence": conf}])


def test_llm_call_requires_every_i06_field():
    LlmCall.model_validate(llm_call_data())
    for key in llm_call_data():
        if key == "error":
            continue
        data = llm_call_data()
        del data[key]
        with pytest.raises(ValidationError):
            LlmCall.model_validate(data)


def test_llm_call_prompt_hash_must_be_sha256():
    with pytest.raises(ValidationError):
        LlmCall.model_validate(llm_call_data(prompt_hash="abc"))


def test_failed_call_needs_error_text():
    with pytest.raises(ValidationError):
        LlmCall.model_validate(llm_call_data(status="timeout"))


def test_failed_call_is_logged_and_chain_stays_valid(tmp_path):
    log = AuditLog(tmp_path / "a.jsonl")
    log.log_llm_call(LlmCall.model_validate(llm_call_data()))
    failed = LlmCall.model_validate(
        llm_call_data(call_id="c-2", status="schema_invalid", error="bad json", tokens_out=0)
    )
    log.log_llm_call(failed)
    entries = log.entries()
    assert [e["data"]["status"] for e in entries] == ["ok", "schema_invalid"]
    assert log.verify().ok
