#!/usr/bin/env bash
# Menguji guard.sh dan statusline.sh dengan data palsu di folder sementara.
# Tidak menyentuh ~/.claude milik pengguna.
set -u

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GUARD="$REPO/.claude/guard/guard.sh"
STATUS="$REPO/.claude/guard/statusline.sh"

command -v jq >/dev/null 2>&1 || { echo "FAIL: jq tidak ditemukan"; exit 1; }

TMPHOME="$(mktemp -d)"
trap 'rm -rf "$TMPHOME"' EXIT
export TRIAGENT_GUARD_HOME="$TMPHOME"
export TRIAGENT_GUARD_LIMIT=45

fail=0
ok()  { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fail=1; }

now="$(date +%s)"
future=$(( now + 86400 ))
past=$(( now - 86400 ))

run_guard() { printf '{}' | bash "$GUARD" 2>/dev/null; }

# 1. Tanpa berkas data: izinkan (mode tidak strict).
out="$(run_guard)"
[ -z "$out" ] && ok "tanpa data, mode biasa mengizinkan" || bad "tanpa data seharusnya mengizinkan: $out"

# 2. Tanpa berkas data, mode strict: hentikan.
out="$(TRIAGENT_GUARD_STRICT=1 run_guard)"
echo "$out" | jq -e '.continue == false' >/dev/null 2>&1 && ok "tanpa data, strict menghentikan" || bad "strict seharusnya menghentikan: $out"

# 3. Di bawah batas: izinkan.
printf '{"five_hour":{"used_percentage":10,"resets_at":%s},"seven_day":{"used_percentage":30,"resets_at":%s}}\n' "$future" "$future" > "$TMPHOME/rate_limits.json"
out="$(run_guard)"
[ -z "$out" ] && ok "30 persen di bawah batas 45, mengizinkan" || bad "seharusnya mengizinkan: $out"

# 4. Tepat di batas: hentikan.
printf '{"five_hour":{"used_percentage":10,"resets_at":%s},"seven_day":{"used_percentage":45,"resets_at":%s}}\n' "$future" "$future" > "$TMPHOME/rate_limits.json"
out="$(run_guard)"
echo "$out" | jq -e '.continue == false' >/dev/null 2>&1 && ok "45 persen mencapai batas, menghentikan" || bad "seharusnya menghentikan: $out"

# 5. Di atas batas, angka desimal: hentikan.
printf '{"seven_day":{"used_percentage":62.4,"resets_at":%s}}\n' "$future" > "$TMPHOME/rate_limits.json"
out="$(run_guard)"
echo "$out" | jq -e '.continue == false and (.stopReason | length > 0)' >/dev/null 2>&1 && ok "62,4 persen menghentikan dengan alasan" || bad "seharusnya menghentikan: $out"

# 6. Jendela sudah reset (resets_at di masa lalu): izinkan.
printf '{"seven_day":{"used_percentage":80,"resets_at":%s}}\n' "$past" > "$TMPHOME/rate_limits.json"
out="$(run_guard)"
[ -z "$out" ] && ok "jendela sudah reset, angka lama diabaikan" || bad "seharusnya mengizinkan: $out"

# 7. Data basi, mode biasa: izinkan; strict: hentikan.
printf '{"seven_day":{"used_percentage":80,"resets_at":%s}}\n' "$future" > "$TMPHOME/rate_limits.json"
touch -d '2 hours ago' "$TMPHOME/rate_limits.json" 2>/dev/null || touch -t "$(date -d '2 hours ago' +%Y%m%d%H%M 2>/dev/null || echo 200001010000)" "$TMPHOME/rate_limits.json"
out="$(run_guard)"
[ -z "$out" ] && ok "data basi, mode biasa mengizinkan" || bad "data basi seharusnya mengizinkan: $out"
out="$(TRIAGENT_GUARD_STRICT=1 run_guard)"
echo "$out" | jq -e '.continue == false' >/dev/null 2>&1 && ok "data basi, strict menghentikan" || bad "data basi strict seharusnya menghentikan: $out"

# 8. Status line menulis berkas data dan mencetak satu baris.
rm -f "$TMPHOME/rate_limits.json"
sample="$(printf '{"model":{"display_name":"Sonnet"},"rate_limits":{"five_hour":{"used_percentage":3,"resets_at":%s},"seven_day":{"used_percentage":39,"resets_at":%s}}}' "$future" "$future")"
line="$(printf '%s' "$sample" | bash "$STATUS")"
echo "$line" | grep -q 'mingguan 39%' && ok "status line mencetak persen mingguan" || bad "status line keliru: $line"
[ "$(jq -r '.seven_day.used_percentage' "$TMPHOME/rate_limits.json" 2>/dev/null)" = "39" ] && ok "status line menyimpan data untuk guard" || bad "status line tidak menyimpan data"

# 9. Status line tanpa rate_limits tidak merusak berkas yang ada.
printf '{"model":{"display_name":"Sonnet"}}' | bash "$STATUS" >/dev/null
[ "$(jq -r '.seven_day.used_percentage' "$TMPHOME/rate_limits.json" 2>/dev/null)" = "39" ] && ok "tanpa rate_limits, data lama tetap utuh" || bad "data lama rusak"

# 10. Alur ujung ke ujung: status line menulis 50 persen lalu guard menghentikan.
sample="$(printf '{"rate_limits":{"seven_day":{"used_percentage":50,"resets_at":%s}}}' "$future")"
printf '%s' "$sample" | bash "$STATUS" >/dev/null
out="$(run_guard)"
echo "$out" | jq -e '.continue == false' >/dev/null 2>&1 && ok "ujung ke ujung: 50 persen menghentikan" || bad "ujung ke ujung gagal: $out"

if [ "$fail" -eq 0 ]; then
  echo "Semua tes guard lulus."
  exit 0
fi
echo "Ada tes guard yang gagal."
exit 1
