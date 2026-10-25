# DESIGN-TRACE.md: jejak keputusan desain ke dasarnya

Setiap keputusan desain penting punya satu baris. Kolom Dasar berisi kunci catatan di `docs/literature/notes/` atau tanda `keputusan teknik` bila memang tidak ada dasar literatur. Reviewer menandai keputusan di diff yang tidak punya baris di sini.

Status dasar:
- `seed`: berasal dari analisis awal, wajib dicek ke catatan atau PDF sebelum dikutip di luar repo.
- `dicatat`: sudah ada catatan di `docs/literature/notes/`.
- `teknik`: tidak ada dasar literatur, keputusan rekayasa.

Aturan: kolom Dasar tidak boleh kosong (diperiksa `scripts/gates/phase-0.sh`).

| ID | Keputusan | Dasar | Status | Fase |
|---|---|---|---|---|
| D-01 | LLM melengkapi scanner, bukan menggantikan (K-01) | iris-2025 | dicatat | semua |
| D-02 | Tidak ada temuan yang dibuang otomatis; ukur TP retention per kategori (I-01) | sifting-noise-2026 | dicatat | 3, 4 |
| D-03 | Redaksi konteks sebelum dikirim ke LLM, termasuk bingkai "kode aman" (I-03) | contextual-bias-2026 | dicatat | 4, 10 |
| D-04 | Status terverifikasi hanya dari bukti eksekusi di sandbox (I-02) | frontier-llms-2026, sifting-noise-2026 | dicatat | 7 |
| D-05 | Konteks berupa slice sumber ke sink, bukan file utuh; tetap seed: catatan purba-2023 ada, tetapi paper tidak menguji slice, hanya menunjukkan model mencocokkan pola, jadi slice masih inferensi | purba-2023 | seed | 5 |
| D-06 | CWE scanner sebagai jangkar; pencocokan per keluarga CWE (I-05); venue huynh-uwa belum diketahui (O-07) | huynh-uwa, frontier-llms-2026 | dicatat | 2, 3 |
| D-07 | Daftar periksa jebakan evaluasi untuk harness | chasing-shadows-2026 | dicatat | 3 |
| D-08 | Evaluasi scanner saja versus scanner dengan LLM pada dataset yang sama; dasar hanya implikasi: tamberg-bahsi-2025 membandingkan alat dan LLM secara terpisah, tidak menguji gabungan SAST dan LLM | tamberg-bahsi-2025 | dicatat | 3 |
| D-09 | Pemilihan model benchmark merujuk studi komparasi; tier apple-to-apple adalah keputusan pemilik | koterba-2026 | dicatat | 4 |
| D-10 | Biaya USD dan latensi terukur per run, bukan hanya tarif; dasar hanya implikasi: gnieciak-2025 hanya memuat tarif, bukan biaya terukur per run | gnieciak-2025 | dicatat | 3, 4 |
| D-11 | Konfigurasi bawaan scanner sering kurang; motivasi lapisan tambahan | anggoman-2025 | dicatat | 1 |
| D-12 | Istilah kategori produk: Static Analysis Augmentation | jin-2025 | dicatat | docs |
| D-13 | Threat modelling di fase desain (roadmap pasca v1) | bedoya-2024 | dicatat | roadmap |
| D-14 | Pemetaan kepatuhan ke praktik SSDF dan model SSDLC (laporan Fase 9); tetap seed: belum ada catatan untuk nist-ssdf-800-218 dan zakkiya-2025 | nist-ssdf-800-218, zakkiya-2025 | seed | 9 |
| D-15 | Korpus benchmark baru buatan sendiri, bukan aplikasi rentan terkenal | chasing-shadows-2026 | dicatat | 3 |
| D-16 | Sandbox Docker tanpa jaringan, non-root, batas sumber daya (I-08) | teknik | teknik | 7 |
| D-17 | Audit log berantai hash | teknik | teknik | 1 |
| D-18 | Semgrep OSS sebagai scanner pertama (A-03) | teknik | teknik | 2 |
| D-19 | Antarmuka model yang dapat ditukar, ID model di konfigurasi | teknik | teknik | 4 |
| D-20 | Lifecycle dan hasil verifikasi dua field terpisah; `verified` diturunkan dari `verification.result == exploitable` (A-14, R-01) | teknik | teknik | 1 |
| D-21 | Id Finding deterministik; duplikat disimpan dengan `duplicate_of`, tidak dibuang (A-15, R-02) | teknik | teknik | 2 |
| D-22 | Entitas `LlmCall` di audit log memuat semua field I-06 termasuk panggilan gagal (A-16, R-03) | teknik | teknik | 1, 4 |
| D-23 | Python `>=3.12` diuji di 3.12 dan 3.13; Semgrep lewat image Docker dengan versi dipin, tes memakai fixture SARIF (A-02, A-03, R-05) | teknik | teknik | 0, 2 |
| D-24 | `cwe` berupa daftar; keluarga CWE dari hierarki MITRE (view 1000) plus pasangan manual di `config/cwe-families.yaml` (R-07). Kecocokan CWE yang longgar juga dipakai di tamberg-bahsi-2025, tetapi tabelnya keputusan teknik | teknik | teknik | 2 |
| D-25 | Hash audit log atas JSON kanonis (kunci terurut, UTF-8, tanpa spasi); hash kepala disimpan di metadata run untuk mendeteksi pemotongan ekor (R-09) | teknik | teknik | 1 |
