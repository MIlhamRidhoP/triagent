"""Label-hint check (review R-02, pitfall P5): names must not reveal a label.

Run on code with comments removed (framing comments are deliberate). Identifiers, string
literals and file names are split into words (non-alphanumerics and camelCase boundaries). A word
is a hint when it is ``fp`` or ``tp``, or contains safe, trap, vuln, insecure, secure, benign or
exploit. ``http`` is not a hint: ``tp`` only counts as a whole word.
"""

from __future__ import annotations

import re
from pathlib import Path

from triagent.benchmark import jsmini

HINT_SUBSTRINGS = ("safe", "trap", "vuln", "insecure", "secure", "benign", "exploit")
HINT_WORDS = ("fp", "tp")
# Explicit allowlist: file -> exact string literal bodies (banner and refusal message in server.js).
ALLOWED_STRINGS: dict[str, frozenset[str]] = {
    "server.js": frozenset({"refusing to start: this application is intentionally vulnerable"}),
}
_SPLIT = re.compile(r"[^A-Za-z0-9]+")
_CAMEL = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|[0-9]+")


def words(text: str) -> list[str]:
    out: list[str] = []
    for chunk in _SPLIT.split(text):
        out.extend(w.lower() for w in _CAMEL.findall(chunk))
    return out


def hint_in(text: str) -> str | None:
    for w in words(text):
        if w in HINT_WORDS:
            return w
        for sub in HINT_SUBSTRINGS:
            if sub in w:
                return w
    return None


def check_names(root: str | Path) -> list[str]:
    """Return problem lines ``app/<file>: <kind> '<text>' contains hint '<word>'``."""
    app = Path(root) / "app"
    problems: list[str] = []
    for path in sorted(p for p in app.rglob("*") if p.is_file()):
        rel = path.relative_to(app)
        if "node_modules" in rel.parts:
            continue
        name = rel.as_posix()
        hit = hint_in(name)
        if hit:
            problems.append(f"app/{name}: file name contains hint {hit!r}")
        if path.suffix != ".js":
            continue
        text = jsmini.strip_comments(path.read_text(encoding="utf-8")).text
        for tok in jsmini.tokenize(text):
            if tok.kind == "id":
                body, kind = tok.text, "identifier"
            elif tok.kind in ("str", "tpl"):
                body, kind = tok.text.strip("'\"`"), "string"
                if body in ALLOWED_STRINGS.get(name, frozenset()):
                    continue
            else:
                continue
            hit = hint_in(body)
            if hit:
                problems.append(f"app/{name}: {kind} {tok.text[:40]!r} contains hint {hit!r}")
    return problems
