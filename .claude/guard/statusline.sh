#!/usr/bin/env bash
# Status line Claude Code. Dua tugas:
# 1. Menyimpan rate_limits (persen 5 jam dan 7 hari) ke berkas yang dibaca guard.sh.
# 2. Mencetak satu baris status. Bila ada status line lama (chain.txt), dipanggil juga.
set -u

GUARD_HOME="${TRIAGENT_GUARD_HOME:-$HOME/.claude/guard}"
mkdir -p "$GUARD_HOME" 2>/dev/null || true

input="$(cat)"
wk="?"
h5="?"
model=""

if command -v jq >/dev/null 2>&1; then
  tmp="$GUARD_HOME/rate_limits.json.tmp"
  if printf '%s' "$input" | jq -c '.rate_limits // empty' > "$tmp" 2>/dev/null && [ -s "$tmp" ]; then
    mv "$tmp" "$GUARD_HOME/rate_limits.json"
  else
    rm -f "$tmp"
  fi
  wk="$(printf '%s' "$input" | jq -r '.rate_limits.seven_day.used_percentage // "?"' 2>/dev/null)"
  h5="$(printf '%s' "$input" | jq -r '.rate_limits.five_hour.used_percentage // "?"' 2>/dev/null)"
  model="$(printf '%s' "$input" | jq -r '.model.display_name // ""' 2>/dev/null)"
fi

line="mingguan ${wk}% | sesi ${h5}%"
[ -n "$model" ] && line="${model} | ${line}"

if [ -f "$GUARD_HOME/chain.txt" ]; then
  chain="$(cat "$GUARD_HOME/chain.txt" 2>/dev/null)"
  if [ -n "$chain" ]; then
    extra="$(printf '%s' "$input" | bash -c "$chain" 2>/dev/null || true)"
    [ -n "$extra" ] && line="${extra} | ${line}"
  fi
fi

printf '%s\n' "$line"
