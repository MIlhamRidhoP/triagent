"""Benchmark tooling: ground truth validation, JS tokenizer, comment stripping, rename, mutation.

No Docker and no network here. The PoC suite itself runs in the phase gate.
"""

from __future__ import annotations

import hashlib
import re
import shutil
from pathlib import Path
from typing import Any

import pytest
import yaml

from triagent.benchmark import jsmini
from triagent.benchmark.groundtruth import GroundTruthError, load_ground_truth, validate_root
from triagent.benchmark.mutate import MutationError, mutate_root, parse_ops
from triagent.schema_export import check_all

BENCH = Path(__file__).resolve().parents[1] / "benchmark"
SCHEMAS = Path(__file__).resolve().parents[1] / "schemas"

HAND_SRC = """// header comment
'use strict';

/* block
   comment */
const total = 1;
// framing: reviewed and safe
function lookup(userInput) { // trailing
  const label = 'lookup: ' + `${userInput}!`;
  return db.query("x" + userInput + label);
}

module.exports = lookup;
"""


def hand_root(tmp_path: Path) -> Path:
    root = tmp_path / "hand"
    (root / "app").mkdir(parents=True)
    (root / "poc").mkdir()
    (root / "app" / "a.js").write_text(HAND_SRC, encoding="utf-8")
    items = []
    for n, (a, b, anchor) in enumerate(
        [(10, 10, "db.query("), (8, 11, "function"), (6, 6, "= 1;")], 1
    ):
        (root / "poc" / f"BM-00{n}.js").write_text("// dummy\n", encoding="utf-8")
        items.append(
            {
                "id": f"BM-00{n}",
                "title": f"hand {n}",
                "cwe": [["CWE-89", "CWE-79", "CWE-22"][n - 1]],
                "category": "sqli",
                "label": "tp",
                "file": "a.js",
                "start_line": a,
                "end_line": b,
                "anchor": anchor,
                "poc": f"poc/BM-00{n}.js",
                "comment_framing": "none",
                "framing_text": None,
                "trap_kind": None,
                "notes": "hand case",
            }
        )
    doc = {
        "schema_version": 1,
        "app": "hand",
        "corpus_date": "2026-10-01",
        "label_source": "poc",
        "labeled_by": "test",
        "items": items,
    }
    (root / "ground-truth.yaml").write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return root


# ---- tokenizer ----------------------------------------------------------------------------


def kinds(src: str) -> list[tuple[str, str]]:
    return [(t.kind, t.text) for t in jsmini.tokenize(src)]


def test_tokenizer_basic_kinds() -> None:
    toks = kinds("const a = 'x' + 1; // c\n")
    assert toks == [
        ("id", "const"),
        ("id", "a"),
        ("punct", "="),
        ("str", "'x'"),
        ("punct", "+"),
        ("num", "1"),
        ("punct", ";"),
        ("comment", "// c"),
    ]


def test_tokenizer_template_substitution_and_nesting() -> None:
    toks = kinds("`a${b + `c${d}`}e`;")
    assert [t for k, t in toks if k == "id"] == ["b", "d"]
    assert toks[0] == ("tpl", "`a${")
    assert toks[-2] == ("tpl", "}e`")


def test_tokenizer_regex_versus_division() -> None:
    assert ("regex", "/[/]+/g") in kinds("x = s.replace(/[/]+/g, '');")
    toks = kinds("y = a / b / c;")
    assert [k for k, _ in toks].count("regex") == 0


def test_tokenizer_comment_like_text_inside_string_and_regex() -> None:
    toks = kinds("a = 'http://x'; b = /\\/\\//;")
    assert not [t for k, t in toks if k == "comment"]


@pytest.mark.parametrize("bad", ["'open", "/* open", "`open", "a = /open"])
def test_tokenizer_rejects_unterminated(bad: str) -> None:
    with pytest.raises(jsmini.JsSyntaxError):
        jsmini.tokenize(bad)


# ---- comment stripping and line map (hand computed) ---------------------------------------


def test_strip_comments_line_map_matches_hand_count() -> None:
    res = jsmini.strip_comments(HAND_SRC)
    # original -> new: 1 x, 2->1, 3->2, 4 x, 5 x, 6->3, 7 x, 8->4, 9->5, 10->6, 11->7, 12->8, 13->9
    expect = {
        1: None,
        2: 1,
        3: 2,
        4: None,
        5: None,
        6: 3,
        7: None,
        8: 4,
        9: 5,
        10: 6,
        11: 7,
        12: 8,
        13: 9,
    }
    assert {k: v for k, v in res.line_map.items() if k <= 13} == expect
    lines = res.text.splitlines()
    assert len(lines) == 9
    assert lines[3] == "function lookup(userInput) {"
    assert jsmini.shift_range(10, 10, res.line_map) == (6, 6)
    assert jsmini.shift_range(8, 11, res.line_map) == (4, 7)
    assert jsmini.shift_range(6, 6, res.line_map) == (3, 3)


def test_strip_comments_keeps_line_structure_inside_code() -> None:
    res = jsmini.strip_comments("a(); /* x\ny */ b();\nc(); // end\n")
    assert res.text.split("\n") == ["a();", " b();", "c();", ""]
    assert res.line_map == {1: 1, 2: 2, 3: 3, 4: 4}


def test_shift_range_rejects_comment_only_range() -> None:
    res = jsmini.strip_comments("// only\ncode();\n")
    with pytest.raises(ValueError):
        jsmini.shift_range(1, 1, res.line_map)
    assert jsmini.shift_range(1, 2, res.line_map) == (1, 1)


# ---- rename -------------------------------------------------------------------------------


def renamed(src: str, seed: int = 3) -> tuple[str, dict[str, str]]:
    toks = jsmini.tokenize(src)
    mapping = jsmini.make_rename_map(jsmini.analyze(toks), seed)
    return jsmini.rewrite(src, toks, renames=mapping), mapping


def test_rename_is_consistent_and_leaves_strings_properties_and_globals() -> None:
    out, mapping = renamed(HAND_SRC)
    assert {"lookup", "userInput", "total", "label"} <= set(mapping)
    assert "db.query(" in out and "module.exports" in out
    assert "'lookup: '" in out
    new_fn, new_param = mapping["lookup"], mapping["userInput"]
    assert f"function {new_fn}({new_param})" in out
    assert f"${{{new_param}}}!" in out
    assert out.rstrip().endswith(f"module.exports = {new_fn};")


def test_rename_never_touches_properties_keys_methods_or_shorthand() -> None:
    src = (
        "const name = 1;\nconst obj = { name: name, other: 2 };\nobj.name = 3;\n"
        "class K { name() { return 1; } }\nfunction f(a, b) { return { a, b }; }\n"
        "const value = require('x'); value.size = 1;\n"
    )
    out, mapping = renamed(src)
    assert "name" not in mapping  # used as a property and a method name
    assert "a" not in mapping and "b" not in mapping  # shorthand position
    assert f"{mapping['obj']}.name = 3" in out and "{ name: name, other: 2 }" in out
    assert "value" in mapping and "obj" in mapping


def test_rename_mapping_is_deterministic_and_collision_free() -> None:
    toks = jsmini.tokenize(HAND_SRC)
    a = jsmini.make_rename_map(jsmini.analyze(toks), 7)
    b = jsmini.make_rename_map(jsmini.analyze(toks), 7)
    c = jsmini.make_rename_map(jsmini.analyze(toks), 8)
    assert a == b and a != c
    assert len(set(a.values())) == len(a)
    assert not set(a.values()) & jsmini.analyze(toks).identifiers


def test_style_changes_quotes_const_and_indent_but_not_strings_with_quotes() -> None:
    src = "const a = 'x';\nconst b = 'say \"hi\"';\nif (a) {\n  go();\n}\n"
    out = jsmini.rewrite(src, jsmini.tokenize(src), style="spaces")
    assert 'let a = "x";' in out and "let b = 'say \"hi\"';" in out
    assert "\n    go();" in out
    tabs = jsmini.rewrite(src, jsmini.tokenize(src), style="tabs")
    assert "\n\tgo();" in tabs


# ---- ground truth -------------------------------------------------------------------------


def test_real_benchmark_ground_truth_is_valid() -> None:
    assert validate_root(BENCH) == []
    gt = load_ground_truth(BENCH / "ground-truth.yaml")
    labels = [i.label.value for i in gt.items]
    assert labels.count("tp") >= 12 and labels.count("fp-trap") >= 6


def test_schema_file_matches_models() -> None:
    assert check_all(SCHEMAS) == []


def test_validator_flags_wrong_lines_and_anchor(tmp_path: Path) -> None:
    root = hand_root(tmp_path)
    assert validate_root(root) == []
    gt = yaml.safe_load((root / "ground-truth.yaml").read_text(encoding="utf-8"))
    gt["items"][0]["start_line"] = gt["items"][0]["end_line"] = 12
    (root / "ground-truth.yaml").write_text(yaml.safe_dump(gt, sort_keys=False), encoding="utf-8")
    problems = validate_root(root)
    assert any(p.startswith("BM-001:") and "anchor" in p for p in problems)


def test_loader_rejects_bad_shape(tmp_path: Path) -> None:
    root = hand_root(tmp_path)
    path = root / "ground-truth.yaml"
    gt: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    gt["items"][0]["verified"] = True
    path.write_text(yaml.safe_dump(gt), encoding="utf-8")
    with pytest.raises(GroundTruthError):
        load_ground_truth(path)
    assert validate_root(root)[0].startswith("GT:")


# ---- mutation -----------------------------------------------------------------------------


def tree_hash(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def test_mutate_hand_case_shifts_lines_exactly(tmp_path: Path) -> None:
    root = hand_root(tmp_path)
    for ops, seed in ((["strip-comments"], 1), (["rename", "strip-comments", "style"], 5)):
        out = tmp_path / f"out{seed}"
        mutate_root(root, out, seed=seed, ops=ops)
        gt = load_ground_truth(out / "ground-truth.yaml")
        assert {i.id: (i.start_line, i.end_line) for i in gt.items} == {
            "BM-001": (6, 6),
            "BM-002": (4, 7),
            "BM-003": (3, 3),
        }
        assert gt.variant is not None and gt.variant.seed == seed
        assert validate_root(out) == []
        text = (out / "app" / "a.js").read_text(encoding="utf-8")
        assert "//" not in text and "/*" not in text


def test_mutate_is_deterministic_and_does_not_touch_the_source(tmp_path: Path) -> None:
    root = hand_root(tmp_path)
    before = tree_hash(root)
    mutate_root(root, tmp_path / "a", seed=2, ops=["rename", "strip-comments"])
    mutate_root(root, tmp_path / "b", seed=2, ops=["rename", "strip-comments"])
    mutate_root(root, tmp_path / "c", seed=3, ops=["rename", "strip-comments"])
    assert tree_hash(tmp_path / "a") == tree_hash(tmp_path / "b")
    assert tree_hash(tmp_path / "a") != tree_hash(tmp_path / "c")
    assert tree_hash(root) == before


def test_mutate_refuses_existing_output_and_variants_and_bad_ops(tmp_path: Path) -> None:
    root = hand_root(tmp_path)
    (tmp_path / "exists").mkdir()
    with pytest.raises(MutationError):
        mutate_root(root, tmp_path / "exists", seed=1, ops=["rename"])
    mutate_root(root, tmp_path / "v", seed=1, ops=["rename"])
    with pytest.raises(MutationError):
        mutate_root(tmp_path / "v", tmp_path / "vv", seed=1, ops=["rename"])
    with pytest.raises(MutationError):
        parse_ops("rename,shuffle")
    assert parse_ops("style,rename") == ["rename", "style"]


def test_mutate_real_benchmark_without_docker(tmp_path: Path) -> None:
    out = tmp_path / "v"
    record = mutate_root(BENCH, out, seed=11, ops=["rename", "strip-comments", "style"])
    assert len(record["renames"]) >= 20
    original = load_ground_truth(BENCH / "ground-truth.yaml")
    mutated = load_ground_truth(out / "ground-truth.yaml")
    assert [i.label for i in original.items] == [i.label for i in mutated.items]
    text = "\n".join(p.read_text(encoding="utf-8") for p in (out / "app").rglob("*.js"))
    assert "escapeHtml" not in text and "assertTicketOwner" not in text
    assert not re.search(r"^\s*(//|/\*)", text, re.M)
    shutil.rmtree(out)


# ---- infrastructure that must stay hardened ------------------------------------------------


def test_compose_file_is_hardened() -> None:
    compose = yaml.safe_load((BENCH / "docker" / "compose.yaml").read_text(encoding="utf-8"))
    assert all(n.get("internal") is True for n in compose["networks"].values())
    for name, svc in compose["services"].items():
        assert "ports" not in svc, name
        assert svc["read_only"] is True and svc["cap_drop"] == ["ALL"], name
        assert svc["user"].split(":")[0] not in ("0", "root"), name
        assert all(v.endswith(":ro") for v in svc.get("volumes", [])), name


# ---- review cycle 1: R-01 spacing, R-02 names, R-03 parser ---------------------------------


def test_validator_rejects_close_items_of_the_same_family(tmp_path: Path) -> None:
    root = hand_root(tmp_path)
    path = root / "ground-truth.yaml"
    gt = yaml.safe_load(path.read_text(encoding="utf-8"))
    gt["items"][2].update(cwe=["CWE-89"], start_line=6, end_line=6, anchor="= 1;")
    path.write_text(yaml.safe_dump(gt, sort_keys=False), encoding="utf-8")
    problems = validate_root(root)  # items at 10 and 6, same family, gap 4 <= 5
    assert any("too close" in p for p in problems)
    gt["items"][0].update(start_line=13, end_line=13, anchor="module.exports")
    gt["items"][1]["cwe"] = ["CWE-22"]
    path.write_text(yaml.safe_dump(gt, sort_keys=False), encoding="utf-8")
    assert validate_root(root) == []  # gap 7 is far enough


@pytest.mark.parametrize(
    ("name", "code", "expect_clean"),
    [
        ("a.js", "app.get('/x-safe', f);\n", False),
        ("a.js", "function trapHandler() { return 1; }\n", False),
        ("a.js", "const isSafeRoute = 1;\n", False),
        ("a.js", "const t = `/vuln-${x}`;\n", False),
        ("safe-route.js", "const a = 1;\n", False),
        ("a.js", "// safe trap\nconst http = require('http'); go('/jump');\n", True),
    ],
)
def test_check_names(tmp_path: Path, name: str, code: str, expect_clean: bool) -> None:
    from triagent.benchmark.hints import check_names

    (tmp_path / "app").mkdir()
    (tmp_path / "app" / name).write_text(code, encoding="utf-8")
    assert (check_names(tmp_path) == []) is expect_clean


def test_real_benchmark_has_no_label_hints() -> None:
    from triagent.benchmark.hints import check_names

    assert check_names(BENCH) == []


def test_selftest_parser_treats_missing_keys_as_failure() -> None:
    from triagent.benchmark.poc import SELFTEST_KEYS, parse_selftest, selftest_ok

    full = dict.fromkeys(SELFTEST_KEYS, True)
    good = {"poc": parse_selftest(full), "app": parse_selftest(full)}
    assert selftest_ok(good, True) and not selftest_ok(good, False)
    partial = dict(full)
    del partial["no_default_route"]
    bad = {"poc": parse_selftest(partial), "app": parse_selftest(full)}
    assert bad["poc"]["no_default_route"] is False and not selftest_ok(bad, True)
    assert not selftest_ok({"poc": good["poc"]}, True)
    assert set(parse_selftest({"extra": True})) == set(SELFTEST_KEYS)
