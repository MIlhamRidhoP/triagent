#!/usr/bin/env bash
# Memasang status line guard di pengaturan pengguna (~/.claude/settings.json).
# Status line lama (bila ada) disimpan sebagai chain dan tetap dipanggil.
# Pengaturan lama dicadangkan lebih dulu.
set -eu

command -v jq >/dev/null 2>&1 || { echo "jq diperlukan. Pasang jq lalu ulangi." >&2; exit 1; }

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO/.claude/guard/statusline.sh"
GUARD_HOME="${TRIAGENT_GUARD_HOME:-$HOME/.claude/guard}"
SETTINGS="${TRIAGENT_USER_SETTINGS:-$HOME/.claude/settings.json}"

chmod +x "$REPO/.claude/guard/"*.sh 2>/dev/null || true
mkdir -p "$GUARD_HOME" "$(dirname "$SETTINGS")"
[ -f "$SETTINGS" ] || echo '{}' > "$SETTINGS"

backup="$SETTINGS.bak-$(date +%Y%m%d-%H%M%S)"
cp "$SETTINGS" "$backup"
echo "Cadangan: $backup"

new_cmd="bash \"$SCRIPT\""
old_cmd="$(jq -r '.statusLine.command // empty' "$SETTINGS")"

if [ -n "$old_cmd" ] && [ "$old_cmd" != "$new_cmd" ]; then
  case "$old_cmd" in
    *triagent*|*statusline.sh*guard*) ;;  # sudah milik guard, jangan dijadikan chain
    *)
      printf '%s' "$old_cmd" > "$GUARD_HOME/chain.txt"
      echo "Status line lama disimpan sebagai chain: $old_cmd"
      ;;
  esac
fi

tmp="$(mktemp)"
jq --arg cmd "$new_cmd" '.statusLine = {"type": "command", "command": $cmd}' "$SETTINGS" > "$tmp"
mv "$tmp" "$SETTINGS"

echo "Terpasang. Status line sekarang: $new_cmd"
echo "Mulai ulang Claude Code. Data limit baru tersedia setelah respons pertama sesi."
echo "Batas diatur di: $REPO/.claude/guard/config.env"
