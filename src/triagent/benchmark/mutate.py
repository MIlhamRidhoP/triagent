"""Mutation generator: semantics-preserving variants of the benchmark with shifted ground truth.

Operations (chosen per run, applied in this order):
- ``strip-comments``: remove every comment, including the misleading "safe" or "alarm" framing.
- ``rename``: new names for declared functions, variables and parameters, the same in all files.
- ``style``: double quotes, ``let`` instead of ``const``, different indentation.

The output directory is a complete benchmark root (``app/``, ``poc/``, ``ground-truth.yaml``) plus
``mutation.json``. Ground truth lines are mapped through the comment removal, labels, CWE ids and
files are untouched, and the result is validated before the function returns. The PoC suite on the
variant is the behavioural proof (``triagent benchmark poc --root <variant>``).
"""

from __future__ import annotations

import json
import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import yaml

from triagent.benchmark import jsmini
from triagent.benchmark.groundtruth import (
    GroundTruthError,
    load_ground_truth,
    sha256_file,
    validate_root,
)

OPS = ("rename", "strip-comments", "style")


class MutationError(Exception):
    """The mutation could not be produced or its result did not validate."""


def parse_ops(text: str) -> list[str]:
    ops = [o.strip() for o in text.split(",") if o.strip()]
    unknown = [o for o in ops if o not in OPS]
    if unknown or not ops:
        raise MutationError(
            f"unknown or empty ops {unknown or text!r}; choose from {', '.join(OPS)}"
        )
    return [o for o in OPS if o in ops]  # canonical order, no duplicates


def _app_files(app: Path) -> list[Path]:
    return sorted(
        p for p in app.rglob("*") if p.is_file() and "node_modules" not in p.relative_to(app).parts
    )


def mutate_root(
    root: str | Path, out: str | Path, *, seed: int, ops: Sequence[str]
) -> dict[str, Any]:
    """Write a mutated copy of the benchmark root to ``out`` and return the mutation record."""
    src_root, dst = Path(root), Path(out)
    ops = [o for o in OPS if o in ops]
    if not ops:
        raise MutationError("no operations selected")
    gt_path = src_root / "ground-truth.yaml"
    try:
        gt = load_ground_truth(gt_path)
    except GroundTruthError as exc:
        raise MutationError(str(exc)) from exc
    if gt.variant is not None:
        raise MutationError("the base ground truth is already a variant; mutate the original")
    if dst.exists():
        raise MutationError(f"output directory {dst} already exists")

    app = src_root / "app"
    texts: dict[str, str] = {}
    binaries: dict[str, bytes] = {}
    for path in _app_files(app):
        rel = path.relative_to(app).as_posix()
        if path.suffix == ".js":
            texts[rel] = path.read_text(encoding="utf-8")
        else:
            binaries[rel] = path.read_bytes()

    line_maps: dict[str, dict[int, int | None]] = {}
    if "strip-comments" in ops:
        for rel, text in texts.items():
            try:
                stripped = jsmini.strip_comments(text)
            except jsmini.JsSyntaxError as exc:
                raise MutationError(f"{rel}: {exc}") from exc
            texts[rel] = stripped.text
            line_maps[rel] = stripped.line_map
    else:
        for rel, text in texts.items():
            line_maps[rel] = {k: k for k in range(1, text.count("\n") + 2)}

    try:
        tokens = {rel: jsmini.tokenize(text) for rel, text in texts.items()}
    except jsmini.JsSyntaxError as exc:
        raise MutationError(str(exc)) from exc
    renames: dict[str, str] = {}
    if "rename" in ops:
        total = jsmini.Analysis()
        for toks in tokens.values():
            total.update(jsmini.analyze(toks))
        renames = jsmini.make_rename_map(total, seed)
    style = None
    if "style" in ops:
        style = "tabs" if seed % 2 else "spaces"

    for rel, text in texts.items():
        texts[rel] = jsmini.rewrite(text, tokens[rel], renames=renames or None, style=style)

    for rel, text in texts.items():
        target = dst / "app" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")
    for rel, data in binaries.items():
        target = dst / "app" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    shutil.copytree(src_root / "poc", dst / "poc")

    doc = gt.model_dump(mode="json")
    for item in doc["items"]:
        new_start, new_end = jsmini.shift_range(
            item["start_line"], item["end_line"], line_maps[item["file"]]
        )
        item["start_line"], item["end_line"] = new_start, new_end
        if "strip-comments" in ops:
            item["framing_text"] = None
    doc["variant"] = {"base_sha256": sha256_file(gt_path), "seed": seed, "ops": ops}
    (dst / "ground-truth.yaml").write_text(
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
        newline="\n",
    )
    record = {"seed": seed, "ops": ops, "renames": dict(sorted(renames.items()))}
    (dst / "mutation.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    problems = validate_root(dst)
    if problems:
        raise MutationError("mutated ground truth does not validate: " + "; ".join(problems[:5]))
    return record
