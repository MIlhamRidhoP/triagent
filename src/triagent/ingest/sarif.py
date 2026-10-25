"""SARIF 2.1.0 to ``Finding`` (R-02, R-07).

The SARIF document is untrusted data. Nothing in it is executed, followed or used as an
instruction; text fields are only stored. The parser tolerates missing optional fields and
malformed results: every result that is a JSON object becomes a Finding (a result with no usable
location gets the placeholder file ``<unknown>`` and a warning), and anything else is listed in
``skipped``. Only a document that is not SARIF 2.1.x at all raises ``SarifError``.

Finding ids are deterministic (R-02): a hash of tool, rule id, file, a content key and an
occurrence counter. The content key is a real ``partialFingerprints`` value when present, else
the whitespace-normalised snippet, else the start line. The SARIF ``fingerprints`` map is ignored
on purpose: Semgrep OSS fills it with the placeholder text "requires login".
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from triagent.models import Finding

UNKNOWN_FILE = "<unknown>"
UNKNOWN_RULE = "unknown"
_LEVELS = {"none", "note", "warning", "error"}
_CWE_TAG = re.compile(r"^\s*(?:external/cwe/)?cwe[-_ ]?0*([1-9][0-9]*)\b", re.IGNORECASE)
_PCT = re.compile(r"(?:%[0-9A-Fa-f]{2})+")


class SarifError(Exception):
    """The input is not a usable SARIF 2.1.x document."""


@dataclass
class ParseResult:
    findings: list[Finding] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skipped: list[dict[str, Any]] = field(default_factory=list)
    tool_versions: list[str] = field(default_factory=list)


def _dict(v: Any) -> dict[str, Any]:
    return v if isinstance(v, dict) else {}


def _list(v: Any) -> list[Any]:
    return v if isinstance(v, list) else []


def _str(v: Any) -> str | None:
    return v if isinstance(v, str) and v.strip() else None


def _int(v: Any) -> int | None:
    return v if isinstance(v, int) and not isinstance(v, bool) and v >= 1 else None


def _decode_pct(s: str) -> str:
    return _PCT.sub(
        lambda m: bytes.fromhex(m.group(0).replace("%", "")).decode("utf-8", errors="replace"), s
    )


def normalize_uri(uri: str, strip_prefixes: Sequence[str] = ()) -> str:
    """Turn an artifact URI into a path with forward slashes, minus any configured prefix."""
    path = uri.strip()
    if path.lower().startswith("file://"):
        path = path[7:]
        if re.match(r"^/[A-Za-z]:", path):
            path = path[1:]
    path = _decode_pct(path).replace("\\", "/")
    for prefix in strip_prefixes:
        p = prefix.replace("\\", "/").rstrip("/")
        if p and (path == p or path.startswith(p + "/")):
            path = path[len(p) :].lstrip("/")
            break
    while path.startswith("./"):
        path = path[2:]
    return path or UNKNOWN_FILE


def extract_cwes(tags: Sequence[Any]) -> list[str]:
    """CWE ids from tags such as ``"CWE-79: Improper ..."``. Order kept, duplicates dropped."""
    out: list[str] = []
    for t in tags:
        if not isinstance(t, str):
            continue
        m = _CWE_TAG.match(t)
        if m:
            cwe = f"CWE-{int(m.group(1))}"
            if cwe not in out:
                out.append(cwe)
    return out


def extract_owasp(tags: Sequence[Any]) -> str | None:
    """The OWASP tag to keep: the 2021 edition if present, else the first one."""
    owasp = [
        t.strip() for t in tags if isinstance(t, str) and t.strip().upper().startswith("OWASP")
    ]
    for t in owasp:
        if ":2021" in t:
            return t
    return owasp[0] if owasp else None


def _tool_name(driver: dict[str, Any]) -> str:
    name = (_str(driver.get("name")) or "unknown").lower()
    if name.startswith("semgrep"):
        return "semgrep"
    slug = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    return slug or "unknown"


def _content_key(result: dict[str, Any], region: dict[str, Any], start: int) -> str:
    pf = _dict(result.get("partialFingerprints"))
    vals = [f"{k}={v}" for k, v in sorted(pf.items()) if isinstance(v, str) and v.strip()]
    if vals:
        return "fp:" + ";".join(vals)
    text = _str(_dict(region.get("snippet")).get("text"))
    if text:
        return "snip:" + " ".join(text.split())
    return f"line:{start}"


def _message(result: dict[str, Any], rule: dict[str, Any]) -> str:
    msg = result.get("message")
    if isinstance(msg, str):
        return msg
    msg = _dict(msg)
    for src in (
        msg.get("text"),
        msg.get("markdown"),
        _dict(rule.get("fullDescription")).get("text"),
        _dict(rule.get("shortDescription")).get("text"),
    ):
        if isinstance(src, str) and src:
            return src
    return ""


def _make_id(tool: str, rule_id: str, file: str, key: str, occurrence: int) -> str:
    payload = json.dumps([tool, rule_id, file, key, occurrence], ensure_ascii=True)
    return "f-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _check_document(doc: Any) -> list[Any]:
    if not isinstance(doc, dict):
        raise SarifError("SARIF root must be a JSON object")
    version = doc.get("version")
    if not isinstance(version, str) or not version.startswith("2.1"):
        raise SarifError(f"unsupported SARIF version: {version!r} (need 2.1.x)")
    runs = doc.get("runs")
    if not isinstance(runs, list):
        raise SarifError("SARIF 'runs' must be a list")
    return runs


def parse_sarif(
    source: dict[str, Any] | str | bytes | Path, *, strip_prefixes: Sequence[str] = ()
) -> ParseResult:
    """Parse a SARIF 2.1.x document (object, JSON text, bytes or file path)."""
    if isinstance(source, Path):
        try:
            source = source.read_bytes()
        except OSError as exc:
            raise SarifError(f"cannot read {source}: {exc}") from exc
    if isinstance(source, bytes | str):
        try:
            doc = json.loads(source)
        except (ValueError, RecursionError) as exc:  # JSONDecodeError and bad UTF-8 are ValueError
            raise SarifError(f"not valid JSON: {exc}") from exc
    else:
        doc = source
    runs = _check_document(doc)

    res = ParseResult()
    drafts: list[dict[str, Any]] = []
    for run_i, run in enumerate(runs):
        if not isinstance(run, dict):
            res.warnings.append(f"runs[{run_i}] is not an object; skipped")
            res.skipped.append({"run": run_i, "result": None, "reason": "run is not an object"})
            continue
        driver = _dict(_dict(run.get("tool")).get("driver"))
        tool = _tool_name(driver)
        version = _str(driver.get("semanticVersion")) or _str(driver.get("version"))
        if version:
            res.tool_versions.append(f"{tool} {version}")
        rules = [r if isinstance(r, dict) else {} for r in _list(driver.get("rules"))]
        rules_by_id = {r["id"]: r for r in rules if isinstance(r.get("id"), str)}
        artifacts = _list(run.get("artifacts"))
        for res_i, result in enumerate(_list(run.get("results"))):
            if not isinstance(result, dict):
                res.warnings.append(f"runs[{run_i}].results[{res_i}] is not an object; skipped")
                res.skipped.append({"run": run_i, "result": res_i, "reason": "not an object"})
                continue
            draft = _draft(
                result, rules, rules_by_id, artifacts, tool, strip_prefixes, run_i, res_i, res
            )
            draft["seq"] = len(drafts)
            drafts.append(draft)

    # Occurrence counters keep ids unique and stable for identical (tool, rule, file, key).
    groups: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for d in drafts:
        groups[(d["tool"], d["rule_id"], d["file"], d["key"])].append(d)
    for group in groups.values():
        group.sort(key=lambda d: (d["start"], d["col"], d["seq"]))
        for n, d in enumerate(group):
            d["id"] = _make_id(d["tool"], d["rule_id"], d["file"], d["key"], n)

    for d in drafts:
        try:
            res.findings.append(
                Finding.model_validate(
                    {
                        "id": d["id"],
                        "source_tool": d["tool"],
                        "rule_id": d["rule_id"],
                        "cwe": d["cwe"],
                        "owasp_category": d["owasp"],
                        "location": {
                            "file": d["file"],
                            "start_line": d["start"],
                            "end_line": d["end"],
                        },
                        "message": d["message"],
                        "severity_scanner": d["level"],
                    }
                )
            )
        except ValidationError as exc:  # defensive; the draft is already normalised
            where = f"runs[{d['run']}].results[{d['res_i']}]"
            res.warnings.append(f"{where}: invalid finding ({exc.error_count()} errors)")
            res.skipped.append({"run": d["run"], "result": d["res_i"], "reason": "invalid"})
    return res


def _draft(
    result: dict[str, Any],
    rules: list[dict[str, Any]],
    rules_by_id: dict[str, dict[str, Any]],
    artifacts: list[Any],
    tool: str,
    strip_prefixes: Sequence[str],
    run_i: int,
    res_i: int,
    res: ParseResult,
) -> dict[str, Any]:
    where = f"runs[{run_i}].results[{res_i}]"
    idx = result.get("ruleIndex")
    rule: dict[str, Any] = {}
    rule_id = _str(result.get("ruleId")) or _str(_dict(result.get("rule")).get("id"))
    if isinstance(idx, int) and not isinstance(idx, bool) and 0 <= idx < len(rules):
        rule = rules[idx]
        rule_id = rule_id or _str(rule.get("id"))
    if rule_id and rule_id in rules_by_id:
        rule = rules_by_id[rule_id]
    if not rule_id:
        rule_id = UNKNOWN_RULE
        res.warnings.append(f"{where}: no rule id; using '{UNKNOWN_RULE}'")

    level = result.get("level")
    if level not in _LEVELS:
        level = _dict(rule.get("defaultConfiguration")).get("level")
    if level not in _LEVELS:
        level = None

    tags = [
        *_list(_dict(rule.get("properties")).get("tags")),
        *_list(_dict(result.get("properties")).get("tags")),
    ]

    locations = _list(result.get("locations"))
    phys = _dict(_dict(locations[0] if locations else None).get("physicalLocation"))
    art = _dict(phys.get("artifactLocation"))
    uri = _str(art.get("uri"))
    ai = art.get("index")
    if (
        uri is None
        and isinstance(ai, int)
        and not isinstance(ai, bool)
        and 0 <= ai < len(artifacts)
    ):
        uri = _str(_dict(_dict(artifacts[ai]).get("location")).get("uri"))
    file = normalize_uri(uri, strip_prefixes) if uri else UNKNOWN_FILE
    region = _dict(phys.get("region"))
    start = _int(region.get("startLine"))
    if file == UNKNOWN_FILE or start is None:
        res.warnings.append(f"{where}: location incomplete (file or startLine); using placeholder")
    start = start or 1
    end = _int(region.get("endLine")) or start
    if end < start:
        res.warnings.append(f"{where}: endLine < startLine; end set to start")
        end = start

    return {
        "tool": tool,
        "rule_id": rule_id,
        "file": file,
        "key": _content_key(result, region, start),
        "start": start,
        "end": end,
        "col": _int(region.get("startColumn")) or 0,
        "cwe": extract_cwes(tags),
        "owasp": extract_owasp(tags),
        "message": _message(result, rule),
        "level": level,
        "run": run_i,
        "res_i": res_i,
    }
