"""Semgrep adapter: run the pinned Docker image and parse its SARIF (R-05).

Semgrep is never required on PATH. Tests use fixtures or a fake ``runner``; this module does not
open network connections itself. The container (which fetches registry rules) is started with
the scanned directory mounted read-only. The scanned code is data and is never executed here.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

from triagent.ingest.sarif import ParseResult, SarifError, parse_sarif

SEMGREP_VERSION = "1.181.1"
# Digest of semgrep/semgrep resolved to 1.181.1 when the fixture was generated (see
# tests/fixtures/sarif/PROVENANCE.md). A digest cannot be moved, a tag can.
SEMGREP_IMAGE = (
    "semgrep/semgrep@sha256:3db5c7af55eb1f512eac0abf0ab69a97b52c74b5e9a27314c221aee1a78d7ab2"
)
DEFAULT_CONFIGS = ("p/javascript", "p/nodejs")
CONTAINER_ROOT = "/src"
DEFAULT_TIMEOUT_S = 900

_DIGEST = re.compile(r"@sha256:[0-9a-f]{64}$")
_SEMVER_TAG = re.compile(r":[0-9]+\.[0-9]+\.[0-9]+$")
_CONFIG = re.compile(r"^[pr]/[A-Za-z0-9_.\-/]+$")

Runner = Callable[..., "subprocess.CompletedProcess[str]"]


class SemgrepError(Exception):
    """Docker or Semgrep failed, or produced no usable SARIF."""


def is_pinned(image: str) -> bool:
    """True for ``name@sha256:<digest>`` or ``name:<major.minor.patch>``; never ``latest``."""
    return bool(_DIGEST.search(image) or _SEMVER_TAG.search(image))


def build_command(target: Path, image: str, configs: Sequence[str]) -> list[str]:
    if not is_pinned(image):
        raise ValueError(f"image must be pinned by digest or exact version: {image!r}")
    if not configs:
        raise ValueError("at least one Semgrep config is required")
    for c in configs:
        if not _CONFIG.match(c):
            raise ValueError(
                f"unsupported Semgrep config (registry packs p/... or r/... only): {c!r}"
            )
    source = str(target.resolve())
    if "," in source or "\n" in source:
        raise ValueError("target path must not contain ',' or newlines")
    cmd = [
        "docker",
        "run",
        "--rm",
        "--mount",
        f"type=bind,source={source},target={CONTAINER_ROOT},readonly",
        "-w",
        CONTAINER_ROOT,
        image,
        "semgrep",
        "scan",
    ]
    for c in configs:
        cmd += ["--config", c]
    return [*cmd, "--metrics=off", "--sarif", CONTAINER_ROOT]


def run_semgrep(
    target: Path,
    *,
    image: str = SEMGREP_IMAGE,
    configs: Sequence[str] = DEFAULT_CONFIGS,
    runner: Runner = subprocess.run,
    timeout: int = DEFAULT_TIMEOUT_S,
) -> ParseResult:
    """Scan ``target`` in the pinned container and return the parsed findings.

    Raises ``ValueError`` for unsafe arguments and ``SemgrepError`` for run failures.
    """
    cmd = build_command(target, image, configs)
    try:
        proc = runner(cmd, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    except FileNotFoundError as exc:
        raise SemgrepError("docker is not installed or not on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise SemgrepError(f"semgrep timed out after {timeout}s") from exc
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()[-3:]
        raise SemgrepError(f"docker/semgrep exited with {proc.returncode}: {' | '.join(tail)}")
    try:
        return parse_sarif(proc.stdout, strip_prefixes=(CONTAINER_ROOT,))
    except SarifError as exc:
        raise SemgrepError(f"semgrep did not produce valid SARIF: {exc}") from exc
