#!/usr/bin/env bash
# Penyiapan lokal sekali jalan: hook git, izin eksekusi, pemeriksaan identitas dan atribusi.
set -u

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO" || exit 1
fail=0

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "FAIL: folder ini belum repositori git. Jalankan git init atau clone dulu."
  exit 1
fi

git config core.hooksPath .githooks
chmod +x .githooks/* scripts/*.sh scripts/gates/*.sh .claude/guard/*.sh 2>/dev/null || true
echo "OK: core.hooksPath = $(git config core.hooksPath)"

name="$(git config user.name || true)"
email="$(git config user.email || true)"
if [ -z "$name" ] || [ -z "$email" ]; then
  echo "FAIL: identitas git belum diset. Jalankan:"
  echo "  git config user.name \"Nama Kamu\""
  echo "  git config user.email \"email-github-kamu\""
  fail=1
else
  echo "OK: author commit akan menjadi: $name <$email>"
fi

if command -v jq >/dev/null 2>&1; then
  c="$(jq -r '.attribution.commit // "UNSET"' .claude/settings.json)"
  p="$(jq -r '.attribution.pr // "UNSET"' .claude/settings.json)"
  if [ "$c" = "" ] && [ "$p" = "" ]; then
    echo "OK: atribusi commit dan PR dikosongkan di .claude/settings.json"
  else
    echo "FAIL: attribution.commit dan attribution.pr harus string kosong"
    fail=1
  fi
else
  echo "FAIL: jq tidak ditemukan. Pasang jq (guard dan hygiene membutuhkannya)."
  fail=1
fi

mkdir -p .triagent reports docs/literature/notes docs/literature/pdf
echo "OK: folder kerja siap"

if [ "$fail" -ne 0 ]; then
  echo "Penyiapan belum lengkap. Perbaiki yang FAIL lalu jalankan ulang."
  exit 1
fi
echo "Penyiapan selesai."
