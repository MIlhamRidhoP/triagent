"""Semgrep adapter: command construction and error handling, with a fake runner (no Docker)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from triagent.ingest import semgrep as sg

SARIF = (
    Path(__file__).parent / "fixtures" / "sarif" / "semgrep-1.181.1-js-sample.sarif"
).read_text(encoding="utf-8")


class Fake:
    def __init__(self, rc=0, out=SARIF, err="", exc=None):
        self.rc, self.out, self.err, self.exc = rc, out, err, exc
        self.calls = []

    def __call__(self, cmd, **kw):
        self.calls.append((cmd, kw))
        if self.exc:
            raise self.exc
        return subprocess.CompletedProcess(cmd, self.rc, stdout=self.out, stderr=self.err)


def test_pinned_image_constant():
    assert sg.is_pinned(sg.SEMGREP_IMAGE) and sg.SEMGREP_VERSION in SARIF


@pytest.mark.parametrize(
    "image,ok",
    [
        ("semgrep/semgrep@sha256:" + "a" * 64, True),
        ("semgrep/semgrep:1.181.1", True),
        ("semgrep/semgrep:latest", False),
        ("semgrep/semgrep", False),
        ("semgrep/semgrep:1.181", False),
        ("semgrep/semgrep@sha256:abc", False),
    ],
)
def test_is_pinned(image, ok):
    assert sg.is_pinned(image) is ok


def test_command_shape(tmp_path):
    fake = Fake()
    out = sg.run_semgrep(tmp_path, runner=fake)
    cmd, kw = fake.calls[0]
    assert cmd[:3] == ["docker", "run", "--rm"] and kw.get("shell") is None
    assert sg.SEMGREP_IMAGE in cmd and "--metrics=off" in cmd and "--sarif" in cmd
    mount = cmd[cmd.index("--mount") + 1]
    assert mount.endswith(",readonly") and "target=/src" in mount
    assert kw["timeout"] == sg.DEFAULT_TIMEOUT_S
    assert len(out.findings) == 4
    assert {f.location.file for f in out.findings} == {"app.js"}


def test_target_cannot_inject_mount_options(tmp_path):
    with pytest.raises(ValueError):
        sg.build_command(tmp_path / "a,b", sg.SEMGREP_IMAGE, sg.DEFAULT_CONFIGS)


@pytest.mark.parametrize("bad", ["auto", "p/x; rm -rf /", "--config", "", "../x", "p/ a"])
def test_bad_configs_rejected(tmp_path, bad):
    with pytest.raises(ValueError):
        sg.run_semgrep(tmp_path, configs=(bad,), runner=Fake())


def test_no_configs_and_unpinned_image_rejected(tmp_path):
    with pytest.raises(ValueError):
        sg.run_semgrep(tmp_path, configs=(), runner=Fake())
    with pytest.raises(ValueError):
        sg.run_semgrep(tmp_path, image="semgrep/semgrep:latest", runner=Fake())


def test_failures_become_semgrep_error(tmp_path):
    with pytest.raises(sg.SemgrepError, match="exited with 2"):
        sg.run_semgrep(tmp_path, runner=Fake(rc=2, err="boom"))
    with pytest.raises(sg.SemgrepError, match="not installed"):
        sg.run_semgrep(tmp_path, runner=Fake(exc=FileNotFoundError()))
    with pytest.raises(sg.SemgrepError, match="timed out"):
        sg.run_semgrep(tmp_path, runner=Fake(exc=subprocess.TimeoutExpired("docker", 1)))
    with pytest.raises(sg.SemgrepError, match="valid SARIF"):
        sg.run_semgrep(tmp_path, runner=Fake(out="not json"))
