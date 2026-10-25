#!/usr/bin/env bash
# Gerbang Fase 3: benchmark, ground truth, PoC di Docker, generator mutasi, harness eval, EVAL-PITFALLS.
#
# Ditulis SEBELUM kode apa pun. Dua tahap:
#   TAHAP A: aplikasi benchmark, ground truth + skema, PoC di Docker (jaringan internal), generator mutasi.
#   TAHAP B: metrik (kasus dihitung tangan), `triagent eval`, docs/EVAL-PITFALLS.md.
# Pilih tahap lewat GATE_STAGE=A, GATE_STAGE=B, atau (bawaan) all. Selama tahap B belum dikerjakan,
# bagian B boleh gagal; gerbang final dijalankan dengan all.
#
# Offline untuk LLM dan layanan berbayar (I-10): tidak ada panggilan model, tidak ada semgrep.
# Docker dipakai untuk PoC. Pembuatan image (`npm ci`, sekali, lalu di-cache) memerlukan jaringan
# registry; PoC dan aplikasi benchmark SENDIRI berjalan di jaringan internal tanpa jalan keluar.
#
# Antarmuka yang dikontrakkan oleh gerbang ini (tahap A):
#   triagent benchmark validate --root R [--gt FILE]      kode 0 bila valid; masalah dicetak per baris
#   triagent benchmark mutate --root R --out D --seed N --ops a,b,c
#                                                         D adalah root lengkap (app/, poc/, ground-truth.yaml, mutation.json)
#   triagent benchmark poc --root R [--items ID,ID] --out J.json
#   triagent benchmark selftest --out J.json
# Antarmuka tahap B:
#   triagent eval score --ground-truth GT --findings F.json [--verdicts V.json] --line-tolerance N --out O.json
#   triagent eval run --ground-truth GT --findings F.json --recording REC.json --out-dir D [--line-tolerance N]
set -u
cd "$(dirname "${BASH_SOURCE[0]}")/../.." || exit 1

STAGE="${GATE_STAGE:-all}"
fail=0
ok()  { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fail=1; }
runA() { [ "$STAGE" = "all" ] || [ "$STAGE" = "A" ]; }
runB() { [ "$STAGE" = "all" ] || [ "$STAGE" = "B" ]; }

if [ -n "${PY:-}" ]; then :
elif [ -x .venv/Scripts/python.exe ]; then PY=.venv/Scripts/python.exe
elif [ -x .venv/bin/python ]; then PY=.venv/bin/python
else PY=python; fi
export PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONIOENCODING=utf-8
export TRIAGENT_OFFLINE=1
export MSYS_NO_PATHCONV=1

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
wtmp="$tmp"
command -v cygpath >/dev/null 2>&1 && wtmp="$(cygpath -m "$tmp")"

BM=benchmark
GT=$BM/ground-truth.yaml
SCHEMA=schemas/ground-truth.schema.json
tg() { "$PY" -m triagent "$@"; }

"$PY" -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" \
  && ok "Python >= 3.12" || bad "Python < 3.12 atau interpreter tidak ditemukan ($PY)"
"$PY" -c "import pydantic, typer, yaml, jsonschema, pytest" >/dev/null 2>&1 \
  && ok "dependensi terpasang" || bad "dependensi belum terpasang (pip install -e .[dev])"

# ====================================================================================
# TAHAP A
# ====================================================================================
if runA; then
echo "== TAHAP A =="

# A1. Tes, lint, skema model (skema ground truth ikut diekspor dari model).
"$PY" -m pytest -q -p no:cacheprovider tests/ >"$tmp/pytest.log" 2>&1 \
  && ok "pytest lulus" || { bad "pytest gagal"; tail -n 25 "$tmp/pytest.log"; }
"$PY" -m ruff check src tests >"$tmp/ruff.log" 2>&1 \
  && ok "ruff check bersih" || { bad "ruff check gagal"; tail -n 20 "$tmp/ruff.log"; }
"$PY" -m ruff format --check src tests >"$tmp/fmt.log" 2>&1 \
  && ok "ruff format bersih" || { bad "ruff format gagal"; tail -n 10 "$tmp/fmt.log"; }
tg export-schema --check >/dev/null 2>&1 \
  && ok "skema JSON cocok dengan model (termasuk ground-truth)" || bad "skema JSON tidak cocok dengan model"

# A2. Skema ground truth sebagai JSON Schema sungguhan, divalidasi dengan jsonschema (independen dari pydantic).
[ -f "$SCHEMA" ] && [ -f "$GT" ] && ok "skema dan ground-truth.yaml ada" || bad "hilang: $SCHEMA atau $GT"
"$PY" - "$SCHEMA" "$GT" <<'PYEOF' && ok "ground-truth.yaml valid terhadap skema JSON (jsonschema, Draft 2020-12)" || bad "ground-truth.yaml tidak valid terhadap skema"
import json, sys, yaml
from jsonschema import Draft202012Validator
schema = json.load(open(sys.argv[1], encoding="utf-8"))
Draft202012Validator.check_schema(schema)
doc = yaml.safe_load(open(sys.argv[2], encoding="utf-8"))
errs = sorted(Draft202012Validator(schema).iter_errors(doc), key=lambda e: list(e.path))
for e in errs[:10]:
    print("  ", list(e.path), e.message[:120])
assert not errs
# Skema harus benar-benar menolak: label tak dikenal, field asing, CWE salah format.
def rejects(mut):
    d = yaml.safe_load(open(sys.argv[2], encoding="utf-8"))
    mut(d)
    return bool(list(Draft202012Validator(schema).iter_errors(d)))
assert rejects(lambda d: d["items"][0].__setitem__("label", "maybe"))
assert rejects(lambda d: d["items"][0].__setitem__("verified", True))
assert rejects(lambda d: d["items"][0].__setitem__("cwe", ["79"]))
assert rejects(lambda d: d["items"][0].__setitem__("cwe", []))
assert rejects(lambda d: d["items"][0].__setitem__("start_line", 0))
assert rejects(lambda d: d["items"][0].pop("poc"))
assert rejects(lambda d: d["items"][0].__setitem__("file", "../../etc/passwd"))
assert rejects(lambda d: d.__setitem__("items", []))
PYEOF

# A3. Validator semantik lewat CLI: kontrol positif dan sebelas kontrol negatif.
tg benchmark validate --root "$BM" >"$tmp/val.log" 2>&1 \
  && ok "benchmark validate lulus pada benchmark asli (skema, berkas, baris, jangkar, PoC ada)" \
  || { bad "benchmark validate gagal pada benchmark asli"; tail -n 15 "$tmp/val.log"; }
"$PY" - "$BM" "$wtmp/neg" "$PY" <<'PYEOF' && ok "validator menolak 11 jenis ground truth rusak (dan menerima salinan utuh)" || bad "validator tidak menolak ground truth rusak (lihat pesan)"
import copy, shutil, subprocess, sys
from pathlib import Path
import yaml
bm, work, py = Path(sys.argv[1]), Path(sys.argv[2]), sys.executable
def run(root):
    p = subprocess.run([py, "-m", "triagent", "benchmark", "validate", "--root", str(root)],
                       capture_output=True, text=True, encoding="utf-8")
    assert "Traceback" not in p.stderr + p.stdout, p.stderr[-400:]
    return p.returncode
base = yaml.safe_load((bm / "ground-truth.yaml").read_text(encoding="utf-8"))
def make(name, mut=None, fs=None):
    root = work / name
    shutil.copytree(bm / "app", root / "app", ignore=shutil.ignore_patterns("node_modules"))
    shutil.copytree(bm / "poc", root / "poc")
    d = copy.deepcopy(base)
    if mut:
        mut(d)
    (root / "ground-truth.yaml").write_text(yaml.safe_dump(d, sort_keys=False), encoding="utf-8")
    if fs:
        fs(root)
    return root
def first(d, label):
    return next(i for i in d["items"] if i["label"] == label)
assert run(make("ok")) == 0, "salinan utuh harus lulus"
cases = {
  "label": lambda d: d["items"][0].__setitem__("label", "maybe"),
  "end_before_start": lambda d: d["items"][0].update(start_line=20, end_line=10),
  "dup_id": lambda d: d["items"][1].__setitem__("id", d["items"][0]["id"]),
  "bad_cwe": lambda d: d["items"][0].__setitem__("cwe", ["CWE-0"]),
  "past_eof": lambda d: d["items"][0].update(start_line=99990, end_line=99991),
  "anchor_missing": lambda d: d["items"][0].__setitem__("anchor", "zzz_not_in_code_zzz"),
  "unknown_field": lambda d: d["items"][0].__setitem__("verified", True),
  "trap_without_kind": lambda d: first(d, "fp-trap").__setitem__("trap_kind", None),
  "framing_without_text": lambda d: first(d, "tp").update(comment_framing="safe_claim", framing_text=None),
}
for name, mut in cases.items():
    assert run(make(name, mut)) != 0, f"{name}: ground truth rusak diterima"
def drop_file(root):
    d = yaml.safe_load((root / "ground-truth.yaml").read_text(encoding="utf-8"))
    (root / "app" / d["items"][0]["file"]).unlink()
assert run(make("missing_file", None, drop_file)) != 0, "berkas sumber hilang diterima"
def drop_poc(root):
    d = yaml.safe_load((root / "ground-truth.yaml").read_text(encoding="utf-8"))
    (root / d["items"][0]["poc"]).unlink()
assert run(make("missing_poc", None, drop_poc)) != 0, "berkas PoC hilang diterima"
PYEOF

# A4. Isi benchmark dihitung independen dari validator: cakupan, jebakan, bingkai komentar, peringatan.
"$PY" - "$GT" "$BM" <<'PYEOF' && ok "ground truth: >=12 TP, >=6 jebakan FP, >=8 kategori, >=6 keluarga CWE, bingkai aman dan alarm ada, PoC dan berkas ada" || bad "cakupan ground truth kurang (lihat pesan)"
import sys
from pathlib import Path
import yaml
gt = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
bm = Path(sys.argv[2])
items = gt["items"]
tp = [i for i in items if i["label"] == "tp"]
fp = [i for i in items if i["label"] == "fp-trap"]
assert len(tp) >= 12, f"TP hanya {len(tp)}"
assert len(fp) >= 6, f"jebakan FP hanya {len(fp)}"
cats = {i["category"] for i in items}
assert len(cats) >= 8, cats
tp_cats = {i["category"] for i in tp}
assert len(tp_cats) >= 8, tp_cats
fp_cats = {i["category"] for i in fp}
assert len(fp_cats) >= 5, f"jebakan terlalu seragam: {fp_cats}"
assert len({i["id"] for i in items}) == len(items)
cwes = {c for i in tp for c in i["cwe"]}
assert len(cwes) >= 8, cwes
assert sum(1 for i in tp if i["comment_framing"] == "safe_claim") >= 3, "kurang TP berbingkai aman"
assert sum(1 for i in fp if i["comment_framing"] == "alarm_claim") >= 1, "kurang jebakan berbingkai alarm"
assert {i["trap_kind"] for i in fp} >= {"sanitization", "parameterized", "allowlist"}, {i["trap_kind"] for i in fp}
for i in items:
    assert (bm / "app" / i["file"]).is_file(), i["file"]
    assert (bm / i["poc"]).is_file(), i["poc"]
    assert i["notes"].strip(), "catatan wajib: " + i["id"]
assert gt["label_source"] == "poc"
js = [p for p in (bm / "app").rglob("*.js") if "node_modules" not in p.parts]
loc = sum(len(p.read_text(encoding="utf-8").splitlines()) for p in js)
assert loc >= 400, f"aplikasi terlalu kecil ({loc} baris)"
assert (bm / "app" / "package.json").is_file()
assert not (bm / "app" / "node_modules").exists(), "node_modules tidak boleh ada di repo"
PYEOF
grep -qi 'INTENTIONALLY VULNERABLE' "$BM/README.md" && grep -qiE 'never (run|expose|deploy)' "$BM/README.md" \
  && ok "benchmark/README.md memuat peringatan sengaja rentan dan larangan membuka ke jaringan" \
  || bad "benchmark/README.md tidak memuat peringatan sengaja-rentan"
grep -rqi 'INTENTIONALLY VULNERABLE' "$BM/app/README.md" "$BM/app/server.js" 2>/dev/null \
  && ok "peringatan juga ada di dalam app (server.js atau app/README.md)" || bad "tidak ada peringatan sengaja-rentan di dalam app"
{ grep -rqE "listen\(" "$BM/app/server.js" && ! grep -rE "listen\([^)]*['\"]0\.0\.0\.0['\"]" "$BM/app" --include=*.js >/dev/null; } \
  && ok "app tidak mengikat 0.0.0.0 secara tertulis (host dari env, bawaan loopback atau jaringan kontainer)" || bad "app mengikat 0.0.0.0 secara hardcode atau tidak punya listen"

# A5. Pengerasan compose dibaca dari berkas (statis); perilaku runtime diuji di A6.
"$PY" - "$BM/docker/compose.yaml" <<'PYEOF' && ok "compose: jaringan internal, tanpa port publik, read_only, cap_drop ALL, no-new-privileges, non-root, mount ro, tanpa docker.sock" || bad "compose tidak memenuhi pengerasan (lihat pesan)"
import sys, yaml
c = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
nets = c.get("networks") or {}
assert nets and all(n.get("internal") is True for n in nets.values()), "semua jaringan harus internal: true"
svcs = c["services"]
assert {"app", "poc"} <= set(svcs), list(svcs)
for name, s in svcs.items():
    assert "ports" not in s, f"{name}: port publik"
    assert not s.get("privileged"), f"{name}: privileged"
    assert s.get("network_mode") in (None, "none"), f"{name}: network_mode"
    assert "extra_hosts" not in s, f"{name}: extra_hosts"
    assert s.get("read_only") is True, f"{name}: read_only"
    assert [x.upper() for x in s.get("cap_drop", [])] == ["ALL"], f"{name}: cap_drop"
    assert any("no-new-privileges" in x for x in s.get("security_opt", [])), f"{name}: no-new-privileges"
    u = str(s.get("user", ""))
    assert u and u.split(":")[0] not in ("root", "0"), f"{name}: user {u!r}"
    assert s.get("mem_limit") and s.get("pids_limit") and s.get("cpus"), f"{name}: batas sumber daya"
    for v in s.get("volumes", []):
        vs = v if isinstance(v, str) else v.get("source", "") + ":" + v.get("target", "") + (":ro" if v.get("read_only") else "")
        assert "docker.sock" not in vs, f"{name}: docker.sock"
        assert vs.endswith(":ro") or (isinstance(v, dict) and v.get("read_only")), f"{name}: mount tidak ro: {v}"
    for n in (s.get("networks") or []):
        assert n in nets, f"{name}: jaringan {n} tidak internal/terdefinisi"
PYEOF

# A6. Selftest runtime di DUA kontainer (poc dan app) dengan himpunan kunci yang persis sama (R-03).
# Kunci hilang, kunci isolasi False, atau kontrol positif False berarti gagal. Termasuk: tanpa default route,
# gateway jaringan bench tertutup (22, 80, 2375, 2376, 3000), 172.17.0.1:2375, host.docker.internal dan
# gateway.docker.internal tidak terselesaikan, 169.254.169.254 tertutup, tanpa docker.sock, dan respons 500
# tidak membocorkan err.message (R-04).
tg benchmark selftest --out "$wtmp/selftest.json" >"$tmp/selftest.log" 2>&1; rc=$?
if [ $rc -ne 0 ]; then bad "benchmark selftest gagal (rc=$rc; Docker berjalan?)"; tail -n 15 "$tmp/selftest.log"; else
"$PY" - "$wtmp/selftest.json" <<'PYEOF' && ok "selftest di kontainer poc dan app: himpunan kunci persis, semua isolasi True (egress, DNS, gateway, host, metadata, docker.sock, default route), kontrol positif True, 500 tanpa err.message" || bad "selftest melaporkan isolasi tidak lengkap atau kunci tidak sesuai"
import json, sys
r = json.load(open(sys.argv[1], encoding="utf-8"))
KEYS = {"egress_ip_blocked", "egress_dns_blocked", "non_root", "rootfs_read_only", "source_mount_read_only",
        "no_default_route", "gateway_ports_blocked", "docker_tcp_blocked", "host_dns_blocked",
        "metadata_blocked", "no_docker_sock", "control_reachable", "error_no_leak"}
assert set(r["containers"]) == {"poc", "app"}, list(r["containers"])
for name, res in r["containers"].items():
    assert set(res) == KEYS, f"{name}: selisih kunci {set(res) ^ KEYS}"
    bad_keys = [k for k in KEYS if res[k] is not True]
    assert not bad_keys, f"{name}: tidak True: {bad_keys}"
assert r["network_internal"] is True and r["ok"] is True
PYEOF
fi

# A7. PoC pada aplikasi asli: TP berhasil dieksploitasi, jebakan FP gagal (karena aman), tiap PoC benar-benar mencoba.
tg benchmark poc --root "$BM" --out "$wtmp/poc.json" >"$tmp/poc.log" 2>&1; rc=$?
[ $rc -eq 0 ] && ok "benchmark poc: semua item sesuai label (exit 0)" || { bad "benchmark poc: ada item tidak sesuai atau error harness (rc=$rc)"; tail -n 20 "$tmp/poc.log"; }
"$PY" - "$GT" "$wtmp/poc.json" <<'PYEOF' && ok "hasil PoC independen: tiap TP exploited=true, tiap jebakan exploited=false, semua item dijalankan, attempts>=1 dan bukti tercatat" || bad "hasil PoC tidak sesuai ground truth (lihat pesan)"
import json, sys, yaml
gt = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))["items"]
res = {r["id"]: r for r in json.load(open(sys.argv[2], encoding="utf-8"))["items"]}
assert set(res) == {i["id"] for i in gt}, "item yang dijalankan tidak sama dengan ground truth"
for i in gt:
    r = res[i["id"]]
    want = i["label"] == "tp"
    assert r["exploited"] is want, f'{i["id"]} ({i["label"]}): exploited={r["exploited"]} exit={r.get("exit_code")}'
    assert r["exit_code"] == (0 if want else 1), (i["id"], r["exit_code"])
    assert r.get("attempts", 0) >= 1, f'{i["id"]}: PoC tidak melakukan percobaan'
    assert str(r.get("evidence", "")).strip(), f'{i["id"]}: tanpa bukti/alasan'
PYEOF
# R-07: base image dipin digest dan hasil PoC mencatat digest serta image id.
grep -qE '^FROM node:20-alpine@sha256:[0-9a-f]{64}' "$BM/docker/Dockerfile" \
  && ok "Dockerfile memakai base image dengan digest sha256" || bad "Dockerfile tidak memin base image ke digest"
"$PY" - "$BM/docker/Dockerfile" "$wtmp/poc.json" <<'PYEOF' && ok "hasil PoC memuat base_image_digest (sama dengan Dockerfile) dan image_id" || bad "hasil PoC tidak memuat base_image_digest/image_id yang benar"
import json, re, sys
digest = re.search(r"@(sha256:[0-9a-f]{64})", open(sys.argv[1], encoding="utf-8").read()).group(1)
r = json.load(open(sys.argv[2], encoding="utf-8"))
assert r["base_image_digest"] == digest, r.get("base_image_digest")
assert str(r["image_id"]).startswith("sha256:"), r.get("image_id")
PYEOF
# Kontrol negatif: tambal satu kerentanan di salinan, PoC-nya harus berhenti berhasil.
"$PY" - "$BM" "$wtmp/patched" <<'PYEOF' && ok "kontrol: salinan aplikasi dengan BM-001 ditambal membuat PoC BM-001 gagal" || bad "kontrol: gagal membuat salinan ditambal (string kode berubah?)"
import shutil, sys
from pathlib import Path
bm, out = Path(sys.argv[1]), Path(sys.argv[2])
shutil.copytree(bm / "app", out / "app", ignore=shutil.ignore_patterns("node_modules"))
shutil.copytree(bm / "poc", out / "poc")
shutil.copy(bm / "ground-truth.yaml", out / "ground-truth.yaml")
f = out / "app" / "routes" / "search.js"
src = f.read_text(encoding="utf-8")
old = "'<h1>Results for ' + term +"
assert old in src, "pola kode BM-001 tidak ditemukan"
f.write_text(src.replace(old, "'<h1>Results for ' + String(term).replace(/</g, '&lt;') +", 1), encoding="utf-8")
PYEOF
tg benchmark poc --root "$wtmp/patched" --items BM-001 --out "$wtmp/poc-patched.json" >"$tmp/poc-patched.log" 2>&1
"$PY" - "$wtmp/poc-patched.json" <<'PYEOF' && ok "kontrol: PoC BM-001 melaporkan exploited=false pada kode yang ditambal" || bad "kontrol: PoC BM-001 tetap berhasil pada kode yang ditambal (PoC tidak sensitif)"
import json, sys
r = json.load(open(sys.argv[1], encoding="utf-8"))["items"]
assert len(r) == 1 and r[0]["id"] == "BM-001" and r[0]["exploited"] is False and r[0]["exit_code"] == 1, r
PYEOF

# A8. Generator mutasi: kasus dihitung tangan.
# Cuplikan a.js (13 baris). Hapus komentar: baris komentar-murni dihapus, baris kosong asli dipertahankan,
# komentar di ujung baris dibuang. Pemetaan baris asli -> baru dihitung tangan:
#   1 hapus | 2->1 | 3->2 | 4,5 hapus | 6->3 | 7 hapus | 8->4 | 9->5 | 10->6 | 11->7 | 12->8 | 13->9
# Item: h1 baris 10-10 -> 6-6; h2 baris 8-11 -> 4-7; h3 baris 6-6 -> 3-3.
"$PY" - "$wtmp/hand" <<'PYEOF'
import sys
from pathlib import Path
import yaml
root = Path(sys.argv[1])
(root / "app").mkdir(parents=True); (root / "poc").mkdir()
(root / "app" / "a.js").write_text(
"""// header comment
'use strict';

/* block
   comment */
const total = 1;
// framing: reviewed and safe
function lookup(userInput) { // trailing
  const label = 'lookup: ' + `${userInput}!`;
  return db.query("x" + userInput + label);
}

module.exports = lookup;
""", encoding="utf-8")
def item(n, lines, anchor, label="tp"):
    return {"id": f"BM-00{n}", "title": f"hand {n}", "cwe": [{1: "CWE-89", 2: "CWE-79", 3: "CWE-22"}[n]], "category": "sqli", "label": label,
            "file": "a.js", "start_line": lines[0], "end_line": lines[1], "anchor": anchor,
            "poc": f"poc/BM-00{n}.js", "comment_framing": "none", "framing_text": None,
            "trap_kind": None if label == "tp" else "parameterized", "notes": "hand case"}
for n in (1, 2, 3):
    (root / "poc" / f"BM-00{n}.js").write_text("// dummy\n", encoding="utf-8")
doc = {"schema_version": 1, "app": "hand", "corpus_date": "2026-10-01", "label_source": "poc",
       "labeled_by": "gate", "items": [item(1, (10, 10), "db.query("), item(2, (8, 11), "function"),
                                       item(3, (6, 6), "= 1;")]}
(root / "ground-truth.yaml").write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
PYEOF
tg benchmark validate --root "$wtmp/hand" >"$tmp/hand-val.log" 2>&1 \
  && ok "kasus tangan: ground truth sumber valid" || { bad "kasus tangan: ground truth sumber ditolak"; tail -n 5 "$tmp/hand-val.log"; }
tg benchmark mutate --root "$wtmp/hand" --out "$wtmp/hand-strip" --seed 1 --ops strip-comments >"$tmp/m1.log" 2>&1 \
  && tg benchmark mutate --root "$wtmp/hand" --out "$wtmp/hand-all" --seed 5 --ops rename,strip-comments,style >"$tmp/m2.log" 2>&1 \
  && ok "mutate berjalan pada kasus tangan" || { bad "mutate gagal pada kasus tangan"; tail -n 8 "$tmp/m1.log" "$tmp/m2.log"; }
"$PY" - "$wtmp/hand-strip" "$wtmp/hand-all" <<'PYEOF' && ok "kasus tangan: baris bergeser 10->6, 8-11->4-7, 6->3 persis seperti hitungan; komentar hilang; rename konsisten (termasuk di dalam \${...}), string dan properti utuh; gaya berubah" || bad "kasus tangan mutasi salah (lihat pesan)"
import re, sys
from pathlib import Path
import yaml
for d in sys.argv[1:]:
    gt = yaml.safe_load((Path(d) / "ground-truth.yaml").read_text(encoding="utf-8"))
    by = {i["id"]: (i["start_line"], i["end_line"]) for i in gt["items"]}
    assert by == {"BM-001": (6, 6), "BM-002": (4, 7), "BM-003": (3, 3)}, (d, by)
    assert gt["variant"]["seed"] in (1, 5) and gt["variant"]["base_sha256"]
    src = (Path(d) / "app" / "a.js").read_text(encoding="utf-8")
    lines = src.splitlines()
    assert len(lines) == 9, (d, len(lines), src)
    assert "//" not in src and "/*" not in src, "komentar masih ada"
    assert "db.query(" in lines[5] and "= 1;" in lines[2], lines
    assert "module.exports" in lines[8]
    assert lines[1].strip() == "" and lines[7].strip() == "", "baris kosong asli harus tetap"
s = (Path(sys.argv[1]) / "app" / "a.js").read_text(encoding="utf-8")
assert "function lookup(userInput) {" in s and "const total = 1;" in s, "strip-comments saja tidak boleh mengubah kode"
a = (Path(sys.argv[2]) / "app" / "a.js").read_text(encoding="utf-8")
m = re.search(r"function (\w+)\((\w+)\) \{", a)
assert m, a
fn, prm = m.groups()
assert fn != "lookup" and prm != "userInput", "tidak di-rename"
for old in ("lookup(", "userInput", "total"):
    assert old not in a.replace("'lookup: '", "").replace('"lookup: "', ""), f"{old} masih ada"
assert f"module.exports = {fn};" in a, "ekspor tidak ikut di-rename"
assert re.search(r"\$\{%s\}!" % re.escape(prm), a), "identifier di dalam template tidak di-rename"
assert re.search(r"[\"']lookup: [\"']", a), "teks string ikut berubah"
assert "db.query(" in a, "properti/global ikut berubah"
assert 'use strict' in a and "'use strict'" not in a, "gaya kutip tidak berubah"
assert re.search(r"\blet \w+ = 1;", a) and "const " not in a, "const -> let tidak berlaku"
PYEOF

# A9. Varian mutasi pada aplikasi benchmark: valid, bergeser benar, deterministik, PoC tetap berlaku.
tg benchmark mutate --root "$BM" --out "$wtmp/v1" --seed 1 --ops rename,strip-comments >"$tmp/v1.log" 2>&1 \
  && tg benchmark mutate --root "$BM" --out "$wtmp/v2" --seed 2 --ops rename,strip-comments,style >"$tmp/v2.log" 2>&1 \
  && tg benchmark mutate --root "$BM" --out "$wtmp/v1b" --seed 1 --ops rename,strip-comments >"$tmp/v1b.log" 2>&1 \
  && ok "mutate menghasilkan dua varian dan satu ulangan seed" || { bad "mutate gagal pada benchmark"; tail -n 8 "$tmp/v1.log" "$tmp/v2.log"; }
for v in v1 v2; do
  tg benchmark validate --root "$wtmp/$v" >"$tmp/val-$v.log" 2>&1 \
    && ok "varian $v: ground truth hasil pergeseran valid (skema, baris dalam berkas, jangkar ada di baris baru)" \
    || { bad "varian $v: ground truth hasil mutasi tidak valid"; tail -n 8 "$tmp/val-$v.log"; }
done
"$PY" - "$BM" "$wtmp" <<'PYEOF' && ok "varian: seed sama -> pohon identik, seed beda -> berbeda, kode benar-benar berubah (nama, komentar, gaya), jumlah item sama, metadata varian tercatat" || bad "sifat varian mutasi salah (lihat pesan)"
import hashlib, json, re, sys
from pathlib import Path
import yaml
bm, w = Path(sys.argv[1]), Path(sys.argv[2])
def tree(d):
    return {str(p.relative_to(d)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(d.rglob("*")) if p.is_file()}
assert tree(w / "v1") == tree(w / "v1b"), "seed sama harus identik"
assert tree(w / "v1" / "app") != tree(w / "v2" / "app"), "seed/ops beda harus berbeda"
orig = yaml.safe_load((bm / "ground-truth.yaml").read_text(encoding="utf-8"))
for v in ("v1", "v2"):
    gt = yaml.safe_load((w / v / "ground-truth.yaml").read_text(encoding="utf-8"))
    assert [i["id"] for i in gt["items"]] == [i["id"] for i in orig["items"]]
    assert [i["label"] for i in gt["items"]] == [i["label"] for i in orig["items"]], "label tidak boleh berubah"
    assert [i["cwe"] for i in gt["items"]] == [i["cwe"] for i in orig["items"]]
    assert [i["file"] for i in gt["items"]] == [i["file"] for i in orig["items"]]
    assert gt["variant"]["seed"] in (1, 2) and "strip-comments" in gt["variant"]["ops"]
    mut = json.loads((w / v / "mutation.json").read_text(encoding="utf-8"))
    assert len(mut["renames"]) >= 20, len(mut["renames"])
    assert all(a != b for a, b in mut["renames"].items())
    moved = sum(1 for a, b in zip(orig["items"], gt["items"]) if (a["start_line"], a["end_line"]) != (b["start_line"], b["end_line"]))
    assert moved >= 8, f"hanya {moved} item bergeser; komentar belum terhapus?"
    text = "\n".join(p.read_text(encoding="utf-8") for p in (w / v / "app").rglob("*.js"))
    otext = "\n".join(p.read_text(encoding="utf-8") for p in (bm / "app").rglob("*.js") if "node_modules" not in p.parts)
    assert "escapeHtml" in otext and "escapeHtml" not in text, "escapeHtml harus di-rename di varian"
    assert "assertTicketOwner" in otext and "assertTicketOwner" not in text, "assertTicketOwner harus di-rename"
    assert not re.search(r"^\s*(//|/\*)", text, re.M), "masih ada baris komentar"
    for key in ("express", "child_process", ".query", ".params"):
        assert key in text, f"{key} hilang dari varian"
    for i in gt["items"]:
        if i["comment_framing"] != "none":
            assert i["framing_text"] is None, "teks bingkai harus dikosongkan setelah komentar dihapus"
PYEOF
if command -v node >/dev/null 2>&1; then
  bad_syntax=0
  for v in v1 v2; do
    while IFS= read -r f; do node --check "$(cygpath -m "$f" 2>/dev/null || echo "$f")" >/dev/null 2>&1 || { echo "  sintaks rusak: $f"; bad_syntax=1; }; done < <(find "$tmp/$v/app" -name '*.js' 2>/dev/null | sort -u)
  done
  [ $bad_syntax -eq 0 ] && ok "node --check lulus untuk semua berkas varian" || bad "ada varian dengan sintaks JavaScript rusak"
else
  echo "SKIP: node tidak ada di host; sintaks varian dibuktikan oleh PoC di Docker di bawah"
fi
# Kontrol negatif pergeseran: geser semua baris +7 secara salah, validator harus menolak sebagian besar item.
"$PY" - "$wtmp" "$PY" <<'PYEOF' && ok "validator mendeteksi pergeseran salah (baris +7) pada >=80% item varian" || bad "validator tidak peka terhadap pergeseran salah"
import shutil, subprocess, sys
from pathlib import Path
import yaml
w, py = Path(sys.argv[1]), sys.executable
bad = w / "v1-bad"
shutil.copytree(w / "v1", bad)
gt = yaml.safe_load((bad / "ground-truth.yaml").read_text(encoding="utf-8"))
for i in gt["items"]:
    i["start_line"] += 7; i["end_line"] += 7
(bad / "ground-truth.yaml").write_text(yaml.safe_dump(gt, sort_keys=False), encoding="utf-8")
p = subprocess.run([py, "-m", "triagent", "benchmark", "validate", "--root", str(bad)], capture_output=True, text=True, encoding="utf-8")
assert p.returncode != 0
flagged = {l.split()[0] for l in (p.stdout + p.stderr).splitlines() if l.strip().startswith("BM-")}
assert len(flagged) >= 0.8 * len(gt["items"]), f"hanya {len(flagged)} dari {len(gt['items'])} item ditandai"
PYEOF
for v in v1 v2; do
  tg benchmark poc --root "$wtmp/$v" --out "$wtmp/poc-$v.json" >"$tmp/poc-$v.log" 2>&1; rc=$?
  if [ $rc -eq 0 ]; then
    "$PY" - "$wtmp/poc-$v.json" "$GT" <<'PYEOF' && ok "varian $v: perilaku terjaga, semua TP tetap berhasil dan semua jebakan tetap gagal" || bad "varian $v: hasil PoC berbeda dari label"
import json, sys, yaml
gt = {i["id"]: i["label"] for i in yaml.safe_load(open(sys.argv[2], encoding="utf-8"))["items"]}
res = {r["id"]: r for r in json.load(open(sys.argv[1], encoding="utf-8"))["items"]}
assert set(res) == set(gt)
for k, lab in gt.items():
    assert res[k]["exploited"] is (lab == "tp"), (k, lab, res[k])
PYEOF
  else
    bad "varian $v: benchmark poc gagal (rc=$rc)"; tail -n 12 "$tmp/poc-$v.log"
  fi
done

# A9b. R-01: validator menolak dua item berdekatan (berkas sama, keluarga CWE sama, jarak <= 2 x toleransi + 1 = 5).
"$PY" - "$wtmp/hand" "$wtmp" <<'PYEOF' && ok "R-01: validator menolak dua item berdekatan sekeluarga CWE dan menerima yang jauh atau beda keluarga" || bad "R-01: validator jarak antar item tidak sesuai (lihat pesan)"
import copy, shutil, subprocess, sys
from pathlib import Path
import yaml
hand, work = Path(sys.argv[1]), Path(sys.argv[2])
def run(root):
    p = subprocess.run([sys.executable, "-m", "triagent", "benchmark", "validate", "--root", str(root)],
                       capture_output=True, text=True, encoding="utf-8")
    assert "Traceback" not in p.stdout + p.stderr
    return p.returncode, p.stdout
def variant(name, mut):
    root = work / name
    shutil.copytree(hand, root)
    d = yaml.safe_load((root / "ground-truth.yaml").read_text(encoding="utf-8"))
    mut(d)
    (root / "ground-truth.yaml").write_text(yaml.safe_dump(d, sort_keys=False), encoding="utf-8")
    return root
# Kasus tangan: item 10-10 dan 6-6 di a.js, jarak 10-6 = 4 <= 5. Sekeluarga (CWE-89 dan CWE-89) -> ditolak.
def close(d):
    d["items"][2]["cwe"] = ["CWE-89"]; d["items"][2]["start_line"] = d["items"][2]["end_line"] = 6
    d["items"][2]["anchor"] = "= 1;"
rc, out = run(variant("close", close))
assert rc != 0 and "BM-" in out, out
# Beda keluarga pada jarak yang sama diterima (kasus tangan asli).
assert run(hand)[0] == 0
# Jarak 6 (di luar 2 x 2 + 1 = 5) diterima: item 3 (baris 6) dan item 1 digeser ke baris 12 (jarak 6)
def far(d):
    d["items"][2]["cwe"] = ["CWE-89"]; d["items"][2]["start_line"] = d["items"][2]["end_line"] = 6
    d["items"][2]["anchor"] = "= 1;"
    d["items"][0]["start_line"] = d["items"][0]["end_line"] = 13
    d["items"][0]["anchor"] = "module.exports"
    d["items"][1]["cwe"] = ["CWE-22"]
rc, out = run(variant("far", far))
assert rc == 0, out
PYEOF

# A9c. R-02: nama netral. Kata petunjuk-label (safe, unsafe, trap, vuln, insecure, secure, benign, exploit, fp, tp)
# tidak boleh ada di identifier, literal string, atau nama berkas, pada kode tanpa komentar.
for r in "$BM" "$wtmp/v1" "$wtmp/v2"; do
  tg benchmark check-names --root "$r" >"$tmp/names.log" 2>&1 \
    && ok "R-02: tidak ada petunjuk label pada nama di $(basename "$r")" || { bad "R-02: petunjuk label ditemukan di $r"; tail -n 8 "$tmp/names.log"; }
done
"$PY" - "$wtmp" <<'PYEOF' && ok "R-02: check-names gagal pada /x-safe, trapHandler, isSafeRoute, template, nama berkas, dan lulus pada kode bersih (http bukan tp)" || bad "R-02: check-names tidak peka (lihat pesan)"
import subprocess, sys
from pathlib import Path
w = Path(sys.argv[1])
def case(name, code, fname="a.js"):
    root = w / ("names-" + name)
    (root / "app").mkdir(parents=True)
    (root / "app" / fname).write_text(code, encoding="utf-8")
    p = subprocess.run([sys.executable, "-m", "triagent", "benchmark", "check-names", "--root", str(root)],
                       capture_output=True, text=True, encoding="utf-8")
    assert "Traceback" not in p.stdout + p.stderr, p.stderr
    return p.returncode
assert case("route", "app.get('/x-safe', f);\n") != 0
assert case("ident", "function trapHandler() { return 1; }\n") != 0
assert case("camel", "const isSafeRoute = 1;\n") != 0
assert case("tpl", "const a = `/vuln-${x}`;\n") != 0
assert case("kebab", "go('/fp-case');\n") != 0
assert case("file", "const a = 1;\n", fname="safe-route.js") != 0
assert case("clean", "// this comment may say safe or trap\nconst http = require('http'); go('/jump');\n") == 0
PYEOF

# A9d. R-04: perilaku publik yang tidak dilabel didokumentasikan; handler error tidak membocorkan pesan (diuji di selftest A6).
grep -qi 'public by design' "$BM/app/README.md" && ok "R-04: app/README.md mendokumentasikan GET /notes/:id publik by design" || bad "R-04: app/README.md belum mendokumentasikan rute publik yang tidak dilabel"

# A10. Tidak ada sisa kontainer atau jaringan benchmark setelah semuanya.
left="$(docker ps -aq --filter label=triagent.benchmark=1 2>/dev/null | wc -l | tr -d ' ')"
leftn="$(docker network ls -q --filter label=triagent.benchmark=1 2>/dev/null | wc -l | tr -d ' ')"
{ [ "$left" = "0" ] && [ "$leftn" = "0" ]; } && ok "tidak ada kontainer atau jaringan benchmark tersisa" || bad "sisa benchmark: $left kontainer, $leftn jaringan"

# A11. Kode produk: tanpa shell=True, tanpa klien jaringan; dokumen keputusan tahap A.
if grep -rnE 'shell\s*=\s*True|os\.system\(' src >/dev/null 2>&1; then bad "src memakai shell=True atau os.system"; else ok "src tidak memakai shell=True atau os.system"; fi
if grep -rnE '^\s*(import|from)\s+(socket|requests|httpx|urllib|http\.client|aiohttp)\b' src >/dev/null 2>&1; then bad "src mengimpor modul jaringan"; else ok "src tidak mengimpor modul jaringan"; fi
grep -qE '^\| D-36 ' docs/DESIGN-TRACE.md && grep -qE '^- \*\*A-28\.\*\*' DECISIONS.md \
  && ok "DESIGN-TRACE (D-36...) dan DECISIONS (A-28...) diperbarui" || bad "DESIGN-TRACE atau DECISIONS belum diperbarui untuk tahap A"
[ -f reports/phase-3/dev-report-a.md ] && ok "dev-report-a ada" || bad "reports/phase-3/dev-report-a.md belum ada"
fi  # runA

# ====================================================================================
# TAHAP B  (boleh gagal sampai tahap B dikerjakan)
# ====================================================================================
if runB; then
echo "== TAHAP B =="

# B1. Kasus metrik dihitung tangan.
#
# GT (8 item), temuan (8), toleransi baris T:
#   BM-001 tp  xss  CWE-79  a.js 10-12     f1 CWE-79  a.js 10   likely_tp
#   BM-002 tp  authz CWE-862 a.js 30-32    f2 CWE-863 a.js 31   uncertain   (cocok hanya longgar: 862/863 satu keluarga)
#   BM-003 tp  sqli CWE-89  a.js 50-50     f3 CWE-89  a.js 52   likely_tp   (cocok hanya bila T>=2)
#   BM-004 tp  path CWE-22  b.js 5-8       (tidak ada temuan: scanner meleset)
#   BM-005 trap sqli CWE-89 a.js 70-72     f4 CWE-89  a.js 71   likely_fp
#   BM-006 trap xss CWE-79  b.js 20-22     f5 CWE-79  b.js 21   likely_tp
#   BM-007 trap cmdi CWE-78 b.js 40-40     f6 CWE-78  b.js 40   uncertain
#   BM-008 tp redirect CWE-601 c.js 3-3    f7 CWE-601 c.js 3    likely_fp
#                                           f8 CWE-798 d.js 1    likely_tp   (di luar ground truth, tak terlabel)
# Definisi (R-06): prediksi positif = likely_tp, dan uncertain bila varian "uncertain_positive".
#   item tp:   tidak ada temuan cocok -> fn_missed; ada temuan positif -> tp; semua temuan negatif -> fn_lost
#   item trap: tidak ada temuan cocok -> not_flagged (tidak masuk FP/TN); ada temuan positif -> fp; semua negatif -> tn
#   precision=tp/(tp+fp), recall=tp/(tp+fn_missed+fn_lost), f1=2tp/(2tp+fp+fn), fpr=fp/(fp+tn),
#   tp_retention=tp/(tp+fn_lost) (hanya TP yang terdeteksi scanner); tak terlabel dilaporkan terpisah.
#
# T=2, longgar, uncertain positif : tp=3 (001,002,003) fp=2 (006,007) tn=1 (005) fn_missed=1 (004) fn_lost=1 (008)
#     precision=3/5=0.6 recall=3/5=0.6 f1=6/10=0.6 fpr=2/3 retention=3/4=0.75 ; tak terlabel [f8]
# T=2, longgar, uncertain negatif : 002 jadi fn_lost, 007 jadi tn -> tp=2 fp=1 tn=2 fn=3 (002,004,008)
#     precision=2/3 recall=2/5=0.4 f1=4/8=0.5 fpr=1/3 retention=2/4=0.5
# T=2, ketat,  uncertain positif  : 002 tak cocok (jadi fn_missed, f2 tak terlabel) -> tp=2 fp=2 tn=1 fn=3
#     precision=2/4=0.5 recall=2/5=0.4 f1=4/9=0.4444 fpr=2/3 retention=2/3 (terdeteksi 001,003,008) ; tak terlabel [f2,f8]
# T=2, ketat,  uncertain negatif  : tp=2 fp=1 tn=2 fn=3 -> precision=2/3 recall=0.4 f1=0.5 fpr=1/3 retention=2/3
# T=0, longgar, uncertain positif : 003 tak cocok (f3 di baris 52 vs 50) -> tp=2 (001,002) fp=2 tn=1 fn=3 (003,004,008)
#     precision=0.5 recall=0.4 f1=4/9 fpr=2/3 retention=2/3 (terdeteksi 001,002,008) ; tak terlabel [f3,f8]
# Basis scanner saja (tanpa --verdicts: semua temuan dianggap likely_tp), T=2, longgar:
#     tp=4 (001,002,003,008) fn=1 (004) fp=3 (005,006,007) tn=0 -> precision=4/7 recall=0.8 f1=8/12 fpr=1.0 retention=1.0
# Semua temuan likely_fp, T=2, longgar : tp=0 fp=0 tn=3 fn=5 (4 hilang + 1 meleset)
#     precision=null (0/0) recall=0.0 f1=0.0 fpr=0.0 retention=0.0
# Retensi per kategori (T=2, longgar, uncertain positif; baris = tp_items/detected/retained/rate):
#     xss 1/1/1/1.0, authz 1/1/1/1.0, sqli 1/1/1/1.0, open-redirect 1/1/0/0.0, path-traversal 1/0/0/null
"$PY" - "$wtmp/ev" <<'PYEOF'
import json, subprocess, sys
from pathlib import Path
import yaml
out = Path(sys.argv[1]); out.mkdir(parents=True)
def item(n, cwe, cat, label, f, a, b):
    return {"id": f"BM-00{n}", "title": f"hand {n}", "cwe": [cwe], "category": cat, "label": label, "file": f,
            "start_line": a, "end_line": b, "anchor": "anchor", "poc": f"poc/BM-00{n}.js",
            "comment_framing": "none", "framing_text": None,
            "trap_kind": None if label == "tp" else "allowlist", "notes": "hand case"}
items = [item(1, "CWE-79", "xss", "tp", "a.js", 10, 12), item(2, "CWE-862", "authz", "tp", "a.js", 30, 32),
         item(3, "CWE-89", "sqli", "tp", "a.js", 50, 50), item(4, "CWE-22", "path-traversal", "tp", "b.js", 5, 8),
         item(5, "CWE-89", "sqli", "fp-trap", "a.js", 70, 72), item(6, "CWE-79", "xss", "fp-trap", "b.js", 20, 22),
         item(7, "CWE-78", "command-injection", "fp-trap", "b.js", 40, 40),
         item(8, "CWE-601", "open-redirect", "tp", "c.js", 3, 3)]
doc = {"schema_version": 1, "app": "hand", "corpus_date": "2026-10-01", "label_source": "poc", "labeled_by": "gate", "items": items}
(out / "gt.yaml").write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
F = [("f1", "CWE-79", "a.js", 10, "likely_tp"), ("f2", "CWE-863", "a.js", 31, "uncertain"),
     ("f3", "CWE-89", "a.js", 52, "likely_tp"), ("f4", "CWE-89", "a.js", 71, "likely_fp"),
     ("f5", "CWE-79", "b.js", 21, "likely_tp"), ("f6", "CWE-78", "b.js", 40, "uncertain"),
     ("f7", "CWE-601", "c.js", 3, "likely_fp"), ("f8", "CWE-798", "d.js", 1, "likely_tp")]
rules = [{"id": f"hand.{l}", "properties": {"tags": [f"{c}: x"]}} for l, c, *_ in F]
results = [{"ruleId": f"hand.{l}", "level": "warning", "message": {"text": l},
            "locations": [{"physicalLocation": {"artifactLocation": {"uri": f}, "region": {
                "startLine": n, "endLine": n, "snippet": {"text": f"code-{l}"}}}}]} for l, c, f, n, _ in F]
sarif = {"version": "2.1.0", "runs": [{"tool": {"driver": {"name": "Semgrep OSS", "semanticVersion": "0", "rules": rules}}, "results": results}]}
(out / "hand.sarif").write_text(json.dumps(sarif), encoding="utf-8")
PYEOF
tg ingest "$wtmp/ev/hand.sarif" --out "$wtmp/ev/findings.json" --audit-log "$wtmp/ev/audit.jsonl" >/dev/null 2>&1 \
  && ok "kasus hitung tangan: ingest SARIF sintetis berhasil" || bad "kasus hitung tangan: ingest gagal"
"$PY" - "$wtmp/ev" <<'PYEOF'
import json, sys
from pathlib import Path
d = Path(sys.argv[1])
fs = json.loads((d / "findings.json").read_text(encoding="utf-8"))["findings"]
by = {f["message"]: f["id"] for f in fs}
assert len(by) == 8 and all(f["duplicate_of"] is None for f in fs)
V = {"f1": "likely_tp", "f2": "uncertain", "f3": "likely_tp", "f4": "likely_fp", "f5": "likely_tp",
     "f6": "uncertain", "f7": "likely_fp", "f8": "likely_tp"}
(d / "verdicts.json").write_text(json.dumps({"verdicts": {by[k]: v for k, v in V.items()}}), encoding="utf-8")
(d / "verdicts-allfp.json").write_text(json.dumps({"verdicts": {by[k]: "likely_fp" for k in V}}), encoding="utf-8")
cost = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08]
lat = [100, 200, 300, 400, 500, 600, 700, 800]
meta = {"model_id": "fake-model", "model_snapshot": "fake-2026-01-01", "api_route": "api", "scanner": "semgrep",
        "scanner_version": "1.181.1", "ruleset": "p/javascript", "prompt_hash": "a" * 64, "temperature": 0.0,
        "context_limit_tokens": 8000, "corpus_date": "2026-10-01", "recorded_at": "2026-10-26T00:00:00Z"}
calls = [{"finding_id": by[k], "verdict": V[k], "cost_usd": cost[i], "latency_ms": lat[i], "truncated": i == 7}
         for i, k in enumerate(sorted(V))]
(d / "recording.json").write_text(json.dumps({"meta": meta, "calls": calls}), encoding="utf-8")
bad_meta = dict(meta); bad_meta.pop("model_snapshot")
(d / "recording-nometa.json").write_text(json.dumps({"meta": bad_meta, "calls": calls}), encoding="utf-8")
(d / "recording-missingcall.json").write_text(json.dumps({"meta": meta, "calls": calls[:-1]}), encoding="utf-8")
PYEOF
score() { tg eval score --ground-truth "$wtmp/ev/gt.yaml" --findings "$wtmp/ev/findings.json" --line-tolerance "$1" --out "$2" "${@:3}"; }
score 2 "$wtmp/ev/s-t2.json" --verdicts "$wtmp/ev/verdicts.json" >"$tmp/s1.log" 2>&1 \
  && score 0 "$wtmp/ev/s-t0.json" --verdicts "$wtmp/ev/verdicts.json" >"$tmp/s2.log" 2>&1 \
  && score 2 "$wtmp/ev/s-base.json" >"$tmp/s3.log" 2>&1 \
  && score 2 "$wtmp/ev/s-allfp.json" --verdicts "$wtmp/ev/verdicts-allfp.json" >"$tmp/s4.log" 2>&1 \
  && ok "eval score berjalan (T=2, T=0, basis scanner saja, semua likely_fp)" \
  || { bad "eval score gagal"; tail -n 8 "$tmp/s1.log" "$tmp/s2.log" "$tmp/s3.log" "$tmp/s4.log"; }
"$PY" - "$wtmp/ev" <<'PYEOF' && ok "metrik sama dengan hitungan tangan: 4 varian (ketat/longgar x uncertain positif/negatif), toleransi baris, basis scanner, kasus 0/0 -> null, retensi per kategori" || bad "metrik tidak sama dengan hitungan tangan (lihat pesan)"
import json, sys
from pathlib import Path
d = Path(sys.argv[1])
def L(n): return json.loads((d / n).read_text(encoding="utf-8"))
def close(a, b):
    if b is None:
        return a is None
    return a is not None and abs(a - b) < 1e-9
def chk(res, cwe, unc, want, tag):
    v = res["variants"][cwe][unc]
    for k, w in want.items():
        got = v[k]
        assert close(got, w) if isinstance(w, float) or w is None else got == w, f"{tag} {cwe}/{unc}.{k}: {got} != {w}"
def mk(tp, fp, tn, fn, p, r, f, fpr, ret):
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn, "precision": p, "recall": r, "f1": f, "fpr": fpr, "tp_retention": ret}
s = L("s-t2.json")
chk(s, "cwe_loose", "uncertain_positive", mk(3, 2, 1, 2, 0.6, 0.6, 0.6, 2/3, 0.75), "T2")
chk(s, "cwe_loose", "uncertain_negative", mk(2, 1, 2, 3, 2/3, 0.4, 0.5, 1/3, 0.5), "T2")
chk(s, "cwe_strict", "uncertain_positive", mk(2, 2, 1, 3, 0.5, 0.4, 4/9, 2/3, 2/3), "T2")
chk(s, "cwe_strict", "uncertain_negative", mk(2, 1, 2, 3, 2/3, 0.4, 0.5, 1/3, 2/3), "T2")
assert s["line_tolerance"] == 2
lp = s["variants"]["cwe_loose"]["uncertain_positive"]
oc = {i["id"]: i["outcome"] for i in lp["items"]}
assert oc == {"BM-001": "tp", "BM-002": "tp", "BM-003": "tp", "BM-004": "fn_missed", "BM-005": "tn",
              "BM-006": "fp", "BM-007": "fp", "BM-008": "fn_lost"}, oc
assert len(lp["unlabeled_findings"]) == 1
assert len(s["variants"]["cwe_strict"]["uncertain_positive"]["unlabeled_findings"]) == 2
assert len(s["variants"]["cwe_loose"]["uncertain_positive"]["items"]) == 8
pc = lp["per_category"]
want = {"xss": (1, 1, 1, 1.0), "authz": (1, 1, 1, 1.0), "sqli": (1, 1, 1, 1.0),
        "open-redirect": (1, 1, 0, 0.0), "path-traversal": (1, 0, 0, None)}
assert set(pc) == set(want), set(pc)
for cat, (n, det, ret, rate) in want.items():
    e = pc[cat]
    assert (e["tp_items"], e["detected"], e["retained"]) == (n, det, ret), (cat, e)
    assert close(e["tp_retention"], rate), (cat, e)
t0 = L("s-t0.json")
assert t0["line_tolerance"] == 0
chk(t0, "cwe_loose", "uncertain_positive", mk(2, 2, 1, 3, 0.5, 0.4, 4/9, 2/3, 2/3), "T0")
assert len(t0["variants"]["cwe_loose"]["uncertain_positive"]["unlabeled_findings"]) == 2
b = L("s-base.json")
for unc in ("uncertain_positive", "uncertain_negative"):
    chk(b, "cwe_loose", unc, mk(4, 3, 0, 1, 4/7, 0.8, 8/12, 1.0, 1.0), "base")
z = L("s-allfp.json")
for unc in ("uncertain_positive", "uncertain_negative"):
    chk(z, "cwe_loose", unc, mk(0, 0, 3, 5, None, 0.0, 0.0, 0.0, 0.0), "allfp")
PYEOF
tg eval score --ground-truth "$wtmp/ev/gt.yaml" --findings "$wtmp/ev/findings.json" --line-tolerance 2 --out "$wtmp/ev/x.json" --verdicts "$wtmp/ev/nonexistent.json" >"$tmp/s5.log" 2>&1; rc=$?
{ [ -s "$wtmp/ev/s-t2.json" ] && [ $rc -ne 0 ] && ! grep -q Traceback "$tmp/s5.log"; } && ok "eval score: verdicts hilang ditolak dengan pesan bersih" || bad "eval score: masukan hilang tidak ditangani bersih (rc=$rc)"

# B1b. R-01: pencocokan satu-ke-satu. Satu temuan diberikan ke paling banyak satu item: jarak baris terkecil
# (0 bila bertumpuk), lalu CWE ketat sebelum keluarga, lalu id item terkecil. Hitung tangan (T=2, longgar):
#   GT: X=BM-001 tp CWE-798 c.js 7-7 ; Y=BM-002 trap CWE-798 c.js 8-8 (berdekatan, hanya untuk uji metrik)
#   a) temuan baris 8, likely_fp : jarak Y=0, X=1 -> Y. Y=tn, X=fn_missed. tp0 fp0 tn1 fn1.
#   b) temuan baris 7, likely_tp : jarak X=0, Y=1 -> X. X=tp, Y=not_flagged. tp1 fp0 tn0 fn0.
#   c) temuan 7-8, likely_tp     : jarak 0 dan 0, CWE sama -> id terkecil BM-001. X=tp, Y=not_flagged (urutan GT dibalik: sama).
#   d) P=BM-001 tp CWE-863 a.js 10 ; Q=BM-002 trap CWE-862 a.js 10 ; temuan CWE-862 baris 10 likely_tp:
#      jarak 0 dan 0, kecocokan ketat dengan Q, hanya keluarga dengan P -> Q. Q=fp, P=fn_missed.
"$PY" - "$wtmp/oto" <<'PYEOF' && ok "R-01: pencocokan satu-ke-satu sesuai hitungan tangan (jarak, lalu ketat, lalu id; urutan GT tidak berpengaruh)" || bad "R-01: pencocokan satu-ke-satu salah (lihat pesan)"
import json, subprocess, sys
from pathlib import Path
import yaml
out = Path(sys.argv[1]); out.mkdir(parents=True)
def tg(*a):
    p = subprocess.run([sys.executable, "-m", "triagent", *a], capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0, (a, p.stderr[-300:])
def item(n, cwe, cat, label, f, a, b):
    return {"id": f"BM-00{n}", "title": f"oto {n}", "cwe": [cwe], "category": cat, "label": label, "file": f,
            "start_line": a, "end_line": b, "anchor": "anchor", "poc": f"poc/BM-00{n}.js",
            "comment_framing": "none", "framing_text": None,
            "trap_kind": None if label == "tp" else "placeholder", "notes": "oto"}
def gt(name, items):
    d = {"schema_version": 1, "app": "oto", "corpus_date": "2026-10-01", "label_source": "poc", "labeled_by": "gate", "items": items}
    p = out / f"{name}.yaml"; p.write_text(yaml.safe_dump(d, sort_keys=False), encoding="utf-8"); return p
def findings(name, cwe, f, a, b):
    res = [{"ruleId": "oto.r", "level": "warning", "message": {"text": "oto"},
            "locations": [{"physicalLocation": {"artifactLocation": {"uri": f}, "region": {"startLine": a, "endLine": b, "snippet": {"text": "code"}}}}]}]
    sarif = {"version": "2.1.0", "runs": [{"tool": {"driver": {"name": "Semgrep OSS", "semanticVersion": "0",
             "rules": [{"id": "oto.r", "properties": {"tags": [f"{cwe}: x"]}}]}}, "results": res}]}
    (out / f"{name}.sarif").write_text(json.dumps(sarif), encoding="utf-8")
    tg("ingest", str(out / f"{name}.sarif"), "--out", str(out / f"{name}.json"), "--audit-log", str(out / f"{name}.audit"))
    fid = json.loads((out / f"{name}.json").read_text(encoding="utf-8"))["findings"][0]["id"]
    return out / f"{name}.json", fid
def score(gtp, fp, fid, verdict, name):
    vp = out / f"{name}.v.json"; vp.write_text(json.dumps({"verdicts": {fid: verdict}}), encoding="utf-8")
    op = out / f"{name}.out.json"
    tg("eval", "score", "--ground-truth", str(gtp), "--findings", str(fp), "--verdicts", str(vp), "--line-tolerance", "2", "--out", str(op))
    v = json.loads(op.read_text(encoding="utf-8"))["variants"]["cwe_loose"]["uncertain_positive"]
    return v, {i["id"]: i["outcome"] for i in v["items"]}
X = item(1, "CWE-798", "hardcoded-secret", "tp", "c.js", 7, 7)
Y = item(2, "CWE-798", "hardcoded-secret", "fp-trap", "c.js", 8, 8)
g = gt("xy", [X, Y]); g_rev = gt("yx", [Y, X])
fa, ida = findings("a", "CWE-798", "c.js", 8, 8)
v, oc = score(g, fa, ida, "likely_fp", "a")
assert oc == {"BM-001": "fn_missed", "BM-002": "tn"} and (v["tp"], v["fp"], v["tn"], v["fn"]) == (0, 0, 1, 1), oc
assert v["matched_findings_total"] == 1
fb, idb = findings("b", "CWE-798", "c.js", 7, 7)
v, oc = score(g, fb, idb, "likely_tp", "b")
assert oc == {"BM-001": "tp", "BM-002": "not_flagged"} and (v["tp"], v["fp"], v["tn"], v["fn"]) == (1, 0, 0, 0), oc
fc, idc = findings("c", "CWE-798", "c.js", 7, 8)
for gp, name in ((g, "c1"), (g_rev, "c2")):
    v, oc = score(gp, fc, idc, "likely_tp", name)
    assert oc == {"BM-001": "tp", "BM-002": "not_flagged"}, (name, oc)
P = item(1, "CWE-863", "authz", "tp", "a.js", 10, 10)
Q = item(2, "CWE-862", "authz", "fp-trap", "a.js", 10, 10)
gd = gt("pq", [P, Q])
fd, idd = findings("d", "CWE-862", "a.js", 10, 10)
v, oc = score(gd, fd, idd, "likely_tp", "d")
assert oc == {"BM-001": "fn_missed", "BM-002": "fp"}, oc
PYEOF

# B1c. R-05: --strip-prefix (boleh berulang), temuan duplicate_of dilewati, peringatan bila nol cocok.
#   Semua path temuan diberi awalan benchmark/app/ dan ditambah satu duplikat dari f1 (verdict tidak diberikan).
#   Dengan --strip-prefix benchmark/app/ hasil sama dengan hitungan tangan B1 (T=2 longgar uncertain positif:
#   tp3 fp2 tn1 fn2, tak terlabel [f8]); duplicates_skipped=1; temuan cocok = f1..f7 = 7.
#   Tanpa strip: nol cocok -> peringatan di stderr, tp0 dan semua TP fn_missed.
"$PY" - "$wtmp/ev" <<'PYEOF' && ok "R-05: strip-prefix (berulang), duplikat dilewati (tidak menambah tp/fp/unlabeled), matched_findings_total, peringatan nol-cocok" || bad "R-05: strip-prefix/duplikat/peringatan tidak sesuai (lihat pesan)"
import json, subprocess, sys
from pathlib import Path
d = Path(sys.argv[1])
doc = json.loads((d / "findings.json").read_text(encoding="utf-8"))
fs = doc["findings"]
for f in fs:
    f["location"]["file"] = "benchmark/app/" + f["location"]["file"]
dup = json.loads(json.dumps(fs[0])); dup["id"] = "f-dup-0000000000000000000001"; dup["duplicate_of"] = fs[0]["id"]
doc["findings"] = fs + [dup]
(d / "findings-prefixed.json").write_text(json.dumps(doc), encoding="utf-8")
def score(*extra):
    p = subprocess.run([sys.executable, "-m", "triagent", "eval", "score", "--ground-truth", str(d / "gt.yaml"),
                        "--findings", str(d / "findings-prefixed.json"), "--verdicts", str(d / "verdicts.json"),
                        "--line-tolerance", "2", "--out", str(d / "pfx.json"), *extra],
                       capture_output=True, text=True, encoding="utf-8")
    assert "Traceback" not in p.stderr, p.stderr[-300:]
    return p
p = score("--strip-prefix", "nomatch/", "--strip-prefix", "benchmark/app/")
assert p.returncode == 0, p.stderr
r = json.loads((d / "pfx.json").read_text(encoding="utf-8"))
v = r["variants"]["cwe_loose"]["uncertain_positive"]
assert (v["tp"], v["fp"], v["tn"], v["fn"]) == (3, 2, 1, 2), v
assert len(v["unlabeled_findings"]) == 1 and v["matched_findings_total"] == 7, (v["unlabeled_findings"], v["matched_findings_total"])
assert r["duplicates_skipped"] == 1 and "f-dup-0000000000000000000001" not in json.dumps(v)
assert "warning" not in p.stderr.lower(), p.stderr
p = score()
assert p.returncode == 0
r = json.loads((d / "pfx.json").read_text(encoding="utf-8"))
v = r["variants"]["cwe_loose"]["uncertain_positive"]
assert v["matched_findings_total"] == 0 and v["tp"] == 0 and v["fn_missed"] == 5, v
assert "warning" in p.stderr.lower() and r["warnings"], p.stderr
PYEOF

# B1d. R-06: metadata rekaman memakai daftar putih; kunci lain dibuang dan hanya namanya dicatat.
"$PY" - "$wtmp/ev" <<'PYEOF' && ok "R-06: kunci liar di meta (api_key, home_path) tidak masuk report.json; hanya nama di dropped_meta_keys; recorded_at (opsional) tetap" || bad "R-06: daftar putih meta tidak bekerja (lihat pesan)"
import json, subprocess, sys
from pathlib import Path
d = Path(sys.argv[1])
rec = json.loads((d / "recording.json").read_text(encoding="utf-8"))
rec["meta"]["api_key"] = "sk-test-LEAKVALUE-0001"
rec["meta"]["home_path"] = "C:/Users/someone/private"
(d / "recording-extra.json").write_text(json.dumps(rec), encoding="utf-8")
p = subprocess.run([sys.executable, "-m", "triagent", "eval", "run", "--ground-truth", str(d / "gt.yaml"),
                    "--findings", str(d / "findings.json"), "--recording", str(d / "recording-extra.json"),
                    "--out-dir", str(d / "run-extra"), "--line-tolerance", "2"], capture_output=True, text=True, encoding="utf-8")
assert p.returncode == 0, p.stderr
text = (d / "run-extra" / "report.json").read_text(encoding="utf-8")
md = (d / "run-extra" / "report.md").read_text(encoding="utf-8")
for leak in ("sk-test-LEAKVALUE-0001", "C:/Users/someone/private"):
    assert leak not in text and leak not in md and leak not in p.stdout + p.stderr, leak
m = json.loads(text)["metadata"]
assert "api_key" not in m and "home_path" not in m
assert m["dropped_meta_keys"] == ["api_key", "home_path"], m["dropped_meta_keys"]
assert m["recorded_at"] == "2026-10-26T00:00:00Z"
PYEOF

# B2. triagent eval run dengan mode rekaman: metadata, biaya, latensi, deterministik, offline, tolak rekaman tak lengkap.
runeval() { tg eval run --ground-truth "$wtmp/ev/gt.yaml" --findings "$wtmp/ev/findings.json" --recording "$1" --out-dir "$2" --line-tolerance 2; }
runeval "$wtmp/ev/recording.json" "$wtmp/ev/run1" >"$tmp/r1.log" 2>&1 && runeval "$wtmp/ev/recording.json" "$wtmp/ev/run2" >"$tmp/r2.log" 2>&1 \
  && ok "eval run (rekaman) berjalan offline dua kali" || { bad "eval run gagal"; tail -n 8 "$tmp/r1.log"; }
"$PY" - "$wtmp/ev" <<'PYEOF' && ok "laporan eval: metadata run lengkap, biaya dan latensi = jumlah rekaman, hasil = hitungan tangan, tabel per item, dua run byte-identik" || bad "laporan eval tidak sesuai (lihat pesan)"
import json, sys
from pathlib import Path
d = Path(sys.argv[1])
r1 = (d / "run1" / "report.json").read_bytes(); r2 = (d / "run2" / "report.json").read_bytes()
assert r1 == r2, "laporan tidak deterministik"
rep = json.loads(r1)
m = rep["metadata"]
for k in ("model_id", "model_snapshot", "api_route", "scanner", "scanner_version", "ruleset", "prompt_hash",
          "temperature", "context_limit_tokens", "corpus_date", "label_source", "ground_truth_sha256",
          "triagent_version", "mode", "line_tolerance", "context_truncated_calls"):
    assert k in m, f"metadata kehilangan {k}"
assert m["mode"] == "recorded" and m["label_source"] == "poc" and m["line_tolerance"] == 2
assert m["dropped_meta_keys"] == [], m["dropped_meta_keys"]
assert m["context_truncated_calls"] == 1 and len(m["ground_truth_sha256"]) == 64 and len(m["prompt_hash"]) == 64
assert abs(rep["cost"]["usd_total"] - 0.36) < 1e-9 and rep["cost"]["calls"] == 8
assert rep["latency"]["ms_total"] == 3600 and abs(rep["latency"]["ms_mean"] - 450.0) < 1e-9
v = rep["results"]["variants"]["cwe_loose"]["uncertain_positive"]
assert (v["tp"], v["fp"], v["tn"], v["fn"]) == (3, 2, 1, 2) and abs(v["tp_retention"] - 0.75) < 1e-9
md = (d / "run1" / "report.md").read_text(encoding="utf-8")
for n in range(1, 9):
    assert f"BM-00{n}" in md, f"tabel per item tidak memuat BM-00{n}"
for h in ("precision", "recall", "FPR", "retention"):
    assert h.lower() in md.lower(), h
PYEOF
for bad_rec in nometa missingcall; do
  runeval "$wtmp/ev/recording-$bad_rec.json" "$wtmp/ev/run-$bad_rec" >"$tmp/r-$bad_rec.log" 2>&1; rc=$?
  { [ -s "$wtmp/ev/run1/report.json" ] && [ $rc -ne 0 ] && ! grep -q Traceback "$tmp/r-$bad_rec.log"; } \
    && ok "eval run menolak rekaman '$bad_rec' dengan pesan bersih (P9/I-06: tanpa snapshot atau panggilan hilang tidak boleh lolos)" \
    || bad "eval run menerima rekaman '$bad_rec' atau melempar traceback (rc=$rc)"
done
if grep -rnE '^\s*(import|from)\s+(socket|requests|httpx|urllib|http\.client|aiohttp|openai|anthropic)\b' src/triagent/eval* src/triagent/benchmark 2>/dev/null | grep -v 'subprocess' >/dev/null; then
  bad "modul eval/benchmark mengimpor klien jaringan atau SDK LLM"
else ok "modul eval/benchmark tidak mengimpor klien jaringan atau SDK LLM (tes tanpa panggilan berbayar)"; fi
ls tests/test_eval*.py >/dev/null 2>&1 && ok "ada tes pytest untuk eval" || bad "tests/test_eval*.py belum ada"

# B3. docs/EVAL-PITFALLS.md: P1..P9 dengan definisi dari catatan chasing-shadows-2026, bukan dari ingatan.
"$PY" - docs/EVAL-PITFALLS.md <<'PYEOF' && ok "EVAL-PITFALLS.md: P1 sampai P9 dengan definisi benar, metadata run, definisi R-06, tanpa em dash" || bad "EVAL-PITFALLS.md tidak lengkap atau definisinya salah (lihat pesan)"
import re, sys
t = open(sys.argv[1], encoding="utf-8").read()
assert "—" not in t, "ada em dash"
parts = re.split(r"(?m)^#{2,4}\s+(P[1-9])\b", t)
sec = {parts[i]: parts[i + 1].lower() for i in range(1, len(parts) - 1, 2)}
assert set(sec) == {f"P{n}" for n in range(1, 10)}, sorted(sec)
need = {
  "P1": ["scraping", "racun"],
  "P2": ["label", "llm", "validasi"],
  "P3": ["kebocoran", "data latih"],
  "P4": ["model collapse", "sintetis"],
  "P5": ["korelasi palsu", "nama variabel"],
  "P6": ["pemotongan konteks"],
  "P7": ["sensitivitas prompt", "variasi"],
  "P8": ["proksi", "tidak diuji"],
  "P9": ["ambiguitas model", "snapshot", "api"],
}
for p, words in need.items():
    for w in words:
        assert w in sec[p], f"{p} tidak memuat '{w}'"
    assert len(sec[p].strip()) > 150, f"{p} terlalu singkat"
low = t.lower()
for w in ("tp retention", "uncertain", "likely_tp", "ketat", "longgar", "toleransi baris", "tidak terlabel",
          "model_snapshot", "prompt_hash", "sumber label", "mutasi", "chasing-shadows-2026"):
    assert w in low, f"dokumen tidak membahas '{w}'"
# Definisi keliru yang tertulis di catatan seed harus tidak muncul sebagai definisi P8/P9.
assert "klaim berlebihan" not in sec["P8"].split("\n")[0], "P8 salah definisi"
assert "model preview" not in sec["P9"].split("\n")[0], "P9 salah definisi"
PYEOF

grep -qE '^\| D-4[0-9] ' docs/DESIGN-TRACE.md && grep -qE '^- \*\*A-29\.\*\*' DECISIONS.md \
  && ok "DESIGN-TRACE dan DECISIONS memuat keputusan metrik tahap B" || bad "DESIGN-TRACE/DECISIONS belum memuat keputusan metrik tahap B"
grep -q 'satu-ke-satu' DECISIONS.md && grep -q 'satu-ke-satu' docs/EVAL-PITFALLS.md && grep -q 'satu-ke-satu' docs/DESIGN-TRACE.md \
  && ok "aturan pencocokan satu-ke-satu tercatat di A-29, D-42, dan EVAL-PITFALLS" || bad "aturan satu-ke-satu belum tercatat di DECISIONS, DESIGN-TRACE, dan EVAL-PITFALLS"
grep -qi 'string literal' benchmark/mutate/README.md && ok "benchmark/mutate/README.md mencatat batas rename (properti, kunci objek, literal string)" || bad "benchmark/mutate/README.md belum mencatat batas rename"
! grep -q 'belum ada kasus nyata' reports/phase-3/dev-report-b.md && ok "klaim keliru 'belum ada kasus nyata' sudah dikoreksi di dev-report-b.md" || bad "dev-report-b.md masih memuat klaim keliru 'belum ada kasus nyata'"
[ -f reports/phase-3/dev-report-b.md ] && ok "dev-report-b ada" || bad "reports/phase-3/dev-report-b.md belum ada"
fi  # runB

[ "$fail" -eq 0 ] && exit 0
exit 1
