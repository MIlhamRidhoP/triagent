Verdict: PASS
Ringkasan: R-01 sampai R-07 sudah diterapkan sesuai resolution.md dan saya uji sendiri. Hasilnya benar, dan selftest dua kontainer sungguh berjalan. Tersisa tiga temuan minor yang tidak menggugurkan perbaikan.

Temuan (urut keparahan)
- R-01 [minor] benchmark/app/README.md:9; src/triagent/benchmark/hints.py:55
  Bukti: README di dalam `app/` menyebut "the stored XSS item (BM-002)", lalu ikut tersalin ke tiap varian (mutate.py menyalin semua berkas app). check-names hanya memindai isi `.js`. Isi `.md`, `.json`, dan literal regex (fixture `/notsafe/` saya lolos) tidak diperiksa.
  Dampak: Bila Fase 4 memberi konteks repo ke model, label bocor (P5). Sebaiknya README dipindah ke luar `app/`, atau check-names juga memindai berkas non-JS.
- R-02 [minor] src/triagent/eval/metrics.py:55
  Bukti: Pencocokan prefix tidak memeriksa batas segmen path. `normalize_path("benchmark/application/x.js", ["benchmark/app"])` menghasilkan `lication/x.js`.
  Dampak: Path bisa diam-diam salah bila prefix ditulis tanpa `/`. Cocokkan hanya pada batas `/`.
- R-03 [minor] benchmark/ground-truth.yaml:128-129 (BM-009)
  Bukti: Rentang BM-009 dipersempit ke baris 8 supaya lolos validator jarak. Sink `res.json(ticket)` ada di tickets.js:13, berjarak 5, jadi di luar toleransi 2. Temuan yang menunjuk sink itu kini jatuh ke `unlabeled_findings`.
  Dampak: Recall pencocokan untuk IDOR bisa turun. Setelah pencocokan satu-ke-satu berlaku, validator ini terlalu ketat untuk item dengan rentang sink.

Keputusan tanpa jejak: tidak ada. Satu-ke-satu, check-names, whitelist meta, dan digest sudah tercatat di EVAL-PITFALLS, README, dan A-29/D-42.

Hal yang diperiksa dan aman:
- Satu-ke-satu, diuji dengan kasus tangan sendiri. (a) Item 7 dan 9 dengan temuan di 8 berjarak sama, jadi tie-break memilih id terkecil, sama untuk kedua urutan GT. (b) Mode longgar memilih jarak dulu (famili di jarak 0 mengalahkan ketat di jarak 1), sedangkan mode ketat memilih item ketat. (c) Dua temuan pada item berbeda dan uncertain dua arah sesuai definisi.
- Duplikat dilewati (`duplicates_skipped=1`, tidak menambah matched maupun unlabeled). Peringatan nol-cocok muncul.
- Validator jarak memakai `combinations` dan menandai tumpang-tindih (gap negatif). Benchmark asli dan varian seed 1, 2, 7 valid.
- check-names lulus pada aplikasi dan tiga varian. Rute netral (`/jump`, `/card`, `/tools/say`). Fixture `isVulnerable`, template `SAFE`, dan `'FP_case'` tertangkap.
- Selftest saya jalankan: 13 kunci True di `poc` dan `app`, gateway 172.20.0.1. `control_reachable` dan `error_no_leak` (login, lalu 500 generik) membuktikan probe benar-benar berjalan. Kunci yang hilang menjadi False (`parse_selftest`).
- Digest `sha256:fb4cd12c...` cocok dengan RepoDigest lokal `node:20-alpine`. `image_id` dan `base_image_digest` dicatat.
- R-06: hanya REQUIRED dan OPTIONAL yang ditulis, kunci lain hanya namanya. R-04: handler 500 mengirim `internal error`.
- Regresi BM-011, 014, 022: anchor, baris, dan CWE sesuai kode. Gerbang PoC lulus. pytest 258 lulus, ruff check dan format bersih.
