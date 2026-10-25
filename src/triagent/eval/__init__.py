"""Evaluation harness: triage metrics and recorded runs (offline, I-10)."""

from __future__ import annotations

from triagent.eval.metrics import EvalError, score
from triagent.eval.run import run_recorded

__all__ = ["EvalError", "run_recorded", "score"]
