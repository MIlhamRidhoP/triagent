# Dev report Fase 0 (penutup)

## Yang jadi
- `DECISIONS.md`: A-02 dan A-03 diubah, A-14 sampai A-18 dan O-05 sampai O-08 ditambah sesuai resolution.md. O-07 (venue huynh-uwa belum diketahui) dan O-08 (pendanaan/konflik beberapa paper belum diperiksa) tambahan dari orkestrator. Bagian K dan `SPEC.md` tidak diubah (R-04 hanya dicatat sebagai O-05).
- `docs/DESIGN-TRACE.md`: D-20 sampai D-25 (teknik, dari R-01, R-02, R-03, R-05, R-07, R-09). 13 baris seed naik ke `dicatat` (D-01 sampai D-04, D-06 sampai D-13, dan D-15) karena catatannya ada, dicek ke PDF, dan isinya mendukung. D-05 (purba-2023: paper tidak menguji slice, hanya pola versus aliran data) dan D-14 (nist dan zakkiya belum punya catatan) tetap `seed`, alasan di kolom Keputusan.
- Catatan literatur: ID "belum dipetakan" diganti D-13 (bedoya), D-06 (huynh), D-11 (anggoman), D-12 (jin), D-10 (gnieciak). rajapaksha-2024 tidak punya baris D-xx, kalimatnya diganti keterangan itu.
- `docs/literature/INDEX.md`: 14 key bercatatan jadi `dicatat`; 10 baris belum-dipilah yang sudah dipetakan dikeluarkan. Format lima kolom utuh, tidak ada key core baru.
- `reports/phase-0/pdf-map.md` ditulis ulang dengan koreksi (gnieciak dan tamberg tertukar, anggoman, purba, koterba ditemukan).

## Penyimpangan dari tugas (perlu diketahui)
Gerbang butir 6 menuntut catatan untuk semua key core, dan `koterba-2026` belum punya catatan (batch A dan B tidak mengerjakannya). Agar gerbang lulus tanpa dilonggarkan, saya menulis `docs/literature/notes/koterba-2026.md` dari teks PDF (pdftotext, DOI cocok). Angka yang dikutip hanya dari abstrak dan teks; Tabel 4 terbaca berantakan dan ditandai "jangan dikutip". Mohon reviewer memeriksa catatan ini lebih ketat karena dibuat tanpa batch tersendiri.

## Hasil gerbang
`bash scripts/gate.sh 0`: GERBANG FASE 0: LULUS (hasil di `reports/phase-0/gate-result.json`). Tidak ada commit.

## Yang diragukan
- Keputusan "dicatat" untuk D-08 dan D-10 bersandar pada bagian implikasi catatan, bukan pada klaim paper yang menguji persis keputusan itu (tamberg tidak menggabungkan SAST dengan LLM; gnieciak hanya mengukur biaya).
- Pendanaan koterba-2026 belum diketahui.
- Nomor halaman koterba: hlm. 8 untuk biaya dan F1 teks adalah perkiraan dari pencarian teks per halaman.

## Belum bisa dilakukan developer, harus diuji orkestrator
- A-07: apakah field `effort: medium` di frontmatter agent didukung versi Claude Code ini.
- A-11: apakah hook `PreToolUse` guard berlaku untuk alat di dalam subagent (uji dengan `GUARD_LIMIT` rendah).
- A-08: alias `opus`/`sonnet`/`haiku` menunjuk ke 5.5 (lewat `/agents`).
- A-09: format aturan deny di `.claude/settings.json` (lewat `/permissions`).
- Catat hasilnya di `reports/phase-0/` (R-11).

## Verifikasi
`bash scripts/gate.sh 0` dan `bash scripts/check-hygiene.sh`

## Asumsi baru
Tidak ada di luar A-14 sampai A-18 dan O-07, O-08.

## Perbaikan siklus 1
- R-01: angka Tabel 1, 5, 6, 7 tamberg dibaca visual dari render PDF (hlm. 7, 11, 12); semua cocok, tetap di "aman dikutip" dengan lokasi; status verifikasi menyebut cara baca dan beda nomor halaman jurnal.
- R-02: kalimat celah alat diganti: enam CWE gagal per alat, lima identik, hanya CWE-81 dan CWE-190 yang berbeda. Implikasi desain disesuaikan.
- R-03: D-08 dan D-10 diberi keterangan "dasar hanya implikasi"; status tetap dicatat.
- R-04: nomor halaman koterba ditandai perkiraan di catatan.
