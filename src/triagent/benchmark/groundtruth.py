"""Ground truth of the benchmark application: model, loader and semantic validator.

The JSON Schema in ``schemas/ground-truth.schema.json`` is generated from these models and covers
shape and enums. Rules that need the files (line ranges, anchors, PoC scripts) live in
``validate_root``. Labels come from PoC runs, never from an LLM (chasing-shadows-2026, P2).
"""

from __future__ import annotations

import hashlib
from enum import StrEnum
from itertools import combinations
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import Field, StringConstraints, ValidationError, model_validator

from triagent.models import CweId, Strict
from triagent.normalize.cwe import families_of

ITEM_ID_PATTERN = r"^BM-[0-9]{3}$"
# Relative path made of plain segments, ends with .js, no "..", no hidden segments.
FILE_PATTERN = r"^(?:[A-Za-z0-9_][A-Za-z0-9_-]*/)*[A-Za-z0-9_][A-Za-z0-9_-]*\.js$"
POC_PATTERN = r"^poc/BM-[0-9]{3}\.js$"
DATE_PATTERN = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"
SHA256_PATTERN = r"^[0-9a-f]{64}$"
# Text that survives renaming, comment removal and quote changes: no quotes, no backslash.
ANCHOR_PATTERN = r"^[^'\"`\\]{3,80}$"
REFERENCE_TOLERANCE = 2  # evaluation line tolerance the item spacing is validated against
FRAMING_WINDOW = 8  # lines above the item in which framing_text must appear in the original source


class Category(StrEnum):
    XSS = "xss"
    SQLI = "sqli"
    PATH_TRAVERSAL = "path-traversal"
    COMMAND_INJECTION = "command-injection"
    SSRF = "ssrf"
    OPEN_REDIRECT = "open-redirect"
    HARDCODED_SECRET = "hardcoded-secret"
    AUTHZ = "authz"
    CODE_INJECTION = "code-injection"
    PROTOTYPE_POLLUTION = "prototype-pollution"
    MASS_ASSIGNMENT = "mass-assignment"


class Label(StrEnum):
    TP = "tp"
    FP_TRAP = "fp-trap"


class Framing(StrEnum):
    NONE = "none"
    SAFE_CLAIM = "safe_claim"  # a comment says the code is safe (it is not)
    ALARM_CLAIM = "alarm_claim"  # a comment says the code is dangerous (it is not)


class TrapKind(StrEnum):
    SANITIZATION = "sanitization"
    PARAMETERIZED = "parameterized"
    ALLOWLIST = "allowlist"
    AUTHZ_CHECK = "authz-check"
    PLACEHOLDER = "placeholder"
    SAFE_API = "safe-api"


class GtItem(Strict):
    id: Annotated[str, StringConstraints(pattern=ITEM_ID_PATTERN)]
    title: Annotated[str, StringConstraints(min_length=3)]
    cwe: Annotated[list[CweId], Field(min_length=1)]
    category: Category
    label: Label
    file: Annotated[str, StringConstraints(pattern=FILE_PATTERN)]
    start_line: Annotated[int, Field(ge=1)]
    end_line: Annotated[int, Field(ge=1)]
    anchor: Annotated[str, StringConstraints(pattern=ANCHOR_PATTERN)]
    poc: Annotated[str, StringConstraints(pattern=POC_PATTERN)]
    comment_framing: Framing = Framing.NONE
    framing_text: str | None = None
    trap_kind: TrapKind | None = None
    notes: Annotated[str, StringConstraints(min_length=1)]

    @model_validator(mode="after")
    def _check(self) -> GtItem:
        if self.end_line < self.start_line:
            raise ValueError(f"{self.id}: end_line before start_line")
        if self.poc != f"poc/{self.id}.js":
            raise ValueError(f"{self.id}: poc must be poc/{self.id}.js")
        if self.label is Label.TP and self.trap_kind is not None:
            raise ValueError(f"{self.id}: a tp item has no trap_kind")
        if self.label is Label.FP_TRAP and self.trap_kind is None:
            raise ValueError(f"{self.id}: an fp-trap item needs trap_kind")
        if self.comment_framing is Framing.NONE and self.framing_text is not None:
            raise ValueError(f"{self.id}: framing_text without comment_framing")
        return self


class Variant(Strict):
    """Provenance of a mutated copy of the benchmark."""

    base_sha256: Annotated[str, StringConstraints(pattern=SHA256_PATTERN)]
    seed: int
    ops: list[Literal["rename", "strip-comments", "style"]]


class GroundTruth(Strict):
    schema_version: Literal[1]
    app: Annotated[str, StringConstraints(min_length=1)]
    corpus_date: Annotated[str, StringConstraints(pattern=DATE_PATTERN)]
    label_source: Literal["poc"]
    labeled_by: Annotated[str, StringConstraints(min_length=1)]
    variant: Variant | None = None
    items: Annotated[list[GtItem], Field(min_length=1)]

    @model_validator(mode="after")
    def _check(self) -> GroundTruth:
        ids = [i.id for i in self.items]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate item ids")
        stripped = self.variant is not None and "strip-comments" in self.variant.ops
        for item in self.items:
            if (
                item.comment_framing is not Framing.NONE
                and item.framing_text is None
                and not stripped
            ):
                raise ValueError(f"{item.id}: comment_framing needs framing_text")
        return self


class GroundTruthError(Exception):
    """The ground truth file cannot be read or does not match the schema."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_ground_truth(path: str | Path) -> GroundTruth:
    """Load and shape-check a ground truth file. File level checks are in ``validate_root``."""
    p = Path(path)
    try:
        raw: Any = yaml.safe_load(p.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise GroundTruthError(f"cannot read {p}: {exc}") from exc
    try:
        return GroundTruth.model_validate(raw)
    except ValidationError as exc:
        parts = [f"{'.'.join(str(x) for x in e['loc'])}: {e['msg']}" for e in exc.errors()]
        raise GroundTruthError("; ".join(parts)) from exc


def validate_root(root: str | Path, gt_path: str | Path | None = None) -> list[str]:
    """Check a benchmark root (``app/``, ``poc/``, ``ground-truth.yaml``). Returns problem lines.

    Each item-level problem starts with the item id so a wrong line shift is easy to count.
    """
    base = Path(root)
    gt_file = Path(gt_path) if gt_path else base / "ground-truth.yaml"
    try:
        gt = load_ground_truth(gt_file)
    except GroundTruthError as exc:
        return [f"GT: {exc}"]
    problems: list[str] = []
    stripped = gt.variant is not None and "strip-comments" in gt.variant.ops
    cache: dict[str, list[str] | None] = {}

    def source_lines(rel: str) -> list[str] | None:
        if rel not in cache:
            target = base / "app" / rel
            try:
                cache[rel] = target.read_text(encoding="utf-8").splitlines()
            except OSError:
                cache[rel] = None
        return cache[rel]

    for item in gt.items:
        lines = source_lines(item.file)
        if lines is None:
            problems.append(f"{item.id}: source file app/{item.file} is missing")
        elif item.end_line > len(lines):
            problems.append(
                f"{item.id}: lines {item.start_line}-{item.end_line} are past the end of "
                f"app/{item.file} ({len(lines)} lines)"
            )
        else:
            text = "\n".join(lines[item.start_line - 1 : item.end_line])
            if item.anchor not in text:
                problems.append(
                    f"{item.id}: anchor {item.anchor!r} not found in "
                    f"app/{item.file} lines {item.start_line}-{item.end_line}"
                )
            if item.framing_text is not None and not stripped:
                lo = max(0, item.start_line - 1 - FRAMING_WINDOW)
                window = "\n".join(lines[lo : item.end_line])
                if item.framing_text not in window:
                    problems.append(f"{item.id}: framing_text not found near the item")
        if not (base / item.poc).is_file():
            problems.append(f"{item.id}: PoC script {item.poc} is missing")
    # R-01: two items of the same CWE family close together would compete for one finding.
    min_gap = 2 * REFERENCE_TOLERANCE + 1
    for a, b in combinations(gt.items, 2):
        if a.file != b.file or not (families_of(a.cwe) & families_of(b.cwe)):
            continue
        gap = max(b.start_line - a.end_line, a.start_line - b.end_line)
        if gap <= min_gap:
            problems.append(
                f"{b.id}: too close to {a.id} in app/{a.file} (gap {gap} <= {min_gap}) "
                "with the same CWE family"
            )
    return problems
