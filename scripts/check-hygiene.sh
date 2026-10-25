#!/usr/bin/env bash
# Pemeriksaan kebersihan repo. Dipakai gate.sh dan CI.
#
#   scripts/check-hygiene.sh                  periksa keadaan sekarang
#   scripts/check-hygiene.sh --commits RANGE  periksa juga pesan commit di RANGE (mis. origin/main..HEAD)
set -u

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO" || exit 1
fail=0
bad() { echo "FAIL: $1"; fail=1; }
ok()  { echo "PASS: $1"; }

range=""
if [ "${1:-}" = "--commits" ]; then range="${2:-}"; fi

git rev-parse --git-dir >/dev/null 2>&1 || { echo "FAIL: bukan repositori git"; exit 1; }

# 1. Tidak ada PDF yang terlacak git.
pdfs="$(git ls-files | grep -iE '\.pdf$' || true)"
[ -z "$pdfs" ] && ok "tidak ada PDF di git" || bad "PDF terlacak git: $pdfs"

# 2. Tidak ada berkas .env terlacak (kecuali contoh).
envs="$(git ls-files | grep -E '(^|/)\.env(\..*)?$' | grep -v '\.env\.example$' || true)"
[ -z "$envs" ] && ok "tidak ada .env di git" || bad ".env terlacak git: $envs"

# 3. Tidak ada tanda pisah panjang (em dash) di dokumen dan skrip.
emdash="$(printf '\342\200\224')"
hits="$(git ls-files '*.md' '*.sh' '*.yml' '*.yaml' '*.json' | xargs grep -l "$emdash" 2>/dev/null || true)"
[ -z "$hits" ] && ok "tidak ada tanda pisah panjang" || bad "tanda pisah panjang di: $hits"

# 4. Pola rahasia umum (pola disusun dari potongan agar skrip ini tidak mengenai dirinya sendiri).
p_ant='sk-a''nt-[A-Za-z0-9_-]{20,}'
p_goog='AI''za[0-9A-Za-z_-]{35}'
p_gh='gh[pousr]''_[A-Za-z0-9]{36,}'
p_aws='AK''IA[0-9A-Z]{16}'
p_key='-----BEGIN [A-Z ]*PRIVATE'' KEY-----'
secrets="$(git grep -nE "$p_ant|$p_goog|$p_gh|$p_aws|$p_key" -- . 2>/dev/null || true)"
[ -z "$secrets" ] && ok "tidak ada pola rahasia" || bad "kemungkinan rahasia ditemukan (path:baris): $(printf '%s' "$secrets" | cut -d: -f1,2 | tr '\n' ' ')"

# 5. Atribusi dikosongkan dan tidak ada agent bermodel fable.
if command -v jq >/dev/null 2>&1 && [ -f .claude/settings.json ]; then
  c="$(jq -r '.attribution.commit // "UNSET"' .claude/settings.json)"
  p="$(jq -r '.attribution.pr // "UNSET"' .claude/settings.json)"
  [ "$c" = "" ] && [ "$p" = "" ] && ok "atribusi commit dan PR kosong" || bad "attribution.commit dan .pr harus string kosong"
fi
if [ -d .claude/agents ]; then
  fab="$(grep -rilE '^model:[[:space:]]*.*fable' .claude/agents 2>/dev/null || true)"
  [ -z "$fab" ] && ok "tidak ada agent bermodel fable" || bad "agent memakai fable: $fab"
fi

# 6. Pesan commit bebas dari trailer atribusi.
if git rev-parse HEAD >/dev/null 2>&1; then
  if [ -n "$range" ]; then
    msgs="$(git log --format=%B "$range" 2>/dev/null || true)"
  else
    msgs="$(git log -1 --format=%B 2>/dev/null || true)"
  fi
  trailers="$(printf '%s' "$msgs" | grep -iE '^co-authored-by:[[:space:]]*claude|^claude-session:|generated with \[?claude' || true)"
  [ -z "$trailers" ] && ok "pesan commit bersih dari trailer atribusi" || bad "trailer atribusi di pesan commit: $trailers"
fi

if [ "$fail" -eq 0 ]; then
  echo "Hygiene lulus."
  exit 0
fi
echo "Hygiene gagal."
exit 1
