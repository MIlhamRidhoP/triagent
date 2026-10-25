# fieldnotes-bench

INTENTIONALLY VULNERABLE application. It exists only as a measuring instrument for triagent.
Never run it on an open network, never deploy it, never point real data at it. The only
supported way to run it is through `triagent benchmark poc`, which starts it in a hardened
container on an internal network without egress. See `../README.md`.

## Behaviour that is public by design and not labelled

`GET /notes/:id` needs no login and does no ownership check. Notes are meant to be shared, and that is what makes the stored XSS item (BM-002) reachable. It is not a labelled weakness; a scanner finding on it lands in `unlabeled_findings`. Error responses with status 500 return a generic message (`internal error`), so internal messages do not leak.
