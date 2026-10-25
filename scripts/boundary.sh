#!/usr/bin/env bash
# Menegakkan batas peran: setelah agent baca-saja bekerja, hanya folder yang diizinkan boleh berubah.
#
#   scripts/boundary.sh begin             rekam keadaan berkas sekarang
#   scripts/boundary.sh check reports/    gagal bila ada perubahan di luar prefix yang diizinkan
#
# Keadaan = berkas yang berbeda dari HEAD (staged, unstaged, untracked) beserta hash isinya.
set -u

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO" || exit 1
SNAP=".triagent/boundary.snap"

snapshot() {
  {
    git diff --name-only HEAD 2>/dev/null
    git ls-files -o --exclude-standard
  } | sort -u | while IFS= read -r f; do
    [ -z "$f" ] && continue
    if [ -e "$f" ]; then
      printf '%s\t%s\n' "$(git hash-object -- "$f" 2>/dev/null || echo UNREADABLE)" "$f"
    else
      printf 'DELETED\t%s\n' "$f"
    fi
  done
}

cmd="${1:-}"
case "$cmd" in
  begin)
    mkdir -p .triagent
    snapshot > "$SNAP"
    echo "boundary: keadaan direkam ($(wc -l < "$SNAP" | tr -d ' ') berkas berubah dari HEAD)"
    ;;
  check)
    allowed="${2:-}"
    [ -n "$allowed" ] || { echo "pemakaian: boundary.sh check <prefix-diizinkan>" >&2; exit 2; }
    [ -f "$SNAP" ] || { echo "boundary: jalankan 'begin' dulu" >&2; exit 2; }
    now="$(mktemp)"
    snapshot > "$now"
    changed="$(diff "$SNAP" "$now" | grep -E '^[<>]' | cut -c3- | cut -f2 | sort -u)"
    rm -f "$now"
    bad=""
    while IFS= read -r f; do
      [ -z "$f" ] && continue
      case "$f" in
        "$allowed"*) ;;
        *) bad="${bad}${f}"$'\n' ;;
      esac
    done <<EOF
$changed
EOF
    if [ -n "$bad" ]; then
      echo "boundary: PELANGGARAN. Berkas di luar '$allowed' berubah:"
      printf '%s' "$bad" | sed 's/^/  /'
      exit 1
    fi
    echo "boundary: aman, perubahan hanya di '$allowed'"
    ;;
  *)
    echo "pemakaian: boundary.sh begin | check <prefix>" >&2
    exit 2
    ;;
esac
