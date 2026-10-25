Verdict: REVISE
Ringkasan: Metrik, hitungan tangan gerbang, validator ground truth, dan pengerasan compose benar dan diuji perilakunya, bukan sekadar keberadaan berkas. Ada dua cacat mayor pada kualitas benchmark: satu kasus tumpang-tindih item yang nyata, sementara dev-report menyangkalnya, dan petunjuk label yang tidak bisa dihapus mutasi. Ada juga satu celah bukti isolasi.

Temuan (urut keparahan)
- R-01 [major] src/triagent/eval/metrics.py:52 dan :70-72; benchmark/ground-truth.yaml:150 (BM-011) dan :304 (BM-022)
  Bukti: BM-011 (tp, CWE-798, config.js 7-7) dan BM-022 (fp-trap, CWE-798, config.js 8-8) berjarak satu baris. Dengan toleransi bawaan 2, satu temuan di baris 7 atau 8 cocok dengan kedua item. Contoh: scanner menandai baris 8 dan triase dengan benar memberi `likely_fp`. Hasilnya BM-022=tn, tetapi BM-011=fn_lost, padahal scanner tidak pernah menunjuk token asli. Sebaliknya, `likely_tp` pada baris 7 menghasilkan BM-011=tp sekaligus BM-022=fp. dev-report-b.md:17 menulis "belum ada kasus nyata", dan klaim itu keliru.
  Dampak: TP retention dan FPR kategori hardcoded-secret bisa salah di run nyata. Perbaiki dengan pencocokan satu-ke-satu (item terdekat), atau pisahkan item ke baris yang berjauhan, lalu tambahkan kasus tangan di gerbang.
- R-02 [major] benchmark/app/routes/links.js:12, :47; routes/tools.js:14
  Bukti: Rute jebakan diberi nama `/go-safe`, `/preview-safe`, dan `/tools/echo-safe`. Nama itu literal string, jadi mutasi `rename` tidak menyentuhnya (jsmini.rewrite hanya mengganti identifier). Nama properti seperti `merge.settings`, `authz.owner`, dan `html.escape` juga tetap di varian. Ini persis P5 (petunjuk nama) di EVAL-PITFALLS.
  Dampak: Model bisa menebak label jebakan dari nama rute tanpa memahami kode, sehingga presisi triase membengkak di semua varian. Ganti dengan nama yang netral dan catat batas rename properti di benchmark/mutate/README.md.
- R-03 [major] benchmark/poc/_selftest.js:69-73; src/triagent/benchmark/poc.py:219-226
  Bukti: Selftest hanya menguji 1.1.1.1:443, 8.8.8.8:53, dan DNS example.com dari kontainer `poc`. Host Docker tidak diuji: `host.docker.internal`, IP gateway jaringan, dan port daemon 2375 tidak dicoba. Kontainer `app`, tempat RCE BM-005/006 berjalan, hanya diperiksa statis (non-root, read-only).
  Dampak: Klaim bahwa PoC tidak bisa menyentuh host (SPEC, ancaman sandbox escape) belum terbukti, padahal infrastruktur ini akan dipakai ulang untuk PoC buatan LLM. Tambahkan probe ke host atau gateway dan jalankan probe yang sama dari kontainer app.
- R-04 [minor] benchmark/app/routes/notes.js:18-28; server.js:45-47
  Bukti: `GET /notes/:id` tidak memakai `requireLogin` maupun pemeriksaan pemilik, padahal catatan punya `ownerId`. Ini kerentanan otorisasi (CWE-862/639) yang tidak berlabel. Error handler juga mengirim `err.message` (CWE-209).
  Dampak: Temuan yang benar di sini jatuh ke `unlabeled_findings`, sehingga ground truth tidak lengkap. Beri label, atau dokumentasikan bahwa rute ini memang publik.
- R-05 [minor] src/triagent/eval/metrics.py:43-50
  Bukti: `_norm_path` hanya membuang `./`. Path SARIF dari Semgrep yang dijalankan di root repo (`benchmark/app/routes/x.js`) tidak akan pernah cocok, dan tidak ada peringatan bila nol temuan cocok. Temuan dengan `duplicate_of` juga ikut dihitung. Gerbang hanya menguji kasus `duplicate_of is None`.
  Dampak: Run Fase 4 bisa diam-diam melaporkan semua item sebagai fn_missed. Tambahkan opsi prefix atau root, peringatan "0 matched", dan lewati temuan duplikat.
- R-06 [minor] src/triagent/eval/run.py:167
  Bukti: `**meta` menyalin semua kunci rekaman ke report.json tanpa daftar putih.
  Dampak: Field liar di rekaman, misalnya kredensial atau path pribadi, ikut ke laporan (I-09). Batasi ke REQUIRED_META ditambah kunci opsional yang dikenal.
- R-07 [minor] benchmark/docker/Dockerfile:4; poc.py:62-66
  Bukti: Base image `node:20-alpine` tidak di-pin ke digest, dan tag image hanya di-hash dari Dockerfile dan lock npm.
  Dampak: Mesin yang berbeda bisa menjalankan runtime berbeda dengan tag yang sama, sehingga reprodusibilitas label PoC menurun.

Keputusan tanpa jejak: tidak ada. Hal yang belum lengkap: aturan "satu temuan dihitung untuk banyak item" sudah disebut di dev-report-b tetapi belum ada di A-29 maupun D-42.

Hal yang diperiksa dan aman:
- Hitung ulang tangan gerbang B1, semuanya cocok: T=2 longgar dan ketat x uncertain positif dan negatif, basis scanner-saja (4/7, 0.8, FPR 1.0), all-fp (precision null, retention 0).
- Pembagian nol menghasilkan `None`. fn_missed dikeluarkan dari retention dan not_flagged dari FPR, sesuai A-29c.
- Sampel ground truth: BM-003, 004, 013, 015, 016, 017, 019, 020, 021, 022, dan 023. Baris, CWE, dan label sesuai kode. Jebakan 017, 019, 020, dan 023 memang aman.
- PoC punya kontrol positif, dan kode 2 dicatat sebagai galat harness. Untuk jebakan, `attempts>=1` dan bukti wajib. Aplikasi di-restart per PoC, jadi pencemaran prototype dari BM-013 tidak bocor ke BM-023. Kontrol tambal BM-001 menguji sensitivitas PoC.
- Pengerasan compose: semua jaringan internal, tanpa port, read_only, cap_drop ALL, no-new-privileges, user 1000, mount ro, batas sumber daya. Aplikasi menolak start tanpa BENCHMARK_SANDBOX dan bawaannya mengikat 127.0.0.1.
- Rename oleh mutasi melewati properti, kunci objek, shorthand, dan nama yang direservasi. PoC dijalankan pada dua varian.
- I-10: modul eval dan benchmark tidak mengimpor jaringan atau SDK. pytest 244 lulus offline, ruff bersih. Catatan: build image pertama butuh registry, dan ini sudah diungkap.
- EVAL-PITFALLS tidak menyalin angka paper. Tidak ada em dash, kunci, atau path pribadi.
