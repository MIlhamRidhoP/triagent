#!/usr/bin/env bash
# Gerbang Fase 1: kerangka, skema, CLI, audit log. Memeriksa perilaku, bukan hanya berkas.
# Offline: tidak ada jaringan, tidak ada panggilan LLM.
set -u
cd "$(dirname "${BASH_SOURCE[0]}")/../.." || exit 1

fail=0
ok()  { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fail=1; }

# Pilih interpreter: PY dari lingkungan, lalu .venv, lalu python di PATH.
if [ -n "${PY:-}" ]; then :
elif [ -x .venv/Scripts/python.exe ]; then PY=.venv/Scripts/python.exe
elif [ -x .venv/bin/python ]; then PY=.venv/bin/python
else PY=python; fi
export PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONIOENCODING=utf-8
export TRIAGENT_OFFLINE=1

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
wtmp="$tmp"
command -v cygpath >/dev/null 2>&1 && wtmp="$(cygpath -m "$tmp")"

# 1. Interpreter dan dependensi.
"$PY" -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" \
  && ok "Python >= 3.12" || bad "Python < 3.12 atau interpreter tidak ditemukan ($PY)"
"$PY" -c "import pydantic, typer, yaml, jsonschema, pytest" >/dev/null 2>&1 \
  && ok "dependensi terpasang" || bad "dependensi belum terpasang (pip install -e .[dev])"

# 2. pyproject dan CI.
grep -qE '^requires-python *= *">=3\.12"' pyproject.toml \
  && ok "pyproject: requires-python >=3.12" || bad "pyproject: requires-python >=3.12 tidak ada"
grep -q 'triagent.cli:app' pyproject.toml && ok "pyproject: entry point triagent" || bad "pyproject: entry point hilang"
ci=.github/workflows/ci.yml
grep -q 'check-hygiene.sh' "$ci" && grep -qE 'ruff (check|format)' "$ci" && grep -q 'pytest' "$ci" \
  && grep -q '"3.12"' "$ci" && grep -q '"3.13"' "$ci" \
  && ok "CI: hygiene, ruff, pytest, matriks 3.12 dan 3.13" || bad "CI belum lengkap (hygiene, ruff, pytest, matriks 3.12/3.13)"

# 3. Tes dan lint.
"$PY" -m pytest -q -p no:cacheprovider tests/ >"$tmp/pytest.log" 2>&1 \
  && ok "pytest lulus" || { bad "pytest gagal"; tail -n 20 "$tmp/pytest.log"; }
"$PY" -m ruff check src tests >"$tmp/ruff.log" 2>&1 \
  && ok "ruff check bersih" || { bad "ruff check gagal"; tail -n 20 "$tmp/ruff.log"; }
"$PY" -m ruff format --check src tests >"$tmp/fmt.log" 2>&1 \
  && ok "ruff format bersih" || { bad "ruff format gagal"; tail -n 10 "$tmp/fmt.log"; }

# 4. Tes invarian I-01 dan I-02 ada, cukup banyak, dan lulus.
n="$("$PY" -m pytest --collect-only -q -p no:cacheprovider tests/test_invariants.py 2>/dev/null | grep -c '::')"
[ "${n:-0}" -ge 28 ] && ok "tes invarian terkumpul ($n)" || bad "tes invarian kurang dari 28 (ditemukan: ${n:-0})"
"$PY" -m pytest -q -p no:cacheprovider tests/test_invariants.py >/dev/null 2>&1 \
  && ok "tes invarian I-01 dan I-02 lulus" || bad "tes invarian gagal"

# 4b. Serangan mandiri (tidak bergantung berkas tes): penugasan, construct, copy, tampering, actor.
cat > "$tmp/attack.py" <<'PYEOF'
import sys, tempfile, os
from datetime import UTC, datetime
from pydantic import ValidationError
from triagent.audit import AuditLog
from triagent.lifecycle import TransitionError, transition
from triagent.models import Finding, Lifecycle, VerificationResult

def mk(**kw):
    d = {"id": "a", "source_tool": "semgrep", "rule_id": "r", "cwe": ["CWE-79"],
         "location": {"file": "a.js", "start_line": 1, "end_line": 2}, "message": "m"}
    d.update(kw)
    return Finding.model_validate(d)

def must_raise(exc, fn, label):
    try:
        fn()
    except exc:
        return
    except Exception as e:
        print(f"ATTACK SUCCEEDED ({label}): wrong exception {type(e).__name__}")
        sys.exit(1)
    print(f"ATTACK SUCCEEDED ({label})")
    sys.exit(1)

def setattr_(o, k, v):
    def run():
        setattr(o, k, v)
    return run

f = mk()
must_raise(ValidationError, setattr_(f, "lifecycle", Lifecycle.SUPPRESSED), "assign lifecycle")
must_raise(ValidationError, setattr_(f, "human_decision", None), "assign human_decision")
must_raise(ValidationError, setattr_(f.verification, "result", VerificationResult.EXPLOITABLE),
           "assign verification.result")
g = mk(lifecycle="fix_proposed", fix={"patch_path": "p.diff"})
must_raise(ValidationError, setattr_(g.fix, "tests_passed", True), "assign fix.tests_passed")
must_raise(TypeError, lambda: Finding.model_construct(id="b", lifecycle=Lifecycle.SUPPRESSED),
           "model_construct")
must_raise(ValidationError, lambda: f.model_copy(update={"lifecycle": "suppressed"}), "model_copy")
if f.lifecycle is not Lifecycle.RAW or f.verified:
    print("ATTACK SUCCEEDED: state changed"); sys.exit(1)

with tempfile.TemporaryDirectory() as d:
    log = AuditLog(os.path.join(d, "a.jsonl"))
    t = mk(lifecycle="triaged")
    object.__setattr__(t, "lifecycle", Lifecycle.SUPPRESSED)
    must_raise(TransitionError, lambda: transition(t, Lifecycle.DEDUPED, log=log, actor="human",
                                                   reason="x"), "tampered finding")
    ok = mk(lifecycle="triaged")
    must_raise(TransitionError, lambda: transition(ok, Lifecycle.SUPPRESSED, log=log,
                                                   actor="admin", reason="x"), "unknown actor")
    must_raise(TransitionError, lambda: transition(ok, Lifecycle.SUPPRESSED, log=log,
                                                   actor="model", reason="x"), "model suppress")
    if log.entries():
        print("ATTACK SUCCEEDED: failed transition wrote audit entries"); sys.exit(1)
print("ok")
PYEOF
"$PY" "$tmp/attack.py" >"$tmp/attack.log" 2>&1 \
  && ok "serangan penugasan/construct/copy/tampering/actor ditolak" \
  || { bad "serangan terhadap invarian berhasil atau skrip gagal"; tail -n 5 "$tmp/attack.log"; }

# Pembuktian: bila frozen dibalik, gerbang harus gagal (skrip serangan mendeteksinya).
mkdir -p "$tmp/mut"
cp -r src "$tmp/mut/src"
find "$tmp/mut" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
sed -i 's/frozen=True/frozen=False/' "$tmp/mut/src/triagent/models.py"
if ! grep -q 'frozen=False' "$tmp/mut/src/triagent/models.py"; then
  bad "mutasi uji tidak dapat diterapkan (frozen=True tidak ditemukan di models.py)"
elif PYTHONPATH="$wtmp/mut/src" "$PY" "$tmp/attack.py" >"$tmp/mut.log" 2>&1; then
  bad "mutasi frozen=False tidak terdeteksi oleh skrip serangan"
elif grep -q 'ATTACK SUCCEEDED' "$tmp/mut.log"; then
  ok "mutasi frozen=False membuat pemeriksaan serangan gagal (gerbang peka)"
else
  bad "skrip serangan gagal karena sebab lain pada mutasi: $(tail -n 1 "$tmp/mut.log")"
fi

# Kode produk tidak memuat jalur bypass.
if grep -rnE '\.model_construct\(|object\.__setattr__' src --include='*.py' >/dev/null 2>&1; then
  bad "src memuat model_construct atau object.__setattr__"
else
  ok "src tanpa model_construct atau object.__setattr__"
fi

# 5. CLI.
out="$("$PY" -m triagent --help 2>&1)"; rc=$?
[ $rc -eq 0 ] && echo "$out" | grep -qi 'triagent' && ok "triagent --help jalan" || bad "triagent --help gagal"
for sub in check-config verify-audit export-schema; do
  echo "$out" | grep -q "$sub" && ok "subperintah terdaftar: $sub" || bad "subperintah hilang: $sub"
done
"$PY" -m triagent --version 2>&1 | grep -q '^triagent ' && ok "--version" || bad "--version gagal"

# 6. Skema terekspor valid, cocok dengan model, dan benar-benar menolak data buruk.
"$PY" -m triagent export-schema --out "$wtmp/schemas" >/dev/null 2>&1 \
  && ok "export-schema berjalan" || bad "export-schema gagal"
"$PY" -m triagent export-schema --check --out schemas >"$tmp/schemacheck.log" 2>&1 \
  && ok "schemas/ cocok dengan model" || { bad "schemas/ tidak cocok dengan model"; cat "$tmp/schemacheck.log"; }
cmp -s <(cat schemas/finding.schema.json 2>/dev/null) <(cat "$tmp/schemas/finding.schema.json" 2>/dev/null) \
  && ok "ekspor ulang identik dengan schemas/finding.schema.json" || bad "ekspor ulang berbeda dari schemas/"
cat > "$tmp/schema_check.py" <<'PYEOF'
import json, sys
from jsonschema import Draft202012Validator

d = sys.argv[1]
good = {
    "id": "f1", "source_tool": "semgrep", "rule_id": "r", "cwe": ["CWE-79", "CWE-80"],
    "location": {"file": "a.js", "start_line": 1, "end_line": 2}, "message": "m",
}
bad_cases = {
    "extra verified field": {**good, "verified": True},
    "unknown lifecycle": {**good, "lifecycle": "verified"},
    "bad cwe": {**good, "cwe": ["79"]},
    "line zero": {**good, "location": {"file": "a.js", "start_line": 0, "end_line": 1}},
}
fv = Draft202012Validator(json.load(open(f"{d}/finding.schema.json", encoding="utf-8")))
Draft202012Validator.check_schema(fv.schema)
assert not list(fv.iter_errors(good)), "good finding rejected"
for name, doc in bad_cases.items():
    assert list(fv.iter_errors(doc)), f"schema accepted: {name}"
call = json.load(open(f"{d}/llm-call.schema.json", encoding="utf-8"))
Draft202012Validator.check_schema(call)
required = set(call["required"])
need = {"call_id", "model_id", "called_at", "params", "prompt_id", "prompt_hash",
        "tokens_in", "tokens_out", "cost_usd", "latency_ms", "status"}
assert need <= required, f"LlmCall schema misses required: {need - required}"
for name in ("audit-entry", "config"):
    Draft202012Validator.check_schema(json.load(open(f"{d}/{name}.schema.json", encoding="utf-8")))
print("ok")
PYEOF
"$PY" "$tmp/schema_check.py" schemas >"$tmp/sc.log" 2>&1 \
  && ok "skema valid, menerima data baik, menolak data buruk, LlmCall mewajibkan field I-06" \
  || { bad "pemeriksaan skema gagal"; tail -n 5 "$tmp/sc.log"; }

# 7. Audit log: rantai hash terdeteksi rusak (diubah, dihapus di tengah, ekor dipotong, disisipi).
cat > "$tmp/mk_log.py" <<'PYEOF'
import sys
from triagent.audit import AuditLog
log = AuditLog(sys.argv[1])
for i in range(6):
    log.append("note", {"i": i, "text": "halo é"})
PYEOF
mklog() { rm -f "$tmp/a.jsonl" "$tmp/a.jsonl.head"; "$PY" "$tmp/mk_log.py" "$wtmp/a.jsonl"; }
verify() { "$PY" -m triagent verify-audit "$wtmp/a.jsonl" >/dev/null 2>&1; }

mklog; verify && ok "audit: log utuh lolos verifikasi" || bad "audit: log utuh ditolak"
mklog; sed -i '3s/"i":2/"i":9/' "$tmp/a.jsonl"
verify && bad "audit: baris yang diubah tidak terdeteksi" || ok "audit: baris diubah terdeteksi"
mklog; sed -i '3d' "$tmp/a.jsonl"
verify && bad "audit: baris dihapus di tengah tidak terdeteksi" || ok "audit: penghapusan di tengah terdeteksi"
mklog; head -n 4 "$tmp/a.jsonl" > "$tmp/a.cut" && mv "$tmp/a.cut" "$tmp/a.jsonl"
verify && bad "audit: ekor terpotong tidak terdeteksi" || ok "audit: ekor terpotong terdeteksi"
mklog; head=$("$PY" -c "import json,sys; print(json.load(open(sys.argv[1]))['head'])" "$wtmp/a.jsonl.head")
head -n 4 "$tmp/a.jsonl" > "$tmp/a.cut" && mv "$tmp/a.cut" "$tmp/a.jsonl"; rm -f "$tmp/a.jsonl.head"
"$PY" -m triagent verify-audit "$wtmp/a.jsonl" --expected-head "$head" >/dev/null 2>&1 \
  && bad "audit: pemotongan lolos dengan expected-head dari luar" || ok "audit: expected-head dari luar mendeteksi pemotongan"

rm -f "$tmp/a.jsonl" "$tmp/a.jsonl.head"
verify && bad "audit: berkas log hilang lolos verifikasi" || ok "audit: berkas log hilang ditolak"
: > "$tmp/a.jsonl"
verify && bad "audit: log kosong tanpa head lolos" || ok "audit: log kosong tanpa head ditolak"
mklog; awk 'NR==3{print ""} {print}' "$tmp/a.jsonl" > "$tmp/a.blank" && mv "$tmp/a.blank" "$tmp/a.jsonl"
verify && bad "audit: baris kosong sisipan lolos" || ok "audit: baris kosong sisipan ditolak"

# 7b. Penulisan paralel: 4 proses x 25 append menghasilkan 100 entri, seq unik, rantai utuh.
cat > "$tmp/par.py" <<'PYEOF'
import sys
from triagent.audit import AuditLog
log = AuditLog(sys.argv[1])
for i in range(25):
    log.append("note", {"w": sys.argv[2], "i": i})
PYEOF
cat > "$tmp/count.py" <<'PYEOF'
import sys
from triagent.audit import AuditLog
seqs = [e["seq"] for e in AuditLog(sys.argv[1]).entries()]
sys.exit(0 if sorted(seqs) == list(range(100)) else 1)
PYEOF
rm -f "$tmp/p.jsonl" "$tmp/p.jsonl.head"
for w in 1 2 3 4; do "$PY" "$tmp/par.py" "$wtmp/p.jsonl" "$w" & done
wait
"$PY" -m triagent verify-audit "$wtmp/p.jsonl" >/dev/null 2>&1 \
  && "$PY" "$tmp/count.py" "$wtmp/p.jsonl" \
  && ok "audit: 4 proses paralel menghasilkan 100 entri, seq unik, verify ok" \
  || bad "audit: penulisan paralel merusak log"

# 8. Konfigurasi: contoh valid lolos, tidak valid ditolak.
printf 'models: [profile-a]\nmode: triage\n' > "$tmp/ok.yml"
printf 'models: [profile-a]\nmode: triage+verify\n' > "$tmp/bad.yml"
printf 'models: [profile-a]\nunknown_key: 1\n' > "$tmp/bad2.yml"
"$PY" -m triagent check-config "$wtmp/ok.yml" >/dev/null 2>&1 && ok "config valid diterima" || bad "config valid ditolak"
"$PY" -m triagent check-config "$wtmp/bad.yml" >/dev/null 2>&1 && bad "config tidak konsisten diterima" || ok "config mode tanpa verify.enabled ditolak"
"$PY" -m triagent check-config "$wtmp/bad2.yml" >/dev/null 2>&1 && bad "config dengan kunci asing diterima" || ok "config dengan kunci asing ditolak"

# 9. Kode produk tidak membawa klien jaringan di fase ini.
if grep -rnE '^\s*(import|from)\s+(socket|requests|httpx|urllib|http\.client|aiohttp)\b' src >/dev/null 2>&1; then
  bad "src mengimpor modul jaringan di Fase 1"
else
  ok "src tidak mengimpor modul jaringan"
fi

[ "$fail" -eq 0 ] && exit 0
exit 1
