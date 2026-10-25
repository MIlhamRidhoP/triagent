"""CWE family table and matching (I-05, R-07)."""

from __future__ import annotations

import pytest

from triagent.normalize import cwe as cwe_mod
from triagent.normalize.cwe import families_of, family_of, match, table_meta


def test_862_and_863_same_family_loose_but_not_strict():
    assert family_of("CWE-862") == family_of("CWE-863") == "CWE-285"
    assert match(["CWE-862"], ["CWE-863"], strict=False)
    assert not match(["CWE-862"], ["CWE-863"], strict=True)


def test_manual_group_applies_even_if_mitre_data_lacks_it(monkeypatch, tmp_path):
    data = tmp_path / "fam.yaml"
    lines = [
        "meta: {source: test, version: '0', date: x, view: 1000, sha256: x, rule: x}",
        "families: {862: 862, 863: 863}",
        "manual_groups:",
        "  - {family: 285, members: [862, 863], reason: r, source: s, verified: false}",
    ]
    data.write_text(chr(10).join(lines), encoding="utf-8")
    monkeypatch.setattr(cwe_mod, "DATA_FILE", data)
    cwe_mod._table.cache_clear()
    try:
        assert family_of("CWE-862") == family_of("CWE-863") == "CWE-285"
    finally:
        cwe_mod._table.cache_clear()


@pytest.mark.parametrize(
    "a,b,loose",
    [
        ("CWE-79", "CWE-89", False),  # XSS vs SQL injection
        ("CWE-79", "CWE-78", False),  # XSS vs OS command injection
        ("CWE-89", "CWE-78", False),
        ("CWE-79", "CWE-601", False),
        ("CWE-79", "CWE-95", True),  # both under CWE-74 (Injection) in view 1000
    ],
)
def test_family_relations_from_mitre_data(a, b, loose):
    assert match([a], [b], strict=False) is loose
    assert match([a], [b], strict=True) is False


def test_known_families_from_mitre_view_1000():
    assert family_of("CWE-79") == "CWE-74"
    assert family_of("CWE-89") == "CWE-943"
    assert family_of("CWE-78") == "CWE-77"
    assert family_of("CWE-601") == "CWE-610"


def test_unknown_malformed_and_pillar_map_to_themselves():
    assert family_of("CWE-9999999") == "CWE-9999999"
    assert family_of("nonsense") == "nonsense"
    assert family_of("") == ""
    assert family_of("CWE-693") == "CWE-693"  # a pillar


def test_multi_cwe_matching_keeps_any_overlap():
    assert match(["CWE-89", "CWE-79"], ["CWE-79"], strict=True)
    assert match(["CWE-89", "CWE-862"], ["CWE-863"], strict=False)
    assert families_of(["CWE-89", "CWE-79"]) == {"CWE-943", "CWE-74"}


def test_empty_never_matches():
    assert not match([], ["CWE-79"], strict=False)
    assert not match([], [], strict=False)
    assert not match([], [], strict=True)


def test_table_records_its_source():
    meta = table_meta()
    assert "MITRE" in meta["source"] and meta["view"] == 1000 and len(meta["sha256"]) == 64
    assert meta["version"]
