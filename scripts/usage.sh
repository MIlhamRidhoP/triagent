#!/usr/bin/env bash
# Menampilkan persen kuota dari data terakhir yang disimpan status line.
# Dipakai orkestrator untuk mencatat pemakaian per fase di PLAN.md.
set -u

GUARD_HOME="${TRIAGENT_GUARD_HOME:-$HOME/.claude/guard}"
state="$GUARD_HOME/rate_limits.json"

command -v jq >/dev/null 2>&1 || { echo "jq tidak ditemukan"; exit 1; }
[ -f "$state" ] || { echo "belum ada data limit (data muncul setelah respons pertama sesi)"; exit 1; }

wk="$(jq -r '.seven_day.used_percentage // "?"' "$state")"
h5="$(jq -r '.five_hour.used_percentage // "?"' "$state")"
reset="$(jq -r '.seven_day.resets_at // empty' "$state")"

age=$(( $(date +%s) - $(stat -c %Y "$state" 2>/dev/null || stat -f %m "$state" 2>/dev/null || echo 0) ))
echo "mingguan=${wk} sesi=${h5} reset_epoch=${reset:-?} umur_data_detik=${age}"
