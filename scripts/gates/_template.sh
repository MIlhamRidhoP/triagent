#!/usr/bin/env bash
# Template gerbang fase. Salin menjadi scripts/gates/phase-N.sh lalu isi.
#
# Prinsip:
# - Periksa PERILAKU (tes jalan, skema valid, hasil sesuai), bukan hanya keberadaan berkas.
# - Berjalan offline (I-10). Tidak memanggil API berbayar.
# - Setiap pemeriksaan mencetak PASS atau FAIL satu baris dan menyetel fail=1 bila gagal.
# - Keluar 0 hanya bila semua pemeriksaan lulus.
set -u
cd "$(dirname "${BASH_SOURCE[0]}")/../.." || exit 1

fail=0
ok()  { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fail=1; }

# Contoh:
# python -m pytest -q tests/ >/dev/null 2>&1 && ok "pytest lulus" || bad "pytest gagal"
# python -m ruff check src tests >/dev/null 2>&1 && ok "ruff bersih" || bad "ruff gagal"

bad "gerbang belum diisi (salinan template)"

[ "$fail" -eq 0 ] && exit 0
exit 1
