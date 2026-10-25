"""Export JSON Schemas of the public data model to ``schemas/``."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from triagent.audit import AuditEntry
from triagent.benchmark.groundtruth import GroundTruth
from triagent.config import Config
from triagent.models import Finding, LlmCall

DRAFT = "https://json-schema.org/draft/2020-12/schema"

MODELS: dict[str, type[BaseModel]] = {
    "finding.schema.json": Finding,
    "llm-call.schema.json": LlmCall,
    "audit-entry.schema.json": AuditEntry,
    "config.schema.json": Config,
    "ground-truth.schema.json": GroundTruth,
}


def build_schema(model: type[BaseModel]) -> dict[str, Any]:
    schema = model.model_json_schema(mode="validation")
    return {"$schema": DRAFT, **schema}


def render(schema: dict[str, Any]) -> str:
    return json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def export_all(out_dir: str | Path) -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name, model in MODELS.items():
        target = out / name
        with target.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(render(build_schema(model)))
        written.append(target)
    return written


def check_all(schema_dir: str | Path) -> list[str]:
    """Return problems: schema files that are missing or differ from the models."""
    problems = []
    for name, model in MODELS.items():
        target = Path(schema_dir) / name
        if not target.exists():
            problems.append(f"missing: {name}")
        elif target.read_bytes().decode("utf-8") != render(build_schema(model)):
            problems.append(f"out of date: {name}")
    return problems
