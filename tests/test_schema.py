"""Exported JSON Schemas are valid, current, and agree with the pydantic models."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from conftest import llm_call_data, make_finding
from triagent.schema_export import MODELS, build_schema, check_all, export_all

SCHEMAS = Path(__file__).resolve().parent.parent / "schemas"


@pytest.mark.parametrize("name", list(MODELS))
def test_committed_schema_is_valid_draft_2020_12(name):
    schema = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)


def test_committed_schemas_match_models():
    assert check_all(SCHEMAS) == []


def test_export_is_deterministic(tmp_path):
    export_all(tmp_path / "a")
    export_all(tmp_path / "b")
    for name in MODELS:
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()


def test_check_detects_drift(tmp_path):
    export_all(tmp_path)
    p = tmp_path / "finding.schema.json"
    p.write_text(p.read_text(encoding="utf-8").replace("fix_validated", "fix_ok"), encoding="utf-8")
    assert check_all(tmp_path) == ["out of date: finding.schema.json"]
    (tmp_path / "config.schema.json").unlink()
    assert "missing: config.schema.json" in check_all(tmp_path)


def test_model_output_validates_against_schema():
    v = Draft202012Validator(build_schema(MODELS["finding.schema.json"]))
    f = make_finding(
        cwe=["CWE-862", "CWE-863"],
        triage=[
            {
                "model_id": "m",
                "verdict": "likely_fp",
                "reason": "r",
                "confidence": 0.5,
                "call_id": "c",
            }
        ],
        verification={"result": "exploitable", "evidence_path": "e", "sandbox_run_id": "r"},
    )
    assert list(v.iter_errors(f.model_dump(mode="json"))) == []


def test_schema_rejects_what_model_rejects():
    v = Draft202012Validator(build_schema(MODELS["finding.schema.json"]))
    good = make_finding().model_dump(mode="json")
    assert not list(v.iter_errors(good))
    for patch in (
        {"verified": True},
        {"lifecycle": "verified"},
        {"cwe": ["79"]},
        {"severity_scanner": "critical"},
    ):
        assert list(v.iter_errors({**good, **patch})), patch


def test_llm_call_schema_requires_i06_fields():
    schema = build_schema(MODELS["llm-call.schema.json"])
    v = Draft202012Validator(schema)
    data = llm_call_data()
    assert not list(v.iter_errors(data))
    for key in data:
        assert list(v.iter_errors({k: x for k, x in data.items() if k != key})), key
    assert "error" not in schema["required"]
