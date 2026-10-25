# triagent benchmark

> **INTENTIONALLY VULNERABLE.** `benchmark/app` is a deliberately insecure Node.js (Express)
> application. Never run it on an open network, never expose or deploy it, never put real data or
> real credentials near it. The only supported way to run it is `triagent benchmark poc`, which
> starts it in hardened containers on an internal Docker network with no way out.

This directory is the measuring instrument for triagent's triage (resolution R-06: v1 measures
triage of scanner findings). It is a new application written for this project, not a well known
vulnerable app, so it is unlikely to be in any model's training data (D-15, pitfall P3).

## Contents

| Path | What |
|---|---|
| `app/` | `fieldnotes-bench`, a small notes and tickets service with planted weaknesses and false positive traps |
| `ground-truth.yaml` | one entry per planted weakness or trap: CWE list, file, lines, category, label, PoC |
| `../schemas/ground-truth.schema.json` | JSON Schema of the ground truth (generated from the pydantic model) |
| `poc/` | one script per item, run inside Docker against the app |
| `docker/` | image (dependencies only) and `compose.yaml` (internal network, hardened containers) |
| `mutate/` | notes on the mutation generator (code lives in `src/triagent/benchmark/`) |

## Labels come from PoCs

`label: tp` means the PoC script exploits the weakness (exit code 0). `label: fp-trap` means the
code looks dangerous to a scanner but is safe: the PoC makes a real attempt and fails (exit code
1). Anything else is a harness error. Labels are not produced by an LLM (pitfall P2). Some
true positives carry a comment that claims the code is safe, and one trap carries a comment that
claims it is dangerous (`comment_framing`); these test whether a triager is swayed by framing
(I-03). `anchor` is a piece of text (a property name or a string) that must stay in the item's
lines; it lets the validator prove that a mutated variant's shifted lines still cover the sink.

## Commands

```
triagent benchmark validate                       # schema, files, lines, anchors, PoC scripts
triagent benchmark selftest --out selftest.json   # isolation checked from inside the container
triagent benchmark poc --out poc.json             # all PoCs; --items BM-001,BM-014 to select
triagent benchmark mutate --out /tmp/variant --seed 1 --ops rename,strip-comments,style
triagent benchmark poc --root /tmp/variant --out poc-variant.json
```

The first run builds the image `triagent-bench-app:<hash>` once (`npm ci` from the lock file, the
only step that needs the network). After that nothing needs a network.

## Isolation

- One `internal: true` Docker network, no published ports, no host mounts except read-only copies
  of the app source and the PoC scripts.
- Every container runs as a non-root user with a read-only root filesystem, all capabilities
  dropped, `no-new-privileges`, and CPU, memory and PID limits.
- The app refuses to start unless `BENCHMARK_SANDBOX=1`, which only `compose.yaml` sets.
- PoCs only talk to the benchmark app (and the stand-in internal service for the SSRF items).
  They never touch the host.
- The self-test runs inside both the PoC and the app container (where the RCE items run) and checks 13 keys: no default route, public IPs and DNS blocked, the network gateway (ports 22, 80, 2375, 2376, 3000), 172.17.0.1:2375, `host.docker.internal`, the metadata address and `docker.sock` all unreachable or absent, read-only filesystems, non-root, 500 responses without internal messages, plus a positive control that the app is reachable.
- The base image is pinned by digest; the PoC result records `base_image_digest` and `image_id`.

## Names that must not reveal labels

`triagent benchmark check-names` fails when an identifier, a string literal or a file name (in code with comments removed) contains a word such as safe, trap, vuln, secure, benign, exploit, fp or tp. It runs on the app and on every mutated variant. The only exception is the refusal message in `app/server.js`. Property names such as `html.escape` or `authz.owner` are allowed: they are normal code semantics, not label hints.

## Limits

- The ground truth is written by the project, so it can be incomplete. Findings that match no item
  are reported separately by the evaluation harness, never counted as false positives.
- The toy SQL engine (`app/lib/minisql.js`) stands in for a database. It is enough to show real
  injection and real parameter binding, but scanner rules written for specific database drivers
  may not fire on it.
- The prototype pollution items point at the merge function (`lib/merge.js`); a scanner may flag
  the call site in `routes/profile.js` instead, which would count as a miss at line level.
