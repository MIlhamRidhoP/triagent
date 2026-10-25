# DESIGN-TRACE.md: jejak keputusan desain ke dasarnya

Setiap keputusan desain penting punya satu baris. Kolom Dasar berisi kunci catatan di `docs/literature/notes/` atau tanda `keputusan teknik` bila memang tidak ada dasar literatur. Reviewer menandai keputusan di diff yang tidak punya baris di sini.

Status dasar:
- `seed`: berasal dari analisis awal, wajib dicek ke catatan atau PDF sebelum dikutip di luar repo.
- `dicatat`: sudah ada catatan di `docs/literature/notes/`.
- `teknik`: tidak ada dasar literatur, keputusan rekayasa.

Aturan: kolom Dasar tidak boleh kosong (diperiksa `scripts/gates/phase-0.sh`).

| ID | Keputusan | Dasar | Status | Fase |
|---|---|---|---|---|
| D-01 | LLM melengkapi scanner, bukan menggantikan (K-01) | iris-2025 | seed | semua |
| D-02 | Tidak ada temuan yang dibuang otomatis; ukur TP retention per kategori (I-01) | sifting-noise-2026 | seed | 3, 4 |
| D-03 | Redaksi konteks sebelum dikirim ke LLM, termasuk bingkai "kode aman" (I-03) | contextual-bias-2026 | seed | 4, 10 |
| D-04 | Status terverifikasi hanya dari bukti eksekusi di sandbox (I-02) | frontier-llms-2026, sifting-noise-2026 | seed | 7 |
| D-05 | Konteks berupa slice sumber ke sink, bukan file utuh | purba-2023 | seed | 5 |
| D-06 | CWE scanner sebagai jangkar; pencocokan per keluarga CWE (I-05) | huynh-uwa, frontier-llms-2026 | seed | 2, 3 |
| D-07 | Daftar periksa jebakan evaluasi untuk harness | chasing-shadows-2026 | seed | 3 |
| D-08 | Evaluasi scanner saja versus scanner dengan LLM pada dataset yang sama | tamberg-bahsi-2025 | seed | 3 |
| D-09 | Pemilihan model benchmark merujuk studi komparasi; tier apple-to-apple adalah keputusan pemilik | koterba-2026 | seed | 4 |
| D-10 | Biaya USD dan latensi terukur per run, bukan hanya tarif | gnieciak-2025 | seed | 3, 4 |
| D-11 | Konfigurasi bawaan scanner sering kurang; motivasi lapisan tambahan | anggoman-2025 | seed | 1 |
| D-12 | Istilah kategori produk: Static Analysis Augmentation | jin-2025 | seed | docs |
| D-13 | Threat modelling di fase desain (roadmap pasca v1) | bedoya-2024 | seed | roadmap |
| D-14 | Pemetaan kepatuhan ke praktik SSDF dan model SSDLC (laporan Fase 9) | nist-ssdf-800-218, zakkiya-2025 | seed | 9 |
| D-15 | Korpus benchmark baru buatan sendiri, bukan aplikasi rentan terkenal | chasing-shadows-2026 | seed | 3 |
| D-16 | Sandbox Docker tanpa jaringan, non-root, batas sumber daya (I-08) | teknik | teknik | 7 |
| D-17 | Audit log berantai hash | teknik | teknik | 1 |
| D-18 | Semgrep OSS sebagai scanner pertama (A-03) | teknik | teknik | 2 |
| D-19 | Antarmuka model yang dapat ditukar, ID model di konfigurasi | teknik | teknik | 4 |
