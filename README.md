# triagent

Turn noisy SAST alerts into triaged, evidence-backed findings with tested fixes, inside your CI/CD pipeline.

> Status: early development. The specification and build plan are in [`SPEC.md`](SPEC.md) and [`PLAN.md`](PLAN.md).

## Why

Static analysis tools report many alerts, most of them noise, and none of them answer the questions a developer actually has: can this be exploited, through which path, and how do I fix it. triagent sits next to your scanner and answers those questions. The LLM augments the scanner. It does not replace it, and it never silently drops a finding.

## How it works

```
scanner (SARIF) -> normalize/dedup -> context slice + redaction
  -> multi-model triage -> sandbox verification -> tested patch proposal
  -> PR comments, SARIF, dashboard
```

Design principles:

- **Findings are never deleted automatically.** Model verdicts are annotations. Only a human or an explicit, logged rule can suppress.
- **The LLM proposes, evidence decides.** "Verified" comes from executing a proof of concept in an isolated sandbox, not from a model's opinion.
- **Measured, not assumed.** A reproducible benchmark with PoC-verified ground truth reports precision, recall, F1, false positive rate, true positive retention per category, cost and latency.
- **Untrusted input.** Analyzed code is data. Context is redacted before it reaches a model.

## Roadmap

See [`PLAN.md`](PLAN.md) for the phased plan (ingest, benchmark, multi-model triage, context slicing, GitHub Action, sandbox verification, automated fixes, dashboard, hardening).

## Development

Prerequisites: Git, `jq`, Python 3.12, Node.js (for the benchmark app), Docker (from the sandbox phase onward). On Windows use Git Bash or WSL.

```bash
git clone https://github.com/MIlhamRidhoP/triagent.git
cd triagent
bash scripts/setup.sh          # git hooks, permissions, identity check
bash scripts/install-guard.sh  # optional: weekly quota guard for Claude Code
bash scripts/guard-selftest.sh
```

Contributor and agent workflow rules are in [`CLAUDE.md`](CLAUDE.md).

## Literature

Design decisions trace back to published work, summarized in [`docs/literature/`](docs/literature/INDEX.md) (the PDFs themselves are not distributed) and mapped in [`docs/DESIGN-TRACE.md`](docs/DESIGN-TRACE.md).

## License

Not chosen yet. Until a license is added, all rights are reserved.
