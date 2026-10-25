# PLAN.md: peta fase triagent

Dokumen hidup. Diperbarui orkestrator di akhir tiap fase. Status: `[ ]` belum, `[~]` berjalan, `[x]` lulus gerbang.

Aturan umum: satu fase hanya selesai bila `scripts/gate.sh N` lulus dan review tidak menyisakan temuan kritis. Developer menulis gerbang fase sebelum menulis kode. Alur lengkap ada di `CLAUDE.md`.

## Ringkasan

| Fase | Judul | Developer | Titik cek | Perkiraan kuota* | Status |
|---|---|---|---|---|---|
| 0 | Fondasi, guard, literatur, validasi SPEC | Sonnet | - | 3 sampai 5% | [x] |
| 1 | Kerangka, skema, CLI, audit log | Sonnet | - | 4 sampai 8% | [ ] |
| 2 | Ingest SARIF, adapter Semgrep, dedup | Sonnet | - | 4 sampai 8% | [ ] |
| 3 | Benchmark dan harness evaluasi | **Opus** | **C1** | 8 sampai 14% | [ ] |
| 4 | Triase LLM multi-model, redaksi | Sonnet | - | 8 sampai 14% | [ ] |
| 5 | Slicing konteks kode | Sonnet | - | 6 sampai 12% | [ ] |
| 6 | GitHub Action dan komentar PR | Sonnet | **C2** | 6 sampai 10% | [ ] |
| 7 | Verifikasi di sandbox | **Opus** | **C3** (setelah fase 8) | 12 sampai 22% | [ ] |
| 8 | Perbaikan otomatis | **Opus** | **C3** | 10 sampai 18% | [ ] |
| 9 | Dashboard dan laporan | Sonnet | - | 8 sampai 14% | [ ] |
| 10 | Pengerasan keamanan dan serah terima | **Opus** | **C4** | 6 sampai 12% | [ ] |

*Persen dari batas mingguan paket Max 5x, dan hanya tebakan kasar. Total sekitar 75 sampai 140% dari satu minggu. Kalibrasi dengan tabel pemakaian di bawah setelah Fase 1. Di Max 20x kemungkinan sekitar setengahnya.

## Titik cek

Di titik cek orkestrator berhenti dan mengirim satu laporan (maksimal satu halaman): apa yang jadi, hasil gerbang, temuan review yang tersisa, keputusan yang butuh pemilik, kuota terpakai. Pemilik membalas "lanjut" atau memberi koreksi singkat. Setelah "lanjut", orkestrator merge branch fase ke `main` dan meneruskan.

- **C1** setelah Fase 3: fondasi dan alat ukur siap.
- **C2** setelah Fase 6: produk inti jalan end-to-end tanpa sandbox.
- **C3** setelah Fase 8: sandbox dan perbaikan otomatis (risiko tertinggi).
- **C4** setelah Fase 10: serah terima akhir.

## Rincian fase

### Fase 0: fondasi

Tujuan: semua pengaman bekerja sebelum satu baris kode produk ditulis.
- Jalankan `scripts/setup.sh` dan `scripts/install-guard.sh`; lulus `scripts/guard-selftest.sh`.
- Verifikasi pengaturan agent: model tiap agent sesuai tabel di `CLAUDE.md` (pemilik memeriksa `/agents` dan `/permissions` sekali, lihat `docs/LAUNCH.md`).
- Triase PDF di `docs/literature/pdf/`: pemilik menaruh file, explorer memetakan, developer menulis catatan untuk semua paper berprioritas `core` di `docs/literature/INDEX.md` memakai `NOTE-TEMPLATE.md`.
- Architect memvalidasi `SPEC.md` dan menandai keputusan yang perlu diubah di `DECISIONS.md`.
- Lengkapi `docs/DESIGN-TRACE.md` sehingga tiap baris punya dasar atau ditandai keputusan teknik.
Gerbang: `scripts/gates/phase-0.sh`.

### Fase 1: kerangka dan skema
- `pyproject.toml`, paket `src/triagent`, `tests/`, CLI `triagent --help`.
- Model `Finding` dan skema JSON, pemuat konfigurasi `.triagent.yml`, audit log berantai hash.
- CI menjalankan hygiene, ruff, dan pytest.
Gerbang: pytest dan ruff hijau; tes skema, tes audit log (rantai hash terdeteksi rusak bila diubah).

### Fase 2: ingest dan normalisasi
- Parser SARIF 2.1.0 ke `Finding`.
- Adapter Semgrep (menjalankan CLI bila ada, atau memakai fixture SARIF).
- Dedup (lokasi berdekatan, keluarga CWE yang sama). Tabel keluarga CWE termasuk pasangan yang sering tertukar (misalnya 862 dan 863).
Gerbang: tes golden pada fixture SARIF nyata; tes dedup.

### Fase 3: benchmark dan harness (Opus)
- Konsultasi `literature-advisor` untuk desain metrik dan protokol.
- Aplikasi benchmark baru di `benchmark/`, kerentanan ditanam, ground truth `ground-truth.yaml` (CWE, file, baris, kategori, skrip PoC), termasuk jebakan false positive.
- Generator varian mutasi.
- `triagent eval`: precision, recall, F1, FPR, TP retention per kategori, tabel per item, biaya, latensi, metadata run. Mode rekaman untuk tes.
- `docs/EVAL-PITFALLS.md`.
Gerbang: tes metrik pada kasus yang dihitung tangan; ground truth tervalidasi skema; PoC benchmark berjalan.
Titik cek: **C1**.

### Fase 4: triase LLM
- Konsultasi `literature-advisor` untuk desain prompt triase.
- Adapter model (minimal tiga penyedia), profil di `config/models.yaml`, keluaran JSON berskema dengan retry, registri prompt berhash, penghitung biaya dan latensi.
- Modul redaksi (I-03, I-09).
- Verdict tidak pernah menghapus temuan (I-01).
- Run berbayar pertama hanya setelah anggaran disebut di prompt peluncuran.
Gerbang: tes kontrak dengan rekaman; tes redaksi; tes bahwa temuan `likely_fp` tetap ada di keluaran.

### Fase 5: slicing konteks
- Parser tree-sitter untuk JS dan TS, slice sumber ke sink di sekitar temuan, anggaran token, fallback ke jendela file.
- Eval: file utuh versus slice (biaya, F1) di benchmark.
Gerbang: tes slice pada kasus benchmark; perbandingan tercatat di `reports/phase-5/`.

### Fase 6: GitHub Action
- `action.yml` komposit, unggah SARIF, komentar inline di PR (klien dengan mock di tes), mode dry-run, konfigurasi `.triagent.yml`.
- Adapter SonarCloud opsional bila token tersedia.
Gerbang: tes klien PR dengan mock; workflow contoh lulus di CI.
Titik cek: **C2**.

### Fase 7: verifikasi sandbox (Opus)
- Konsultasi `literature-advisor` (prinsip bukti memutuskan, mode gagal).
- Runner Docker: tanpa jaringan, non-root, sistem berkas hanya baca, batas CPU, memori, waktu.
- Peluncuran aplikasi target dari konfigurasi, pembuatan PoC oleh LLM, eksekusi, penyimpanan bukti, hasil `exploitable` atau `not_reproduced`.
Gerbang: tes egress terblokir, tes isolasi, tes batas waktu, bukti tersimpan; `not_reproduced` tidak mengubah status temuan jadi suppressed.

### Fase 8: perbaikan otomatis (Opus)
- Usulan patch di branch terpisah, jalankan tes proyek, pindai ulang, lolos hanya bila tes lulus, temuan hilang, dan tidak ada temuan baru.
- PR lewat klien (mock di tes). Tidak pernah menyentuh branch default (I-07).
Gerbang: tes alur patch pada kasus benchmark; tes bahwa branch default tidak pernah ditulis.
Titik cek: **C3**.

### Fase 9: dashboard dan laporan
- Laporan statis satu berkas HTML, dashboard FastAPI.
- Funnel dari alert mentah ke temuan terbukti, halaman detail (jalur sumber ke sink, bukti, diff patch), tren, perbandingan model, matriks kepatuhan CWE ke OWASP.
Gerbang: tes render, tes snapshot, pemeriksaan aksesibilitas dasar.

### Fase 10: pengerasan dan serah terima (Opus)
- Suite injeksi prompt lewat komentar dan string di kode, uji fuzz redaksi, audit dependensi, `SECURITY.md`, dokumen ancaman final, pemeriksaan jejak audit.
- README dan panduan pemasangan final.
Gerbang: suite injeksi lulus (temuan tidak berubah oleh teks di kode), tes redaksi, hygiene.
Titik cek: **C4**.

## Catatan pemakaian kuota

Diisi orkestrator dari `scripts/usage.sh` di awal dan akhir tiap fase.

| Fase | Tanggal | Meter sebelum (%) | Meter sesudah (%) | Selisih | Catatan |
|---|---|---|---|---|---|
| 0 | 2026-10-26 | belum tersedia | belum tersedia | belum diketahui | Guard baru dipasang di fase ini; status line aktif setelah sesi dimulai ulang, jadi `scripts/usage.sh` belum punya data. Reviewer Sonnet (instruksi pemilik), architect Opus. Siklus perbaikan 1 tanpa architect (temuan kecil). A-07, A-08, A-09, A-11 belum diuji. |
| | | | | | |

## Status berjalan

Terakhir diperbarui: 2026-10-26, fase 0 lulus.
Fase aktif: 1 (belum dimulai)
Langkah terakhir yang lulus: fase 0 (gate + review siklus 1)
Hal yang sedang dikerjakan saat berhenti: -
