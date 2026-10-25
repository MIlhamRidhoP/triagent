#!/usr/bin/env bash
# Hook PreToolUse: hentikan agent saat meter mingguan mencapai GUARD_LIMIT.
# Data berasal dari statusline.sh (rate_limits dari Claude Code, sama dengan /usage).
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GUARD_HOME="${TRIAGENT_GUARD_HOME:-$HOME/.claude/guard}"

GUARD_LIMIT=45
GUARD_STALE_SECONDS=900
GUARD_STRICT=0
# shellcheck disable=SC1091
[ -f "$HERE/config.env" ] && . "$HERE/config.env"
[ -n "${TRIAGENT_GUARD_LIMIT:-}" ] && GUARD_LIMIT="$TRIAGENT_GUARD_LIMIT"
[ -n "${TRIAGENT_GUARD_STRICT:-}" ] && GUARD_STRICT="$TRIAGENT_GUARD_STRICT"

# Buang stdin hook agar tidak menggantung.
cat >/dev/null 2>&1 || true

block() {
  # $1 = alasan (tanpa tanda kutip ganda)
  printf '{"continue": false, "stopReason": "triagent guard: %s"}\n' "$1"
  exit 0
}

unavailable() {
  # $1 = alasan. Mode strict menghentikan, mode biasa mengizinkan.
  if [ "$GUARD_STRICT" = "1" ]; then
    block "$1 (GUARD_STRICT=1)"
  fi
  exit 0
}

command -v jq >/dev/null 2>&1 || unavailable "jq tidak ditemukan"

state="$GUARD_HOME/rate_limits.json"
[ -f "$state" ] || unavailable "data limit belum ada"

now="$(date +%s)"
mtime="$(stat -c %Y "$state" 2>/dev/null || stat -f %m "$state" 2>/dev/null || echo 0)"
age=$(( now - mtime ))
if [ "$age" -gt "$GUARD_STALE_SECONDS" ]; then
  unavailable "data limit basi (${age} detik)"
fi

pct="$(jq -r '.seven_day.used_percentage // empty' "$state" 2>/dev/null)"
[ -n "$pct" ] || unavailable "persen mingguan tidak terbaca"

# Bila jendela mingguan sudah reset sejak data ditulis, angka lama tidak berlaku.
resets="$(jq -r '.seven_day.resets_at // 0' "$state" 2>/dev/null)"
case "$resets" in ''|*[!0-9]*) resets=0 ;; esac
if [ "$resets" -gt 0 ] && [ "$now" -gt "$resets" ]; then
  exit 0
fi

if awk -v a="$pct" -v b="$GUARD_LIMIT" 'BEGIN { exit !(a + 0 >= b + 0) }'; then
  block "meter mingguan ${pct} persen sudah mencapai batas ${GUARD_LIMIT} persen. Simpan keadaan di PLAN.md lalu lapor"
fi

exit 0
