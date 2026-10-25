# Resolusi Fase 0: validasi SPEC.md v0.1

Architect, 2026-10-26. Dasar: SPEC, DECISIONS, PLAN, DESIGN-TRACE, `reports/phase-0/pdf-map.md`. Folder `docs/literature/notes/` masih kosong, jadi semua keputusan di bawah adalah keputusan teknik kecuali disebut lain. Urutan: tinggi, sedang, rendah.

## Tinggi

R-01: valid. Mesin status di bagian 5 linear (`triaged -> verified -> fix_proposed`) padahal `verify.enabled: false` adalah bawaan, dan `not_reproduced` tidak punya status tujuan. Ini membuat fix mustahil tanpa sandbox, dan membuka celah I-02 (status `verified` bisa ditafsirkan sebagai "sudah dicek"). `suppressed` juga muncul dua kali (status dan `human_decision`).
Opsi A: pisahkan sumbu: `lifecycle` (`raw`, `deduped`, `triaged`, `fix_proposed`, `fix_validated`, `suppressed`) dan `verification.result` terpisah; `verified` diturunkan dari `result == exploitable`. Murah, I-02 jadi bisa dites langsung.
Opsi B: pertahankan satu enum, tambah transisi `triaged -> fix_proposed` dan aturan eksplisit. Lebih sedikit field, tabel transisi lebih rumit.
Rekomendasi: A. Transisi diuji sebagai tabel di Fase 1.
Selesai bila: tes Fase 1 menolak `verified` tanpa `sandbox_run_id` dan `evidence_path`; `not_reproduced` tidak mengubah lifecycle; `suppressed` hanya bisa diset bila ada entri audit `human` atau `rule` dengan id aturan.

R-02: valid. Dedup (Fase 2) berpotensi melanggar I-01 karena model data tidak punya cara menyimpan duplikat tanpa membuangnya, dan `id` tidak didefinisikan stabil antar run (dibutuhkan kestabilan 3 run di bagian 7).
Opsi A: `id` = hash deterministik (tool, rule_id, file, `partialFingerprints` SARIF atau potongan kode ternormalisasi); duplikat tetap disimpan dengan `duplicate_of: id`. Biaya kecil.
Opsi B: id acak plus tabel pemetaan run. Lebih fleksibel, pencocokan antar run jadi tugas harness.
Rekomendasi: A.
Selesai bila: tes golden Fase 2: jumlah Finding keluaran sama dengan jumlah result SARIF masukan; id identik pada dua parse berkas yang sama; tiap duplikat menunjuk ke id yang ada.

R-03: valid. I-06 menuntut parameter, tanggal, status, versi prompt, dan pencatatan run gagal, tetapi entri `triage` hanya memuat sebagian dan run gagal tidak punya tempat.
Opsi A: entitas `LlmCall` terpisah di audit log (semua field I-06, termasuk `status: ok|error|timeout|schema_invalid`); verdict hanya mereferensikan `call_id`. Biaya sedang, audit bersih.
Opsi B: tambah field ke verdict dan buat verdict `error`. Mencampur hasil dan telemetri.
Rekomendasi: A. Skema dibuat di Fase 1 walau adapter baru di Fase 4.
Selesai bila: JSON Schema `LlmCall` mewajibkan semua field I-06; tes Fase 1 menulis panggilan gagal dan rantai hash tetap valid.

R-04: sebagian, butuh persetujuan pemilik. I-10 berbunyi "panggilan berbayar hanya lewat perintah eval", padahal GitHub Action (Fase 6) memanggil LLM berbayar di CI pengguna. Tafsiran harfiah melarang produk itu sendiri.
Opsi A: ubah teks I-10 menjadi "di repo ini, panggilan berbayar hanya lewat eval eksplisit; di pemakaian produk, hanya bila pengguna menyalakan dan dibatasi `budget`". Butuh persetujuan.
Opsi B: biarkan teks, catat tafsiran di DECISIONS sebagai A-xx. Tanpa ubah invarian, tetapi ambigu bagi reviewer.
Rekomendasi: A, diajukan ke pemilik. Sampai disetujui pakai B.
Selesai bila: teks I-10 diputuskan pemilik; tes Fase 4 memastikan klien LLM nyata menolak berjalan saat `TRIAGENT_OFFLINE=1` (bawaan pytest).

R-05: valid. Kelayakan stack di mesin pemilik. Python 3.13 terpasang, SPEC mengunci 3.12. Semgrep belum terpasang dan dukungan Windows native untuk Semgrep belum diketahui pasti di repo ini.
Opsi A: `requires-python >=3.12`, CI matriks 3.12 dan 3.13, Semgrep dijalankan lewat image Docker resmi dengan versi dipin; tes hanya memakai fixture SARIF yang dihasilkan sekali dan di-commit. Memanfaatkan Docker yang sudah ada.
Opsi B: pasang Semgrep lewat WSL atau pip. Lebih cepat dijalankan, tetapi lingkungan berbeda dari CI.
Rekomendasi: A.
Selesai bila: CI hijau di 3.12 dan 3.13; `tests/fixtures/sarif/*.sarif` mencatat versi Semgrep di `tool.driver.version`; pytest lulus tanpa semgrep di PATH.

## Sedang

R-06: valid. Fase 3 ambigu: kolom "hanya LLM" di bagian 7 mengandaikan mode deteksi LLM tanpa scanner, yang tidak ada di arsitektur. Definisi positif juga belum ada (bagaimana `uncertain` dihitung, apa itu TP retention, toleransi baris).
Opsi A: v1 mengukur triase saja: prediksi positif = `likely_tp` atau `uncertain` (varian ketat: hanya `likely_tp`), TP retention = TP scanner yang tidak diberi `likely_fp` / semua TP scanner, per kategori. "Hanya LLM" dikeluarkan dari v1 atau ditandai roadmap.
Opsi B: tambah mode deteksi LLM. Biaya tinggi, di luar G1 sampai G7.
Rekomendasi: A, ditulis di `docs/EVAL-PITFALLS.md` dan diverifikasi literature-advisor di Fase 3.
Selesai bila: tes metrik kasus hitung tangan mencakup `uncertain` di kedua varian dan toleransi baris yang dikonfigurasi.

R-07: valid. Tabel keluarga CWE (I-05) belum punya sumber. Selain itu `cwe` tunggal, padahal aturan Semgrep sering memuat beberapa CWE.
Opsi A: `cwe: list[str]`, keluarga diturunkan dari hierarki MITRE CWE (view 1000) ditambah daftar pasangan manual (862/863) di `config/cwe-families.yaml`. Keputusan teknik.
Opsi B: daftar manual saja. Cepat, sulit dipertahankan.
Rekomendasi: A.
Selesai bila: tes Fase 2: 862 dan 863 satu keluarga di varian longgar, berbeda di ketat; temuan multi-CWE tidak hilang CWE-nya.

R-08: valid. PoC benchmark Fase 3 berjalan di mana belum jelas. I-08 berlaku untuk sandbox, tetapi PoC benchmark juga kode serang.
Opsi A: PoC benchmark dijalankan di Docker dengan `--network none` antar container target dan PoC, sejak Fase 3. Opsi B: jalankan di host, pindah ke sandbox di Fase 7.
Rekomendasi: A, tes egress dini mengurangi risiko Fase 7.
Selesai bila: gerbang Fase 3 menjalankan PoC hanya lewat `docker compose` dengan jaringan internal.

R-09: valid. Audit log berantai hash tidak mendeteksi pemotongan ekor dan kanonisasi JSON tidak ditentukan.
Opsi A: hash atas JSON kanonis (kunci terurut, UTF-8, tanpa spasi), hash kepala disimpan di metadata run. Opsi B: hanya rantai. Rekomendasi: A.
Selesai bila: tes mendeteksi baris diubah, dihapus di tengah, dan dipotong di ekor.

## Rendah

R-10: valid. DESIGN-TRACE lengkap secara format, tetapi semua `seed`, catatan belum ada, dan pdf-map tidak menemukan PDF untuk purba-2023, koterba-2026, gnieciak-2025. Baris D-05, D-09, D-10 tidak boleh naik ke `dicatat` tanpa PDF. Keputusan baru R-01, R-02, R-03, R-05, R-07, R-09 belum punya baris.
Rekomendasi: tambah D-20 sampai D-25 bertanda `teknik`; bila PDF tidak ada, tandai dasar "belum diketahui" dan catat di O-02.
Selesai bila: gerbang Fase 0 butir 6 dan 7 lulus.

R-11: valid. Field `effort: medium` (A-07) dan cakupan hook di subagent (A-11) belum diverifikasi; laporan ini tidak bisa memverifikasinya. Rekomendasi: orkestrator mencatat hasil uji di `reports/phase-0/`.

## Usulan teks untuk DECISIONS.md (belum diterapkan)

- Ubah A-02: "Inti ditulis dengan Python, `requires-python >=3.12`, diuji di 3.12 dan 3.13 (mesin pemilik 3.13)."
- Ubah A-03: tambah "Di Windows, Semgrep dijalankan lewat image Docker resmi dengan versi dipin. Tes hanya memakai fixture SARIF."
- A-14 baru: "Status lifecycle dan hasil verifikasi adalah dua field terpisah; `verified` diturunkan dari `verification.result == exploitable` (R-01)."
- A-15 baru: "Id Finding deterministik; duplikat disimpan dengan `duplicate_of`, tidak dibuang (R-02)."
- A-16 baru: "Setiap panggilan LLM dicatat sebagai entitas `LlmCall` di audit log, termasuk yang gagal (R-03)."
- A-17 baru: "Evaluasi v1 mengukur triase atas temuan scanner; deteksi tanpa scanner adalah roadmap (R-06)."
- A-18 baru: "Tafsiran I-10: larangan panggilan berbayar berlaku untuk tes dan pengembangan repo ini; pemakaian produk dibatasi `budget` (sementara, menunggu R-04)."
- O-05 baru: "Teks final I-10 untuk pemakaian produk (butuh persetujuan pemilik)."
- O-06 baru: "Dukungan Semgrep native di Windows: belum diketahui."
- Bagian K tidak perlu diubah.
