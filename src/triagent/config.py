""".triagent.yml loader with validation (SPEC section 6)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

PROFILE_NAME = r"^[A-Za-z0-9][A-Za-z0-9_.-]*$"
VERIFY_MODES = ("triage+verify", "triage+verify+fix")


class ConfigError(Exception):
    """The configuration file is missing, unreadable or invalid."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Budget(_Strict):
    max_usd_per_invocation: float = Field(default=5.0, gt=0)


class VerifyConfig(_Strict):
    enabled: bool = False
    sandbox: Literal["docker"] = "docker"


class Config(_Strict):
    scanners: list[Literal["semgrep", "sonarcloud", "codeql"]] = Field(
        default_factory=lambda: ["semgrep"], min_length=1
    )
    languages: list[Literal["javascript", "typescript"]] = Field(
        default_factory=lambda: ["javascript", "typescript"], min_length=1
    )
    models: list[str] = Field(min_length=1)
    mode: Literal["triage", "triage+verify", "triage+verify+fix"] = "triage"
    redact: bool = True
    redact_experiment: str | None = Field(default=None, min_length=1)
    budget: Budget = Field(default_factory=Budget)
    verify: VerifyConfig = Field(default_factory=VerifyConfig)

    @model_validator(mode="after")
    def _cross_checks(self) -> Config:
        for name in self.models:
            if not re.match(PROFILE_NAME, name):
                raise ValueError(f"invalid model profile name {name!r}")
        if len(set(self.models)) != len(self.models):
            raise ValueError("models contains duplicates")
        if not self.redact and not self.redact_experiment:
            raise ValueError(
                "redact: false requires redact_experiment (I-03: recorded experiments)"
            )
        if self.redact and self.redact_experiment:
            raise ValueError("redact_experiment is only meaningful with redact: false")
        if self.mode in VERIFY_MODES and not self.verify.enabled:
            raise ValueError(f"mode {self.mode!r} requires verify.enabled: true")
        return self


def parse_config(text: str) -> Config:
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML: {exc}") from exc
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ConfigError("top level of the config must be a mapping")
    try:
        return Config.model_validate(raw)
    except ValidationError as exc:
        details = "; ".join(
            f"{'.'.join(str(p) for p in e['loc']) or '<root>'}: {e['msg']}" for e in exc.errors()
        )
        raise ConfigError(f"invalid config: {details}") from exc


def load_config(path: str | Path = ".triagent.yml") -> Config:
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"cannot read {p}: {exc.strerror or exc}") from exc
    return parse_config(text)
