# Mutation generator

Code: `src/triagent/benchmark/mutate.py` and `jsmini.py`. CLI: `triagent benchmark mutate`.

```
triagent benchmark mutate --out DIR --seed N --ops rename,strip-comments,style
```

`DIR` becomes a complete benchmark root (`app/`, `poc/`, `ground-truth.yaml`, `mutation.json`).

| Operation | Effect |
|---|---|
| `strip-comments` | removes all comments, including the safe and alarm framing comments; lines that held only comments are deleted, so ground truth lines shift |
| `rename` | new random names for declared functions, variables and parameters, the same in every file; names used as properties, methods or in shorthand positions are left alone |
| `style` | double quotes, `let` instead of `const`, indentation doubled (even seed) or tabs (odd seed) |

The ground truth of the variant keeps ids, labels, CWE lists and files. Lines are mapped through
the comment removal. `framing_text` becomes `null` when comments are stripped. A `variant` block
records the SHA-256 of the base ground truth, the seed and the operations.

A variant is accepted in three steps: `triagent benchmark validate --root DIR` (the `anchor`
text must still be in the shifted lines), `node --check` on the sources, and
`triagent benchmark poc --root DIR` (every true positive still exploitable, every trap still
safe). The same seed and operations always produce a byte-identical variant.

Why: model results on the original may come from memorized text or from names and comments
(pitfalls P3 and P5). Comparing triage on the original and on variants shows how much of a result
depends on those surface features. This test is an engineering decision, not taken from a paper.

## Limits of rename

Rename changes declared identifiers only. It does not touch properties, object keys, method names or string literals (route paths, messages), so those must be written without label hints. `triagent benchmark check-names` enforces that on the original and on every variant.
