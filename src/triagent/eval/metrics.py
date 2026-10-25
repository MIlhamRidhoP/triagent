"""Triage metrics against the benchmark ground truth (resolution R-06, invariant I-05).

v1 measures triage of scanner findings. Definitions (also in docs/EVAL-PITFALLS.md):

- One-to-one matching (review R-01): a finding is assigned to at most one item. Candidates are
  items in the same file whose line range is within ``line_tolerance`` lines of the finding and
  whose CWE matches (strict: shared id, loose: shared family). The winner has the smallest line
  distance (0 when the ranges overlap), then a strict CWE match before a family-only match, then
  the smallest item id. One finding is one prediction, so it is never counted for two items.
- Findings with ``duplicate_of`` are skipped (counted in ``duplicates_skipped``).
- A finding is predicted positive when its verdict is ``likely_tp``, or ``uncertain`` in the
  ``uncertain_positive`` variant. An item is positive when any finding assigned to it is positive.
- tp item: no assigned finding -> ``fn_missed``; positive -> ``tp``; all negative -> ``fn_lost``.
- fp-trap item: no assigned finding -> ``not_flagged`` (outside FP/TN); positive -> ``fp``;
  all negative -> ``tn``.
- precision = tp/(tp+fp), recall = tp/(tp+fn), f1 = 2tp/(2tp+fp+fn), fpr = fp/(fp+tn),
  tp_retention = tp/(tp+fn_lost). A ratio with an empty denominator is ``None``.
- Findings assigned to no item are ``unlabeled_findings``, never counted as FP.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from triagent.benchmark.groundtruth import GroundTruth, GtItem, Label
from triagent.models import Finding
from triagent.normalize.cwe import match as cwe_match

VERDICTS = ("likely_tp", "likely_fp", "uncertain")
CWE_MODES = {"cwe_strict": True, "cwe_loose": False}
UNCERTAIN_MODES = {
    "uncertain_positive": frozenset({"likely_tp", "uncertain"}),
    "uncertain_negative": frozenset({"likely_tp"}),
}


class EvalError(Exception):
    """Input to the evaluation is inconsistent or malformed."""


def _ratio(num: int, den: int) -> float | None:
    return None if den == 0 else num / den


def normalize_path(p: str, strip_prefixes: Sequence[str] = ()) -> str:
    """Forward slashes, no leading ``./``, and the first matching prefix removed."""
    p = p.replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    for prefix in strip_prefixes:
        pre = prefix.replace("\\", "/")
        while pre.startswith("./"):
            pre = pre[2:]
        if pre and p.startswith(pre):
            return p[len(pre) :].lstrip("/")
    return p


def _distance(f: Finding, item: GtItem) -> int:
    loc = f.location
    if loc.start_line > item.end_line:
        return loc.start_line - item.end_line
    if loc.end_line < item.start_line:
        return item.start_line - loc.end_line
    return 0


def _assign(
    items: Sequence[GtItem],
    findings: Sequence[tuple[Finding, str]],
    tolerance: int,
    strict: bool,
) -> dict[str, list[Finding]]:
    """Give every finding to its single best item. Returns item id -> assigned findings."""
    out: dict[str, list[Finding]] = {i.id: [] for i in items}
    for f, path in findings:
        best: tuple[int, int, str] | None = None
        for item in items:
            if path != item.file:
                continue
            dist = _distance(f, item)
            if dist > tolerance or not cwe_match(f.cwe, item.cwe, strict=strict):
                continue
            rank = 0 if cwe_match(f.cwe, item.cwe, strict=True) else 1
            key = (dist, rank, item.id)
            if best is None or key < best:
                best = key
        if best is not None:
            out[best[2]].append(f)
    return out


def _variant(
    gt: GroundTruth,
    findings: Sequence[tuple[Finding, str]],
    verdicts: Mapping[str, str],
    tolerance: int,
    strict: bool,
    positive: frozenset[str],
) -> dict[str, Any]:
    assigned = _assign(gt.items, findings, tolerance, strict)
    matched_ids = {f.id for fs in assigned.values() for f in fs}
    items_out: list[dict[str, Any]] = []
    counts = {"tp": 0, "fp": 0, "tn": 0, "fn_missed": 0, "fn_lost": 0, "not_flagged": 0}
    cats: dict[str, dict[str, int]] = {}
    for item in gt.items:
        hits = assigned[item.id]
        is_pos = any(verdicts[f.id] in positive for f in hits)
        if item.label is Label.TP:
            outcome = "fn_missed" if not hits else "tp" if is_pos else "fn_lost"
            c = cats.setdefault(item.category.value, {"tp_items": 0, "detected": 0, "retained": 0})
            c["tp_items"] += 1
            c["detected"] += 1 if hits else 0
            c["retained"] += 1 if outcome == "tp" else 0
        else:
            outcome = "not_flagged" if not hits else "fp" if is_pos else "tn"
        counts[outcome] += 1
        items_out.append(
            {
                "id": item.id,
                "label": item.label.value,
                "category": item.category.value,
                "matched_findings": sorted(f.id for f in hits),
                "outcome": outcome,
            }
        )
    tp, fp, tn = counts["tp"], counts["fp"], counts["tn"]
    fn = counts["fn_missed"] + counts["fn_lost"]
    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "fn_missed": counts["fn_missed"],
        "fn_lost": counts["fn_lost"],
        "not_flagged": counts["not_flagged"],
        "precision": _ratio(tp, tp + fp),
        "recall": _ratio(tp, tp + fn),
        "f1": _ratio(2 * tp, 2 * tp + fp + fn),
        "fpr": _ratio(fp, fp + tn),
        "tp_retention": _ratio(tp, tp + counts["fn_lost"]),
        "matched_findings_total": len(matched_ids),
        "per_category": {
            name: {**c, "tp_retention": _ratio(c["retained"], c["detected"])}
            for name, c in sorted(cats.items())
        },
        "items": items_out,
        "unlabeled_findings": sorted(f.id for f, _ in findings if f.id not in matched_ids),
    }


def score(
    gt: GroundTruth,
    findings: Sequence[Finding],
    verdicts: Mapping[str, str] | None,
    *,
    line_tolerance: int,
    strip_prefixes: Sequence[str] = (),
) -> dict[str, Any]:
    """Compute all four variants. ``verdicts=None`` is the scanner-only baseline (all positive)."""
    if line_tolerance < 0:
        raise EvalError("line_tolerance must be >= 0")
    ids = [f.id for f in findings]
    if len(set(ids)) != len(ids):
        raise EvalError("duplicate finding ids in the findings file")
    live = [f for f in findings if f.duplicate_of is None]
    skipped = len(findings) - len(live)
    if verdicts is None:
        resolved = {f.id: "likely_tp" for f in live}
    else:
        bad = sorted(v for v in verdicts.values() if v not in VERDICTS)
        if bad:
            raise EvalError(f"unknown verdict {bad[0]!r}")
        missing = [f.id for f in live if f.id not in verdicts]
        if missing:
            raise EvalError(f"no verdict for {len(missing)} finding(s), first: {missing[0]}")
        extra = sorted(set(verdicts) - set(ids))
        if extra:
            raise EvalError(f"verdict for unknown finding {extra[0]}")
        resolved = dict(verdicts)
    prepared = [(f, normalize_path(f.location.file, strip_prefixes)) for f in live]
    variants = {
        cwe_name: {
            unc_name: _variant(gt, prepared, resolved, line_tolerance, strict, positive)
            for unc_name, positive in UNCERTAIN_MODES.items()
        }
        for cwe_name, strict in CWE_MODES.items()
    }
    warnings: list[str] = []
    if live and variants["cwe_loose"]["uncertain_positive"]["matched_findings_total"] == 0:
        warnings.append(
            f"0 of {len(live)} findings matched any ground truth item; check file paths "
            "(use --strip-prefix), line tolerance and CWE ids"
        )
    return {
        "line_tolerance": line_tolerance,
        "duplicates_skipped": skipped,
        "warnings": warnings,
        "variants": variants,
    }
