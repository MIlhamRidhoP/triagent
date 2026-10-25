"""A small JavaScript tokenizer and three source rewrites used by the mutation generator.

This is not a full parser. It understands comments, strings, template literals (with nested
substitutions) and regex literals well enough to rename identifiers, drop comments and change
style without touching text inside strings. The renamer is deliberately conservative: a name that
is also used as a property, a method name, or in a shorthand/destructuring position is never
renamed. Correctness of a mutated variant is proven elsewhere, by running the PoC suite on it.
"""

from __future__ import annotations

import random
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

KEYWORDS = frozenset(
    """
    break case catch class const continue debugger default delete do else enum export extends
    false finally for function if import in instanceof new null return super switch this throw
    true try typeof var void while with yield let static async await of get set
    """.split()  # noqa: SIM905
)
# Names that must never be produced or renamed even if the code declares them.
RESERVED_NAMES = KEYWORDS | frozenset(
    """
    undefined NaN Infinity arguments eval constructor prototype __proto__ require module exports
    process console Buffer global globalThis Object Array String Number Boolean Map Set WeakMap
    JSON Math Date Error Promise RegExp URL URLSearchParams Symbol Function
    """.split()  # noqa: SIM905
)
_REGEX_AFTER_WORDS = frozenset(
    "return typeof instanceof in of new delete void throw case do else yield await".split()  # noqa: SIM905
)
_PUNCT = (
    ">>>=", "...", "===", "!==", "**=", "<<=", ">>=", ">>>", "&&=", "||=", "??=",
    "=>", "==", "!=", "<=", ">=", "&&", "||", "??", "?.", "++", "--", "+=", "-=", "*=", "/=",
    "%=", "&=", "|=", "^=", "**", "<<", ">>",
)  # fmt: skip
_NUMBER = re.compile(
    r"0[xX][0-9a-fA-F_]+n?|0[bB][01_]+n?|0[oO][0-7_]+n?"
    r"|(?:\d[\d_]*\.?[\d_]*|\.\d[\d_]*)(?:[eE][+-]?\d+)?n?"
)
_IDENT = re.compile(r"(?:[^\W\d]|\$)[\w$]*")


class JsSyntaxError(ValueError):
    """The text is not tokenizable (unterminated string, comment, template or regex)."""


@dataclass(frozen=True, slots=True)
class Token:
    kind: str  # id, num, str, tpl, regex, punct, comment
    text: str
    start: int
    end: int


def tokenize(src: str) -> list[Token]:
    toks: list[Token] = []
    n = len(src)
    i = 0
    stack: list[int] = []  # open-brace depth inside each active ${ ... }
    prev: Token | None = None

    def add(kind: str, start: int, end: int) -> Token:
        nonlocal prev
        tok = Token(kind, src[start:end], start, end)
        toks.append(tok)
        if kind != "comment":
            prev = tok
        return tok

    def scan_chunk(j: int) -> tuple[int, bool]:
        """Scan template text from j. Returns (end, closed); closed False means ``${`` follows."""
        while j < n:
            ch = src[j]
            if ch == "\\":
                j += 2
            elif ch == "`":
                return j + 1, True
            elif ch == "$" and src.startswith("${", j):
                return j + 2, False
            else:
                j += 1
        raise JsSyntaxError("unterminated template literal")

    def regex_allowed() -> bool:
        if prev is None:
            return True
        if prev.kind == "punct":
            return prev.text not in (")", "]", "}")
        if prev.kind == "tpl":
            return prev.text.endswith("${")
        if prev.kind == "id":
            return prev.text in _REGEX_AFTER_WORDS
        return False

    while i < n:
        c = src[i]
        if c.isspace() or c == "﻿":
            i += 1
            continue
        if src.startswith("//", i):
            j = src.find("\n", i)
            j = n if j < 0 else j
            add("comment", i, j)
            i = j
            continue
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            if j < 0:
                raise JsSyntaxError("unterminated block comment")
            add("comment", i, j + 2)
            i = j + 2
            continue
        if c in "\"'":
            j = i + 1
            while j < n and src[j] != c:
                if src[j] == "\\":
                    j += 1
                elif src[j] == "\n":
                    raise JsSyntaxError("unterminated string")
                j += 1
            if j >= n:
                raise JsSyntaxError("unterminated string")
            add("str", i, j + 1)
            i = j + 1
            continue
        if c == "`":
            j, closed = scan_chunk(i + 1)
            add("tpl", i, j)
            if not closed:
                stack.append(0)
            i = j
            continue
        if c == "}" and stack:
            if stack[-1] == 0:
                stack.pop()
                j, closed = scan_chunk(i + 1)
                add("tpl", i, j)
                if not closed:
                    stack.append(0)
                i = j
                continue
            stack[-1] -= 1
            add("punct", i, i + 1)
            i += 1
            continue
        if c == "{" and stack:
            stack[-1] += 1
            add("punct", i, i + 1)
            i += 1
            continue
        if c == "/" and regex_allowed():
            j = i + 1
            in_class = False
            while j < n:
                ch = src[j]
                if ch == "\\":
                    j += 1
                elif ch == "\n":
                    raise JsSyntaxError("unterminated regex literal")
                elif ch == "[":
                    in_class = True
                elif ch == "]":
                    in_class = False
                elif ch == "/" and not in_class:
                    break
                j += 1
            if j >= n:
                raise JsSyntaxError("unterminated regex literal")
            j += 1
            while j < n and (src[j].isalnum() or src[j] == "_"):
                j += 1
            add("regex", i, j)
            i = j
            continue
        if c.isdigit() or (c == "." and i + 1 < n and src[i + 1].isdigit()):
            m = _NUMBER.match(src, i)
            assert m is not None
            add("num", i, m.end())
            i = m.end()
            continue
        m = _IDENT.match(src, i)
        if m:
            add("id", i, m.end())
            i = m.end()
            continue
        for p in _PUNCT:
            if src.startswith(p, i):
                add("punct", i, i + len(p))
                i += len(p)
                break
        else:
            add("punct", i, i + 1)
            i += 1
    return toks


# --------------------------------------------------------------------------------------
# Comment removal with a line map
# --------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StripResult:
    text: str
    # original 1-based line -> new 1-based line, None when the whole line was deleted
    line_map: dict[int, int | None]


def strip_comments(src: str) -> StripResult:
    """Remove comments. Lines that held only comments are deleted; blank lines stay.

    A comment at the end of a code line is removed with the whitespace before it. A block comment
    inside a line of code keeps the line structure (its newlines are preserved).
    """
    mask = [False] * len(src)
    for tok in tokenize(src):
        if tok.kind == "comment":
            for k in range(tok.start, tok.end):
                mask[k] = True
    kept_chars = [("" if (mask[k] and ch != "\n") else ch) for k, ch in enumerate(src)]
    masked = "".join(kept_chars)
    orig_lines = src.split("\n")
    new_lines_text = masked.split("\n")
    out: list[str] = []
    line_map: dict[int, int | None] = {}
    offset = 0
    for idx, (orig, new) in enumerate(zip(orig_lines, new_lines_text, strict=True), start=1):
        had_comment = any(mask[offset : offset + len(orig)])
        offset += len(orig) + 1
        if had_comment and new.strip() == "":
            line_map[idx] = None
            continue
        out.append(new.rstrip() if had_comment else new)
        line_map[idx] = len(out)
    return StripResult("\n".join(out), line_map)


def shift_range(start: int, end: int, line_map: Mapping[int, int | None]) -> tuple[int, int]:
    """Map an original line range to the new file: first kept line at or after start, last kept
    line at or before end."""
    new_start = next((line_map[k] for k in range(start, end + 1) if line_map.get(k)), None)
    new_end = next((line_map[k] for k in range(end, start - 1, -1) if line_map.get(k)), None)
    if new_start is None or new_end is None:
        raise ValueError(f"lines {start}-{end} hold only comments, cannot shift")
    return new_start, new_end  # type: ignore[return-value]


# --------------------------------------------------------------------------------------
# Identifier analysis and rename
# --------------------------------------------------------------------------------------


@dataclass(slots=True)
class Analysis:
    declared: set[str] = field(default_factory=set)
    properties: set[str] = field(default_factory=set)  # after "." or method names
    risky: set[str] = field(default_factory=set)  # shorthand / destructuring positions
    identifiers: set[str] = field(default_factory=set)  # every identifier seen

    def update(self, other: Analysis) -> None:
        self.declared |= other.declared
        self.properties |= other.properties
        self.risky |= other.risky
        self.identifiers |= other.identifiers

    def renamable(self) -> list[str]:
        banned = self.properties | self.risky | RESERVED_NAMES
        return sorted(n for n in self.declared if n not in banned)


def _sig(tokens: Iterable[Token]) -> list[Token]:
    return [t for t in tokens if t.kind != "comment"]


def _match_forward(sig: list[Token], i: int) -> int:
    """Index of the bracket that closes the "(" at i, or -1."""
    depth = 0
    for k in range(i, len(sig)):
        t = sig[k]
        if t.kind == "punct" and t.text in "([{":
            depth += 1
        elif t.kind == "punct" and t.text in ")]}":
            depth -= 1
            if depth == 0:
                return k
    return -1


def _match_backward(sig: list[Token], i: int) -> int:
    depth = 0
    for k in range(i, -1, -1):
        t = sig[k]
        if t.kind == "punct" and t.text in ")]}":
            depth += 1
        elif t.kind == "punct" and t.text in "([{":
            depth -= 1
            if depth == 0:
                return k
    return -1


def _params(sig: list[Token], open_idx: int, close_idx: int, out: set[str]) -> None:
    depth = 0
    for k in range(open_idx, close_idx + 1):
        t = sig[k]
        if t.kind == "punct" and t.text in "([{":
            depth += 1
        elif t.kind == "punct" and t.text in ")]}":
            depth -= 1
        elif t.kind == "id" and depth == 1 and sig[k - 1].text in ("(", ","):
            nxt = sig[k + 1].text if k + 1 < len(sig) else ""
            if nxt in (",", ")", "="):
                out.add(t.text)


def key_positions(sig: list[Token]) -> set[int]:
    """Indexes (in ``sig``) of identifiers used as object-literal keys: ``{ name: value }``."""
    keys: set[int] = set()
    for brackets, i in _brackets(sig):
        t = sig[i]
        if (
            t.kind == "id"
            and brackets
            and brackets[-1] == "{"
            and i + 1 < len(sig)
            and sig[i + 1].text == ":"
            and sig[i - 1].text in ("{", ",")
        ):
            keys.add(i)
    return keys


def _brackets(sig: list[Token]) -> Iterable[tuple[list[str], int]]:
    """Yield (open bracket stack before token i, i). Template substitutions count as braces."""
    stack: list[str] = []
    for i, t in enumerate(sig):
        yield stack, i
        if t.kind == "punct" and t.text in "([{":
            stack.append(t.text)
        elif t.kind == "punct" and t.text in ")]}" and stack:
            stack.pop()
        elif t.kind == "tpl":
            if t.text.startswith("}") and stack:
                stack.pop()
            if t.text.endswith("${"):
                stack.append("{")


def analyze(tokens: list[Token]) -> Analysis:
    sig = _sig(tokens)
    a = Analysis()
    for t in sig:
        if t.kind == "id":
            a.identifiers.add(t.text)
    for i, t in enumerate(sig):
        nxt = sig[i + 1] if i + 1 < len(sig) else None
        prv = sig[i - 1] if i > 0 else None
        if t.kind == "id" and t.text in ("const", "let", "var") and nxt and nxt.kind == "id":
            a.declared.add(nxt.text)
        elif t.kind == "id" and t.text == "function":
            j = i + 1
            if nxt and nxt.kind == "id":
                a.declared.add(nxt.text)
                j += 1
            if j < len(sig) and sig[j].text == "(":
                close = _match_forward(sig, j)
                if close > 0:
                    _params(sig, j, close, a.declared)
        elif t.kind == "id" and t.text == "class" and nxt and nxt.kind == "id":
            a.declared.add(nxt.text)
        elif t.kind == "id" and t.text == "catch" and nxt and nxt.text == "(":
            close = _match_forward(sig, i + 1)
            if close > 0:
                _params(sig, i + 1, close, a.declared)
        elif t.kind == "punct" and t.text == "=>" and prv is not None:
            if prv.kind == "id":
                a.declared.add(prv.text)
            elif prv.text == ")":
                open_idx = _match_backward(sig, i - 1)
                if open_idx >= 0:
                    _params(sig, open_idx, i - 1, a.declared)
        if t.kind == "id" and prv is not None and prv.text in (".", "?."):
            a.properties.add(t.text)
        if (
            t.kind == "id"
            and t.text not in KEYWORDS
            and nxt is not None
            and nxt.text == "("
            and not (prv is not None and prv.text in ("function", "."))
        ):
            close = _match_forward(sig, i + 1)
            if 0 < close + 1 < len(sig) and sig[close + 1].text == "{":
                a.properties.add(t.text)  # method definition
    for brackets, i in _brackets(sig):
        t = sig[i]
        if t.kind != "id" or not brackets or brackets[-1] != "{":
            continue
        prv = sig[i - 1] if i > 0 else None
        nxt = sig[i + 1] if i + 1 < len(sig) else None
        if (
            prv is not None
            and nxt is not None
            and prv.text in ("{", ",")
            and nxt.text in (",", "}")
        ):
            a.risky.add(t.text)
    return a


def make_rename_map(analysis: Analysis, seed: int) -> dict[str, str]:
    rng = random.Random(seed)
    taken = set(analysis.identifiers) | RESERVED_NAMES
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    mapping: dict[str, str] = {}
    for name in analysis.renamable():
        while True:
            fresh = "_" + "".join(rng.choice(alphabet) for _ in range(7))
            if fresh not in taken:
                break
        taken.add(fresh)
        mapping[name] = fresh
    return mapping


# --------------------------------------------------------------------------------------
# Rewriting
# --------------------------------------------------------------------------------------


def rewrite(
    src: str,
    tokens: list[Token],
    *,
    renames: Mapping[str, str] | None = None,
    style: str | None = None,
) -> str:
    """Rebuild the source from tokens, renaming identifiers and/or changing style.

    ``style`` is "spaces" (indentation doubled) or "tabs" (two spaces become one tab). Both also
    switch simple single-quoted strings to double quotes and ``const`` to ``let``.
    """
    sig = _sig(tokens)
    sig_index = {t.start: k for k, t in enumerate(sig)}
    keys = key_positions(sig) if renames else set()
    out: list[str] = []
    pos = 0
    for tok in tokens:
        gap = src[pos : tok.start]
        if style and "\n" in gap:
            head, _, indent = gap.rpartition("\n")
            if indent and set(indent) == {" "}:
                indent = (
                    indent * 2
                    if style == "spaces"
                    else "\t" * (len(indent) // 2) + " " * (len(indent) % 2)
                )
            gap = head + "\n" + indent
        out.append(gap)
        text = tok.text
        if tok.kind == "id":
            k = sig_index[tok.start]
            prev_text = sig[k - 1].text if k > 0 else ""
            if renames and text in renames and prev_text not in (".", "?.") and k not in keys:
                text = renames[text]
            elif style and text == "const":
                text = "let"
        elif tok.kind == "str" and style:
            body = text[1:-1]
            if text[0] == "'" and '"' not in body and "\\" not in body:
                text = '"' + body + '"'
        out.append(text)
        pos = tok.end
    out.append(src[pos:])
    return "".join(out)
