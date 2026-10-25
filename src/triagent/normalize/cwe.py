"""CWE families for loose matching (I-05, R-07).

The table lives in ``data/cwe-families.yaml`` (generated from the MITRE catalog plus a short list
of manual groups, with the source recorded in its ``meta`` block). Strict matching compares exact
CWE ids; loose matching compares families. A weakness missing from the table is its own family.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

DATA_FILE = Path(__file__).resolve().parent / "data" / "cwe-families.yaml"
_CWE = re.compile(r"^CWE-([1-9][0-9]*)$")


@lru_cache(maxsize=1)
def _table() -> tuple[dict[int, int], dict[str, Any]]:
    raw = yaml.safe_load(DATA_FILE.read_text(encoding="utf-8"))
    families: dict[int, int] = {int(k): int(v) for k, v in raw["families"].items()}
    for group in raw.get("manual_groups", []):
        for member in group["members"]:
            families[int(member)] = int(group["family"])
    return families, raw["meta"]


def table_meta() -> dict[str, Any]:
    """Source and rule of the family table (for reports)."""
    return dict(_table()[1])


def family_of(cwe: str) -> str:
    """Family of ``CWE-n`` as ``CWE-m``. Unknown ids and malformed input map to themselves."""
    m = _CWE.match(cwe)
    if not m:
        return cwe
    n = int(m.group(1))
    return f"CWE-{_table()[0].get(n, n)}"


def families_of(cwes: Iterable[str]) -> frozenset[str]:
    return frozenset(family_of(c) for c in cwes)


def match(a: Iterable[str], b: Iterable[str], *, strict: bool) -> bool:
    """True when the two CWE lists share an exact id (strict) or a family (loose).

    Multi-CWE findings match when any one id (or family) is shared. An empty list never matches.
    """
    la, lb = list(a), list(b)
    if strict:
        return bool(set(la) & set(lb))
    return bool(families_of(la) & families_of(lb))
