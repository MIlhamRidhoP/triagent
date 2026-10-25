# Laporan developer Fase 3 (tahap A dan B)

## Hasil
- Benchmark baru `benchmark/app` (`fieldnotes-bench`, Express, sekitar 830 baris JS): 13 TP dan 10 jebakan FP, 11 kategori, bingkai komentar aman pada 4 TP dan bingkai bahaya pada 1 jebakan. Ground truth `benchmark/ground-truth.yaml` dengan skema `schemas/ground-truth.schema.json`; label dari PoC.
- PoC per item di `benchmark/poc/`, dijalankan hanya lewat `docker compose` pada jaringan `internal: true` (non-root, rootfs baca-saja, tanpa capability, tanpa egress; selftest membuktikannya dari dalam kontainer). TP: PoC berhasil; jebakan: PoC gagal.
- Generator mutasi (`triagent benchmark mutate`): hapus komentar, ganti nama, ubah gaya; ground truth bergeser dan divalidasi lewat `anchor`; PoC dijalankan pada dua varian.
- Harness `triagent eval score|run` dengan mode rekaman, metrik ketat/longgar, uncertain dua arah, TP retention per kategori, temuan tak terlabel, biaya, latensi, metadata P9. `docs/EVAL-PITFALLS.md` P1 sampai P9.
- Keputusan: D-36 sampai D-42, A-28, A-29.

## Ragu
- Belum ada run Semgrep nyata pada benchmark; ground truth dilabel satu pihak (agent + PoC); ambang kestabilan run belum ditetapkan; build image butuh jaringan registry sekali; diuji di Windows saja (CI Linux belum).

## Verifikasi
`bash scripts/gate.sh 3`, `python -m pytest -q`, `python -m ruff check src tests`. Rincian: `dev-report-a.md`, `dev-report-b.md`.

## Perbaikan siklus 1
- R-01: pencocokan satu-ke-satu (jarak, CWE ketat, id), validator jarak antar item sekeluarga CWE (<= 2 x toleransi + 1); BM-022 pindah ke `routes/docs.js`, BM-009 dipersempit ke baris 8, BM-014 ke `routes/home.js`; PoC BM-011/022 diulang.
- R-02: rute jebakan menjadi `/jump`, `/card`, `/tools/say`; `triagent benchmark check-names` dipanggil gerbang pada aplikasi dan varian.
- R-03: selftest di kontainer poc dan app, 13 kunci tetap (default route, gateway, 2375, host.docker.internal, metadata, docker.sock, kontrol positif).
- R-04: error 500 generik, `GET /notes/:id` didokumentasikan publik by design. R-05: `--strip-prefix`, duplikat dilewati, peringatan nol-cocok. R-06: daftar putih meta, `dropped_meta_keys`.
- R-07: base image dipin digest, hasil PoC memuat `base_image_digest` dan `image_id`.
- A-29, D-42, EVAL-PITFALLS, README benchmark diperbarui; klaim "belum ada kasus nyata" dikoreksi. Gerbang: kasus tangan baru, tidak ada pemeriksaan yang dilonggarkan.
