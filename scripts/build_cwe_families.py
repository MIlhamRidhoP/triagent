"""Build src/triagent/normalize/data/cwe-families.yaml from the MITRE CWE catalog XML.

Usage (run with ``python -I``; the XML is untrusted data and is only parsed, never executed):

    python -I scripts/build_cwe_families.py cwec_v4.20.xml cwec_v4.20.zip

Rule (engineering decision, D-31): the family of weakness X is its nearest *proper* ancestor
in view 1000 (Research Concepts, "ChildOf") whose abstraction is Class or Pillar. When a node
has several parents, the walk is breadth-first and ties go to the lowest CWE id. A Pillar is
its own family. A weakness with no Class or Pillar ancestor is its own family (not listed).
Manual groups below are applied on top; they are NOT derived from MITRE.
"""

from __future__ import annotations

import hashlib
import sys
import xml.etree.ElementTree as ET
from collections import deque
from pathlib import Path

import yaml

OUT = Path(__file__).resolve().parent.parent / "src/triagent/normalize/data/cwe-families.yaml"

# Manual groups: frequently confused pairs (R-07). 862 and 863 are also siblings under CWE-285 in
# view 1000, so this entry only makes the pairing explicit and independent of future MITRE edits.
MANUAL_GROUPS = [
    {
        "family": 285,
        "members": [862, 863],
        "reason": "Missing Authorization (862) and Incorrect Authorization (863) are often confused",
        "source": "MITRE CWE v4.20: both are ChildOf CWE-285 in view 1000 (checked in this build)",
        "verified": True,
    }
]


def build(xml_path: Path, zip_path: Path | None) -> dict:
    root = ET.parse(xml_path).getroot()
    ns = {"c": root.tag.split("}")[0][1:]}
    parents: dict[int, list[int]] = {}
    abstraction: dict[int, str] = {}
    for w in root.findall(".//c:Weaknesses/c:Weakness", ns):
        i = int(w.get("ID"))
        abstraction[i] = w.get("Abstraction", "")
        parents[i] = sorted(
            int(r.get("CWE_ID"))
            for r in w.findall("c:Related_Weaknesses/c:Related_Weakness", ns)
            if r.get("Nature") == "ChildOf" and r.get("View_ID") == "1000"
        )
    families: dict[int, int] = {}
    for i in sorted(parents):
        if abstraction[i] == "Pillar":
            continue
        seen = {i}
        queue = deque(parents[i])
        found = None
        while queue:
            p = queue.popleft()
            if p in seen:
                continue
            seen.add(p)
            if abstraction.get(p) in ("Class", "Pillar"):
                found = p
                break
            queue.extend(parents.get(p, []))
        if found is not None:
            families[i] = found
    for g in MANUAL_GROUPS:
        for m in g["members"]:
            assert m in abstraction, f"manual member CWE-{m} not in catalog"
            assert all(p in parents[m] for p in [g["family"]]), (
                f"CWE-{m} is not ChildOf CWE-{g['family']}; mark verified false"
            )
    digest = hashlib.sha256((zip_path or xml_path).read_bytes()).hexdigest()
    return {
        "meta": {
            "source": "MITRE CWE catalog (cwe.mitre.org/data/xml/cwec_latest.xml.zip)",
            "version": root.get("Version"),
            "date": root.get("Date"),
            "view": 1000,
            "sha256": digest,
            "sha256_of": (zip_path or xml_path).name,
            "rule": (
                "family = nearest proper ancestor of abstraction Class or Pillar via ChildOf in "
                "view 1000 (BFS, lowest id on ties); Pillar and unlisted ids are their own family"
            ),
            "generated_by": "scripts/build_cwe_families.py",
        },
        "families": {k: families[k] for k in sorted(families)},
        "manual_groups": MANUAL_GROUPS,
    }


def main() -> None:
    xml_path = Path(sys.argv[1])
    zip_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    data = build(xml_path, zip_path)
    OUT.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=False, width=100), encoding="utf-8"
    )
    print(f"wrote {OUT} ({len(data['families'])} families)")


if __name__ == "__main__":
    main()
