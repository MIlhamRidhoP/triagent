#!/usr/bin/env bash
# Gerbang Fase 0: fondasi, guard, agent, literatur, jejak desain.
set -u
cd "$(dirname "${BASH_SOURCE[0]}")/../.." || exit 1

fail=0
ok()  { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fail=1; }

# 1. Berkas wajib ada.
for f in CLAUDE.md SPEC.md PLAN.md DECISIONS.md README.md docs/DESIGN-TRACE.md docs/LAUNCH.md \
         docs/literature/INDEX.md docs/literature/NOTE-TEMPLATE.md .claude/settings.json \
         .claude/guard/guard.sh .claude/guard/statusline.sh .claude/guard/config.env \
         scripts/gate.sh scripts/boundary.sh scripts/check-hygiene.sh .githooks/commit-msg .githooks/pre-commit; do
  [ -f "$f" ] && ok "ada: $f" || bad "hilang: $f"
done

# 2. Guard lulus tes mandiri.
bash scripts/guard-selftest.sh >/dev/null 2>&1 && ok "guard-selftest lulus" || bad "guard-selftest gagal"

# 3. Pengaturan JSON valid dan hook terpasang.
if command -v jq >/dev/null 2>&1; then
  jq -e . .claude/settings.json >/dev/null 2>&1 && ok "settings.json valid" || bad "settings.json tidak valid"
  jq -e '.hooks.PreToolUse[0].hooks[0].command | contains("guard.sh")' .claude/settings.json >/dev/null 2>&1 \
    && ok "hook guard terpasang" || bad "hook guard belum terpasang di settings.json"
else
  bad "jq tidak ditemukan"
fi

# 4. Agent: model sesuai pembagian peran.
check_model() { # file, pola
  grep -qE "^model:[[:space:]]*($2)[[:space:]]*$" ".claude/agents/$1.md" 2>/dev/null \
    && ok "agent $1 memakai model yang benar" || bad "agent $1 salah model (harus: $2)"
}
check_model developer 'sonnet|claude-sonnet-5-5'
check_model reviewer 'opus|claude-opus-5-5'
check_model architect 'opus|claude-opus-5-5'
check_model explorer 'haiku|claude-haiku-5-5'
check_model literature-advisor 'sonnet|claude-sonnet-5-5'

# 5. Git: hook aktif dan identitas ada.
[ "$(git config core.hooksPath 2>/dev/null)" = ".githooks" ] && ok "core.hooksPath = .githooks" || bad "jalankan scripts/setup.sh (core.hooksPath belum diset)"
[ -n "$(git config user.name 2>/dev/null)" ] && [ -n "$(git config user.email 2>/dev/null)" ] \
  && ok "identitas git terisi" || bad "identitas git belum diset"

# 6. Setiap paper berprioritas core di INDEX punya catatan.
if [ -f docs/literature/INDEX.md ]; then
  missing=0
  while IFS='|' read -r _ key _ prio _; do
    key="$(echo "$key" | tr -d ' ')"
    prio="$(echo "$prio" | tr -d ' ')"
    [ "$prio" = "core" ] || continue
    if [ -f "docs/literature/notes/$key.md" ]; then
      ok "catatan ada: $key"
    else
      bad "catatan belum ada untuk paper core: $key"
      missing=1
    fi
  done < <(grep -E '^\|' docs/literature/INDEX.md | grep -vE '^\|[- |]+\|$')
fi

# 7. DESIGN-TRACE: kolom Dasar tidak kosong di semua baris D-xx.
empty=0
while IFS='|' read -r _ id _ dasar _; do
  id="$(echo "$id" | tr -d ' ')"
  dasar="$(echo "$dasar" | tr -d ' ')"
  case "$id" in D-*) [ -n "$dasar" ] || { bad "DESIGN-TRACE $id tanpa dasar"; empty=1; } ;; esac
done < docs/DESIGN-TRACE.md
[ "$empty" -eq 0 ] && ok "DESIGN-TRACE: semua baris punya dasar"

# 8. Hasil validasi Architect tercatat.
[ -f reports/phase-0/resolution.md ] && ok "resolusi Architect untuk SPEC ada" || bad "reports/phase-0/resolution.md belum ada (validasi SPEC oleh Architect)"

[ "$fail" -eq 0 ] && exit 0
exit 1
