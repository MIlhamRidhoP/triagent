from __future__ import annotations

import pytest

from triagent.config import ConfigError, load_config, parse_config

SPEC_SKETCH = """
scanners: [semgrep]
languages: [javascript, typescript]
models: [profile-a, profile-b, profile-c]
mode: triage
redact: true
budget:
  max_usd_per_invocation: 5
verify:
  enabled: false
  sandbox: docker
"""


def test_spec_sketch_is_valid():
    cfg = parse_config(SPEC_SKETCH)
    assert cfg.models == ["profile-a", "profile-b", "profile-c"]
    assert cfg.budget.max_usd_per_invocation == 5
    assert cfg.redact is True


def test_defaults_are_safe():
    cfg = parse_config("models: [a]")
    assert cfg.mode == "triage" and cfg.redact is True and cfg.verify.enabled is False
    assert cfg.budget.max_usd_per_invocation == 5


@pytest.mark.parametrize(
    "text",
    [
        "",  # models is required
        "models: []",
        "models: [a, a]",
        "models: ['bad name']",
        "models: [a]\nunknown: 1",
        "models: [a]\nmode: yolo",
        "models: [a]\nscanners: []",
        "models: [a]\nscanners: [nope]",
        "models: [a]\nbudget:\n  max_usd_per_invocation: 0",
        "models: [a]\nbudget:\n  max_usd_per_invocation: -1",
        "models: [a]\nmode: triage+verify",
        "models: [a]\nmode: triage+verify+fix\nverify: {enabled: false}",
        "models: [a]\nredact: false",
        "models: [a]\nredact: true\nredact_experiment: exp-1",
        "- just\n- a list",
        "models: [a\n",
    ],
)
def test_invalid_configs_are_rejected(text):
    with pytest.raises(ConfigError):
        parse_config(text)


def test_verify_mode_with_verify_enabled_is_valid():
    cfg = parse_config("models: [a]\nmode: triage+verify\nverify: {enabled: true}")
    assert cfg.mode == "triage+verify"


def test_redaction_off_only_for_recorded_experiment():
    cfg = parse_config("models: [a]\nredact: false\nredact_experiment: exp-42")
    assert cfg.redact is False and cfg.redact_experiment == "exp-42"


def test_error_message_names_the_field():
    with pytest.raises(ConfigError, match="mode"):
        parse_config("models: [a]\nmode: yolo")


def test_load_config_from_file_and_missing_file(tmp_path):
    p = tmp_path / ".triagent.yml"
    p.write_text(SPEC_SKETCH, encoding="utf-8")
    assert load_config(p).mode == "triage"
    with pytest.raises(ConfigError):
        load_config(tmp_path / "missing.yml")
