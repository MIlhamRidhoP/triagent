# Resolusi Fase 3, siklus 1

Semua keputusan di bawah adalah keputusan teknik, tanpa dasar literatur khusus. Tidak ada yang menyentuh Invarian atau bagian K, jadi tidak perlu persetujuan pemilik.

R-01: valid. Dengan toleransi 2, satu temuan di config.js baris 7 atau 8 cocok ke BM-011 dan BM-022 sekaligus. Klaim "belum ada kasus nyata" di dev-report-b keliru.
Opsi A: hanya memisahkan lokasi item. Murah, tetapi rapuh, karena tumpang-tindih bisa muncul lagi lewat mutasi atau item baru.
Opsi B: pencocokan satu-ke-satu di metrics.py. Setiap temuan diberikan ke paling banyak satu item, dipilih menurut jarak baris terkecil (0 bila rentang bertumpuk), lalu CWE ketat sebelum famili, lalu id item terkecil. Ditambah validator ground truth yang menolak dua item di berkas yang sama dengan famili CWE yang sama bila jaraknya kurang dari atau sama dengan 2 x toleransi + 1.
Rekomendasi: B. BM-022 (exampleToken) juga dipindah supaya lolos validator, misalnya ke berkas lain, lalu PoC BM-011/022 diulang dan anchor diperbarui. Secara metrik, B lebih benar. Satu temuan adalah satu prediksi, jadi kalau dihitung dua kali, TP dan FP sama-sama menggelembung. Catat aturan ini di A-29, D-42, dan EVAL-PITFALLS.
Selesai bila: ada tes unit yang membuktikan empat hal. Temuan baris 8 dengan `likely_fp` menghasilkan BM-022=tn dan BM-011=fn_missed. Temuan baris 7 dengan `likely_tp` menghasilkan BM-011=tp dan BM-022=not_flagged. Temuan yang berjarak sama memakai tie-break deterministik. Ground truth sintetis dengan dua item berdekatan ditolak validator. Gerbang juga menghitung ulang kasus ini dengan tangan.

R-02: sebagian. Bagian yang valid: nama rute `/go-safe`, `/preview-safe`, dan `/tools/echo-safe` adalah petunjuk label (P5) dan tidak tersentuh mutasi. Bagian yang tidak valid: nama properti `html.escape`, `authz.owner`, dan `merge.settings` adalah sinyal semantik yang wajar di kode nyata, dan model memang seharusnya membacanya.
Opsi A: ganti nama rute jebakan saja, tanpa pemeriksaan. Murah, tetapi bisa terulang.
Opsi B: ganti dengan nama netral yang setara dengan rute TP pasangannya (contoh `/jump`, `/card`, `/tools/say`), lalu tambahkan pemeriksaan otomatis.
Rekomendasi: B. Pemeriksaan berjalan pada kode yang komentarnya sudah dibuang (bingkai komentar memang disengaja), untuk aplikasi asli dan semua varian mutasi. Regex tak peka huruf mencari `safe|unsafe|trap|vuln|insecure|secure|benign|exploit|fp|tp`, baik sebagai kata utuh maupun bagian camelCase atau kebab-case, pada identifier, literal string, dan nama berkas. Daftar izin dibuat eksplisit per berkas:baris dan hanya untuk banner serta pesan penolakan di server.js. Catat di benchmark/mutate/README.md bahwa rename tidak menyentuh properti, kunci objek, dan literal string.
Selesai bila: pemeriksaan gagal pada fixture yang berisi `/x-safe` atau `trapHandler`, lulus pada aplikasi dan semua varian, dan dipanggil oleh gerbang.

R-03: valid. Selftest belum membuktikan bahwa host tidak terjangkau, dan kontainer app sama sekali belum diprobe.
Opsi A: tambah probe di selftest poc saja. Murah, tetapi app, tempat RCE BM-005/006 berjalan, tetap tidak teruji.
Opsi B: salin _selftest.js ke dalam image (COPY ke /opt/selftest), lalu jalankan di poc dan lewat `docker compose exec app`. Probe tambahan:
- tidak ada default route di /proc/net/route;
- TCP ke IP gateway jaringan bench gagal pada port 22, 80, 2375, 2376, dan 3000 (IP diambil host lewat `docker network inspect`, dikirim lewat env);
- TCP ke 172.17.0.1:2375 gagal;
- DNS `host.docker.internal` dan `gateway.docker.internal` gagal;
- 169.254.169.254:80 terblokir;
- /var/run/docker.sock tidak ada.
Kontrol positif: poc ke app:3000 dan app ke 127.0.0.1:3000 harus berhasil.
Rekomendasi: B.
Selesai bila: selftest.json memuat hasil per kontainer (`poc`, `app`) dengan himpunan kunci yang persis sama dengan yang diharapkan. Gerbang gagal bila ada kunci yang hilang, ada kunci isolasi bernilai false, atau kontrol positif bernilai false. Tes unit pada parser hasil membuktikan bahwa kunci yang hilang dianggap gagal.

R-04: valid, wajib karena murah. Opsi A: beri label baru (perlu PoC dan kategori baru). Opsi B: ubah error handler supaya mengirim pesan generik (`internal error`), dan tulis di benchmark/app/README.md bahwa `GET /notes/:id` memang publik by design (catatan berbagi, syarat stored XSS BM-002). Rekomendasi: B, karena ini kerentanan yang tidak disengaja, bukan bagian desain. Selesai bila: tes atau PoC menunjukkan respons 500 tidak memuat `err.message`, dan README punya bagian tentang perilaku publik yang tidak dilabel.

R-05: valid, wajib karena Fase 4 bergantung padanya. Opsi A: hanya menambah peringatan. Opsi B: opsi `--strip-prefix` (boleh berulang) di score dan run. Temuan dengan `duplicate_of` dilewati dan dihitung di `duplicates_skipped`. Laporan memuat `matched_findings_total`. Ada peringatan di stderr bila nol temuan cocok padahal temuan ada. Rekomendasi: B. Selesai bila: tes membuktikan path `benchmark/app/routes/x.js` cocok setelah strip, duplikat tidak menambah tp, fp, maupun unlabeled, dan peringatan muncul pada kasus nol cocok. Gerbang menambah kasus tangan yang memuat duplikat.

R-06: valid, wajib. Opsi A: tolak rekaman yang punya kunci tak dikenal. Opsi B: daftar putih berisi REQUIRED_META ditambah kunci opsional yang terdokumentasi. Kunci lain dibuang, dan hanya namanya yang dicatat di `dropped_meta_keys`. Rekomendasi: B, karena rekaman lama tetap terbaca dan nilai liar tidak pernah ditulis. Selesai bila: tes dengan kunci `api_key` di meta menghasilkan report.json tanpa nilai itu.

R-07: sebagian, wajib sebagian. Opsi A: pin base image ke `node:20-alpine@sha256:...` dengan digest dari `docker image inspect` lokal (jangan dikarang), lalu masukkan digest ke hash tag. Opsi B: hanya catat image ID dan RepoDigest base di hasil PoC. Rekomendasi: A dan B sekaligus. Bila digest tidak bisa diperoleh, cukup B, lalu catat sebagai pertanyaan terbuka di DECISIONS. Selesai bila: Dockerfile memakai digest, dan hasil PoC memuat `base_image_digest`.

## Perubahan gerbang wajib (phase-3.sh)
1. Kasus tangan satu-ke-satu R-01 dan validator jarak antar item.
2. Pemeriksaan nama netral R-02 pada aplikasi dan semua varian.
3. Selftest dua kontainer dengan himpunan kunci tetap (R-03).
4. Kasus strip-prefix, duplikat, dan nol-cocok (R-05), serta daftar putih meta (R-06).
5. Grep Dockerfile untuk `@sha256:`, atau periksa adanya entri pertanyaan terbuka untuk R-07.
