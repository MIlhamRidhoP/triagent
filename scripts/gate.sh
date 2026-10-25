#!/usr/bin/env bash
# Menjalankan gerbang sebuah fase: hygiene umum, lalu gerbang khusus fase.
# Hasil ditulis ke reports/phase-N/gate-result.json. Kode keluar 0 hanya bila semuanya lulus.
#
#   scripts/gate.sh 3
set -u

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO" || exit 1

n="${1:-}"
case "$n" in ''|*[!0-9]*) echo "pemakaian: gate.sh <nomor-fase>" >&2; exit 2 ;; esac
command -v jq >/dev/null 2>&1 || { echo "jq diperlukan" >&2; exit 2; }

outdir="reports/phase-$n"
mkdir -p "$outdir"
log_h="$outdir/gate-hygiene.log"
log_p="$outdir/gate-phase.log"

bash scripts/check-hygiene.sh > "$log_h" 2>&1
rc_h=$?

phase_script="scripts/gates/phase-$n.sh"
if [ -f "$phase_script" ]; then
  bash "$phase_script" > "$log_p" 2>&1
  rc_p=$?
else
  echo "Gerbang fase $n belum ditulis ($phase_script). Developer wajib menulisnya sebelum implementasi." > "$log_p"
  rc_p=1
fi

passed=false
[ "$rc_h" -eq 0 ] && [ "$rc_p" -eq 0 ] && passed=true

jq -n \
  --argjson phase "$n" \
  --argjson passed "$passed" \
  --argjson rc_h "$rc_h" \
  --argjson rc_p "$rc_p" \
  --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg head "$(git rev-parse --short HEAD 2>/dev/null || echo none)" \
  --arg log_h "$log_h" \
  --arg log_p "$log_p" \
  '{phase: $phase, passed: $passed, timestamp_utc: $ts, git_head: $head,
    checks: [{name: "hygiene", exit_code: $rc_h, log: $log_h},
             {name: "phase", exit_code: $rc_p, log: $log_p}]}' \
  > "$outdir/gate-result.json"

tail -n 3 "$log_h"
tail -n 8 "$log_p"
if [ "$passed" = true ]; then
  echo "GERBANG FASE $n: LULUS ($outdir/gate-result.json)"
  exit 0
fi
echo "GERBANG FASE $n: GAGAL ($outdir/gate-result.json)"
exit 1
