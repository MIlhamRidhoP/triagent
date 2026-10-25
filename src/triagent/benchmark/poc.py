"""Run the benchmark PoC scripts against the benchmark app, only inside Docker (R-08, I-08).

Layout (``benchmark/docker/compose.yaml``): the app, a stand-in internal service and the PoC
container share one ``internal: true`` network, so nothing can leave it and nothing is published.
Every container is non-root, read-only, capability-free and resource limited; the app source and
the PoC scripts are mounted read-only. Only the one-time image build (``npm ci``) uses the network.

PoC exit codes: 0 exploit confirmed, 1 not reproduced, anything else is a harness error.
A tp item must exit 0 and an fp-trap item must exit 1. The app is restarted before each PoC.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
import uuid
from collections.abc import Sequence
from pathlib import Path
from types import TracebackType
from typing import Any

from triagent.benchmark.groundtruth import GroundTruthError, Label, load_ground_truth

REPO_BENCHMARK = Path(__file__).resolve().parents[3] / "benchmark"
SELFTEST_KEYS = (
    "egress_ip_blocked",
    "egress_dns_blocked",
    "non_root",
    "rootfs_read_only",
    "source_mount_read_only",
    "no_default_route",
    "gateway_ports_blocked",
    "docker_tcp_blocked",
    "host_dns_blocked",
    "metadata_blocked",
    "no_docker_sock",
    "control_reachable",
    "error_no_leak",
)


class DockerError(Exception):
    """Docker is missing, a command failed, or the benchmark stack could not start."""


def _run(
    cmd: Sequence[str], *, env: dict[str, str], timeout: float
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            list(cmd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise DockerError("docker is not installed or not on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise DockerError(f"timed out after {timeout:.0f}s: {' '.join(cmd[:6])}") from exc


def image_tag(docker_dir: Path) -> str:
    h = hashlib.sha256()
    for name in ("Dockerfile", "package.json", "package-lock.json", "selftest.js"):
        h.update((docker_dir / name).read_bytes())
    return f"triagent-bench-app:{h.hexdigest()[:12]}"


def ensure_image(docker_dir: Path, env: dict[str, str]) -> str:
    """Build the dependency image once (needs registry access for ``npm ci``), then reuse it."""
    tag = image_tag(docker_dir)
    if _run(["docker", "image", "inspect", tag], env=env, timeout=60).returncode == 0:
        return tag
    built = _run(["docker", "build", "-t", tag, str(docker_dir)], env=env, timeout=900)
    if built.returncode != 0:
        raise DockerError(f"image build failed: {built.stderr[-600:]}")
    return tag


class BenchStack:
    """Context manager: start the isolated stack, run PoCs, always tear it down."""

    def __init__(self, root: Path, docker_dir: Path | None = None) -> None:
        self.root = Path(root).resolve()
        self.docker_dir = Path(docker_dir) if docker_dir else REPO_BENCHMARK / "docker"
        self.project = "tgbench" + uuid.uuid4().hex[:10]
        self.env: dict[str, str] = {}
        self._up = False

    def _compose(self, *args: str, timeout: float = 120) -> subprocess.CompletedProcess[str]:
        compose_file = self.docker_dir / "compose.yaml"
        cmd = ["docker", "compose", "-p", self.project, "-f", str(compose_file), *args]
        return _run(cmd, env=self.env, timeout=timeout)

    def __enter__(self) -> BenchStack:
        base_env = dict(os.environ)
        if _run(["docker", "info"], env=base_env, timeout=60).returncode != 0:
            raise DockerError("the docker daemon is not reachable")
        app_dir, poc_dir = self.root / "app", self.root / "poc"
        for needed in (app_dir, poc_dir, self.docker_dir / "compose.yaml"):
            if not needed.exists():
                raise DockerError(f"missing {needed}")
        tag = ensure_image(self.docker_dir, base_env)
        self.env = {
            **base_env,
            "BENCH_IMAGE": tag,
            "BENCH_APP_DIR": app_dir.as_posix(),
            "BENCH_POC_DIR": poc_dir.as_posix(),
        }
        self._up = True
        started = self._compose("up", "-d", "--wait", "app", "internal", timeout=180)
        if started.returncode != 0:
            tail = (started.stderr or started.stdout)[-600:]
            self.__exit__(None, None, None)
            raise DockerError(f"could not start the benchmark stack: {tail}")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._up:
            self._compose("down", "-v", "--remove-orphans", "-t", "1", timeout=120)
            self._up = False

    def network_internal(self) -> bool:
        listed = _run(
            [
                "docker",
                "network",
                "ls",
                "-q",
                "--filter",
                f"label=com.docker.compose.project={self.project}",
            ],
            env=self.env,
            timeout=60,
        )
        ids = listed.stdout.split()
        if not ids:
            return False
        shown = _run(
            ["docker", "network", "inspect", "--format", "{{.Internal}}", *ids],
            env=self.env,
            timeout=60,
        )
        flags = shown.stdout.split()
        return shown.returncode == 0 and bool(flags) and all(f == "true" for f in flags)

    def restart_app(self) -> None:
        restarted = self._compose("restart", "-t", "1", "app", timeout=60)
        if restarted.returncode != 0:
            raise DockerError(f"restart failed: {restarted.stderr[-300:]}")

    def gateway_ip(self) -> str:
        """Gateway of the bench network (IPAM), read by the host and handed to the probes."""
        listed = _run(
            [
                "docker",
                "network",
                "ls",
                "-q",
                "--filter",
                f"label=com.docker.compose.project={self.project}",
            ],
            env=self.env,
            timeout=60,
        )
        ids = listed.stdout.split()
        if not ids:
            return ""
        fmt = "{{range .IPAM.Config}}{{.Gateway}} {{end}}"
        shown = _run(
            ["docker", "network", "inspect", "--format", fmt, ids[0]], env=self.env, timeout=60
        )
        parts = shown.stdout.split()
        return parts[0] if parts else ""

    def image_id(self) -> str:
        shown = _run(
            ["docker", "image", "inspect", "--format", "{{.Id}}", self.env["BENCH_IMAGE"]],
            env=self.env,
            timeout=60,
        )
        return shown.stdout.strip()

    def selftest_in(self, service: str, gateway: str) -> subprocess.CompletedProcess[str]:
        """Run /opt/selftest/selftest.js inside the poc (fresh container) or app (exec) service."""
        env_args = ["-e", f"BENCH_GATEWAY_IP={gateway}"]
        if service == "poc":
            return self._compose(
                "run",
                "--rm",
                "-T",
                *env_args,
                "poc",
                "node",
                "/opt/selftest/selftest.js",
                timeout=180,
            )
        env_args += ["-e", "SELFTEST_TARGET=http://127.0.0.1:3000"]
        return self._compose(
            "exec", "-T", *env_args, "app", "node", "/opt/selftest/selftest.js", timeout=180
        )

    def run_script(self, script: str, timeout: float = 90) -> subprocess.CompletedProcess[str]:
        return self._compose("run", "--rm", "-T", "poc", "node", f"/poc/{script}", timeout=timeout)


def _last_json(text: str) -> dict[str, Any]:
    for line in reversed(text.strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                return data
    return {}


def run_poc_suite(
    root: str | Path, *, items: Sequence[str] | None = None, docker_dir: Path | None = None
) -> dict[str, Any]:
    """Run the PoC of every (selected) ground truth item. Returns the result document."""
    try:
        gt = load_ground_truth(Path(root) / "ground-truth.yaml")
    except GroundTruthError as exc:
        raise DockerError(str(exc)) from exc
    selected = [i for i in gt.items if not items or i.id in items]
    unknown = sorted(set(items or ()) - {i.id for i in gt.items})
    if unknown:
        raise DockerError(f"unknown item ids: {', '.join(unknown)}")
    results: list[dict[str, Any]] = []
    with BenchStack(Path(root), docker_dir) as stack:
        internal = stack.network_internal()
        image_id = stack.image_id()
        digest = base_image_digest(stack.docker_dir)
        for item in selected:
            expected = 0 if item.label is Label.TP else 1
            stack.restart_app()
            t0 = time.monotonic()
            proc = stack.run_script(Path(item.poc).name)
            verdict = _last_json(proc.stdout)
            code = proc.returncode
            exploited = True if code == 0 else False if code == 1 else None
            results.append(
                {
                    "id": item.id,
                    "label": item.label.value,
                    "expected_exit": expected,
                    "exit_code": code,
                    "exploited": exploited,
                    "attempts": int(verdict.get("attempts", 0)),
                    "evidence": str(verdict.get("evidence", "")),
                    "ok": code == expected and int(verdict.get("attempts", 0)) >= 1,
                    "duration_s": round(time.monotonic() - t0, 2),
                    "stderr_tail": proc.stderr[-300:] if code not in (0, 1) else "",
                }
            )
    return {
        "root": str(Path(root)),
        "base_image_digest": digest,
        "image_id": image_id,
        "network": {"internal": internal},
        "items": results,
        "ok": internal and all(r["ok"] for r in results),
    }


def base_image_digest(docker_dir: Path) -> str:
    """The sha256 digest the Dockerfile pins its base image to ("" when it is not pinned)."""
    m = re.search(
        r"^FROM\s+\S+@(sha256:[0-9a-f]{64})",
        (docker_dir / "Dockerfile").read_text(encoding="utf-8"),
        re.M,
    )
    return m.group(1) if m else ""


def parse_selftest(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Reduce probe output to exactly SELFTEST_KEYS; a missing key counts as False."""
    raw = raw or {}
    return {k: raw.get(k) is True for k in SELFTEST_KEYS}


def selftest_ok(containers: dict[str, dict[str, Any]], network_internal: bool) -> bool:
    return (
        network_internal
        and set(containers) == {"poc", "app"}
        and all(set(c) == set(SELFTEST_KEYS) and all(c.values()) for c in containers.values())
    )


def run_selftest(*, docker_dir: Path | None = None) -> dict[str, Any]:
    """Prove isolation from inside BOTH the PoC and the app container (R-03)."""
    with BenchStack(REPO_BENCHMARK, docker_dir) as stack:
        gateway = stack.gateway_ip()
        containers = {
            name: parse_selftest(_last_json(stack.selftest_in(name, gateway).stdout))
            for name in ("poc", "app")
        }
        internal = stack.network_internal()
    return {
        "containers": containers,
        "gateway_ip": gateway,
        "network_internal": internal,
        "ok": bool(gateway) and selftest_ok(containers, internal),
    }
