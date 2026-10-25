"""Evaluation run in recorded mode: replay verdicts, cost and latency, then score (I-10).

A recording holds the run metadata and one call record per finding. Nothing here talks to a model
or to the network. Incomplete metadata is rejected because an unidentified model (pitfall P9) or a
missing call would make the numbers uninterpretable.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from triagent import __version__
from triagent.benchmark.groundtruth import (
    GroundTruth,
    GroundTruthError,
    load_ground_truth,
    sha256_file,
)
from triagent.eval.metrics import VERDICTS, EvalError, score
from triagent.models import Finding

REQUIRED_META = (
    "model_id",
    "model_snapshot",
    "api_route",
    "scanner",
    "scanner_version",
    "ruleset",
    "prompt_hash",
    "temperature",
    "context_limit_tokens",
    "corpus_date",
)
OPTIONAL_META = ("recorded_at", "cassette_id", "max_output_tokens", "top_p", "seed")
_HASH = re.compile(r"^[0-9a-f]{64}$")


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvalError(f"cannot read {path}: {exc}") from exc


def load_findings(path: Path) -> list[Finding]:
    doc = read_json(path)
    if not isinstance(doc, dict) or not isinstance(doc.get("findings"), list):
        raise EvalError(f"{path}: expected an object with a 'findings' list")
    try:
        return [Finding.model_validate(f) for f in doc["findings"]]
    except ValueError as exc:
        raise EvalError(f"{path}: invalid finding: {str(exc)[:200]}") from exc


def load_verdicts(path: Path) -> dict[str, str]:
    doc = read_json(path)
    v = doc.get("verdicts") if isinstance(doc, dict) else None
    if not isinstance(v, dict) or not all(isinstance(x, str) for x in v.values()):
        raise EvalError(f"{path}: expected {{'verdicts': {{finding_id: verdict}}}}")
    return v


def load_gt(path: Path) -> GroundTruth:
    try:
        return load_ground_truth(path)
    except GroundTruthError as exc:
        raise EvalError(f"ground truth: {exc}") from exc


def _fmt(v: float | None) -> str:
    return "n/a" if v is None else f"{v:.3f}"


def render_markdown(report: dict[str, Any]) -> str:
    meta = report["metadata"]
    lines = [
        "# Evaluation report",
        "",
        f"Model: {meta['model_id']} ({meta['model_snapshot']}), route {meta['api_route']}, "
        f"scanner {meta['scanner']} {meta['scanner_version']}, mode {meta['mode']}, "
        f"line tolerance {meta['line_tolerance']}.",
        f"Cost: {report['cost']['usd_total']} USD over {report['cost']['calls']} calls. "
        f"Latency: {report['latency']['ms_total']} ms total.",
        "",
        "## Metrics",
        "",
        "| CWE match | uncertain | tp | fp | tn | fn | precision | recall | f1 | FPR | TP retention |",  # noqa: E501
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    variants = report["results"]["variants"]
    for cwe_name, by_unc in variants.items():
        for unc_name, v in by_unc.items():
            lines.append(
                f"| {cwe_name} | {unc_name} | {v['tp']} | {v['fp']} | {v['tn']} | {v['fn']} | "
                f"{_fmt(v['precision'])} | {_fmt(v['recall'])} | {_fmt(v['f1'])} | "
                f"{_fmt(v['fpr'])} | {_fmt(v['tp_retention'])} |"
            )
    ref = variants["cwe_loose"]["uncertain_positive"]
    lines += ["", "## TP retention per category (loose, uncertain positive)", ""]
    lines += ["| category | tp items | detected | retained | retention |", "|---|---|---|---|---|"]
    for cat, c in ref["per_category"].items():
        lines.append(
            f"| {cat} | {c['tp_items']} | {c['detected']} | {c['retained']} | "
            f"{_fmt(c['tp_retention'])} |"
        )
    lines += ["", "## Per item (loose, uncertain positive)", ""]
    lines += ["| item | label | category | outcome | findings |", "|---|---|---|---|---|"]
    for it in ref["items"]:
        found = ", ".join(it["matched_findings"]) or "none"
        lines.append(
            f"| {it['id']} | {it['label']} | {it['category']} | {it['outcome']} | {found} |"
        )
    unl = ref["unlabeled_findings"]
    lines += ["", f"Unlabeled findings (outside the ground truth, not counted as FP): {len(unl)}"]
    return "\n".join(lines) + "\n"


def run_recorded(
    gt_path: Path,
    findings_path: Path,
    recording_path: Path,
    out_dir: Path,
    *,
    line_tolerance: int = 2,
    strip_prefixes: Sequence[str] = (),
) -> dict[str, Any]:
    gt = load_gt(gt_path)
    findings = load_findings(findings_path)
    rec = read_json(recording_path)
    if not isinstance(rec, dict) or not isinstance(rec.get("meta"), dict):
        raise EvalError(f"{recording_path}: expected an object with 'meta' and 'calls'")
    meta = rec["meta"]
    missing = [k for k in REQUIRED_META if meta.get(k) in (None, "")]
    if missing:
        raise EvalError(f"recording metadata incomplete, missing: {', '.join(missing)}")
    if not _HASH.match(str(meta["prompt_hash"])):
        raise EvalError("prompt_hash must be a SHA-256 hex digest")
    calls = rec.get("calls")
    if not isinstance(calls, list):
        raise EvalError(f"{recording_path}: 'calls' must be a list")
    verdicts: dict[str, str] = {}
    cost = 0.0
    latency = 0
    truncated = 0
    for c in calls:
        try:
            fid, verdict = c["finding_id"], c["verdict"]
            cost += float(c["cost_usd"])
            latency += int(c["latency_ms"])
        except (KeyError, TypeError, ValueError) as exc:
            raise EvalError(f"bad call record: {str(c)[:100]}") from exc
        if verdict not in VERDICTS:
            raise EvalError(f"unknown verdict {verdict!r} for {fid}")
        if fid in verdicts:
            raise EvalError(f"two calls recorded for {fid}")
        verdicts[fid] = verdict
        truncated += 1 if c.get("truncated") else 0
    missing_calls = [f.id for f in findings if f.duplicate_of is None and f.id not in verdicts]
    if missing_calls:
        raise EvalError(
            f"no recorded call for {len(missing_calls)} finding(s), first: {missing_calls[0]}"
        )
    results = score(
        gt, findings, verdicts, line_tolerance=line_tolerance, strip_prefixes=strip_prefixes
    )
    allowed = (*REQUIRED_META, *OPTIONAL_META)
    dropped = sorted(k for k in meta if k not in allowed)
    report = {
        "metadata": {
            **{k: meta[k] for k in allowed if k in meta},
            "dropped_meta_keys": dropped,
            "label_source": gt.label_source,
            "ground_truth_sha256": sha256_file(gt_path),
            "triagent_version": __version__,
            "mode": "recorded",
            "line_tolerance": line_tolerance,
            "context_truncated_calls": truncated,
        },
        "cost": {"usd_total": round(cost, 10), "calls": len(calls)},
        "latency": {
            "ms_total": latency,
            "ms_mean": (latency / len(calls)) if calls else 0.0,
        },
        "results": results,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, indent=2, sort_keys=True) + chr(10)
    with (out_dir / "report.json").open("w", encoding="utf-8", newline=chr(10)) as fh:
        fh.write(text)
    with (out_dir / "report.md").open("w", encoding="utf-8", newline=chr(10)) as fh:
        fh.write(render_markdown(report))
    return report
