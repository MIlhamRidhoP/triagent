Verdict: PASS
Ringkasan: Fase 2 solid. Gerbang dan 209 tes lulus saat saya jalankan ulang, dedup tidak membuang temuan dan hasilnya independen urutan, tabel CWE cocok dengan XML MITRE v4.20 yang saya unduh ulang. Temuan hanya minor (tidak ada yang memblokir); beberapa perlu dicatat sebelum fase triase dan fase yang membaca berkas sumber.

Temuan (urut keparahan)
- R-01 [minor] src/triagent/ingest/sarif.py:295-299, 293
  Bukti: `file` dan `start_line` dari SARIF tidak divalidasi. Uji saya: uri `%FF%00../../x` menghasilkan `file='�\x00../../x'`, `startLine` 10^30 diterima apa adanya. `normalize_uri` tidak menolak `..`, NUL, atau path absolut.
  Dampak: Fase ini hanya menyimpan string (aman). Tetapi fase yang membaca konteks kode (3+/verifikasi) bila memakai `location.file` langsung bisa keluar dari akar repo. Perlu aturan "resolve di bawah root, tolak `..`/NUL" di pembaca berkas; catat di DECISIONS.
- R-02 [minor] src/triagent/ingest/sarif.py:199-208
  Bukti: `suppressions`, `baselineState`, `kind` pada result tidak dibaca. Result dengan `suppressions:[{kind:inSource}]` menjadi Finding aktif.
  Dampak: Alert yang sudah disuppress scanner ikut ditriase (bukan kehilangan temuan, jadi tidak melanggar I-01, tetapi menambah biaya LLM dan false positive). Catat sebagai batasan atau simpan flag.
- R-03 [minor] src/triagent/normalize/dedup.py:47-51
  Bukti: dua hit dari aturan sama pada baris sama tetapi kolom berbeda (dua sink pada satu baris) dianggap "bertumpuk persis" lalu duplikat; kolom tidak dipakai. Gerbang r9/r11 malah mengunci perilaku ini.
  Dampak: Temuan kedua tidak hilang (I-01 aman) tetapi tidak ditriase sendiri bila fase triase mewarisi verdict kanonik. Dev-report sudah mengakui risiko serupa; pastikan Fase 3 tidak mewarisi verdict tanpa pertimbangan.
- R-04 [minor] src/triagent/ingest/sarif.py:175-179, cli.py ingest
  Bukti: tidak ada batas ukuran masukan; berkas dibaca utuh (`read_bytes`) lalu `json.loads`. JSON bersarang dalam ditangani benar (RecursionError menjadi SarifError, diuji ulang), tetapi SARIF ratusan MB akan memakan memori. Stdout Docker juga tidak dibatasi.
  Dampak: DoS lokal saja; terima sebagai batas yang diketahui atau tambahkan batas ukuran.
- R-05 [minor] reports/phase-2/dev-report.md:35 vs src/triagent/normalize/data/cwe-families.yaml (meta.sha256_of)
  Bukti: laporan menyebut sha256 milik `cwec_v4.20.xml`; tabel mencatat `sha256_of: cwec.zip`. Saya unduh ulang zip dari cwe.mitre.org: sha256 `3976f599...7d50` identik dengan yang tercatat (jadi hash sah, hanya laporan yang keliru). Nama berkas `cwec.zip` juga berbeda dari contoh perintah di skrip pembangun (`cwec_v4.20.zip`).
  Dampak: kebingungan audit saja.

Keputusan tanpa jejak: tidak ada. D-31 sampai D-35 dan A-23 sampai A-27, O-09 ada. Catatan: PROVENANCE menyebut perintah dengan `--output`, sedangkan adapter membaca stdout dan `-v`, bukan `--mount readonly`; dev-report mengklaim satu run nyata identik dengan golden, tidak bisa saya verifikasi (butuh Docker dan jaringan), tidak ada di gerbang.

Hal yang saya periksa dan aman
- Gate 2 dan pytest (209 lulus) dijalankan ulang lewat .venv. Gerbang menguji perilaku: hitungan tangan 14 temuan, masukan diacak, hitungan independen dari parser, SARIF cacat dengan teks injeksi, pemeriksaan tanpa modul jaringan dan tanpa shell=True. Tes dedup mencakup rantai, urutan (seed), audit sekali per temuan; tidak ada tes yang selalu lulus ditemukan.
- I-01: `dedup` mempertahankan panjang dan urutan; `duplicate_of` hanya menunjuk kanonik (tidak ada rantai/siklus; kanonik diurut total dengan tie-break id; model menolak self-reference). Id unik dijaga.
- Id stabil terhadap pergeseran baris (kunci snippet, bukan nomor baris) dan terhadap urutan masukan; `fingerprints` placeholder Semgrep memang diabaikan, terkonfirmasi di fixture.
- Parser: JSON cacat, root bukan objek, versi salah, result bukan objek, level aneh, CWE-0, "not CWE-5" ditangani; teks bernada injeksi hanya disimpan (I-04).
- Adapter Semgrep: argumen list tanpa shell, image dipin digest, config dibatasi regex `^[pr]/...` (tak bisa menyisipkan flag), path mount ditolak bila ada koma/newline, mount readonly.
- Tabel CWE: dengan skrip independen atas XML v4.20 hasil unduhan ulang, 6 sampel acak (384->610, 180->20, 476->710, 843->704, 61->706, 90->943) plus 79->74, 89->943, 22->706, 352->345, 94->74, 502->913, 78->77, 601->610, 862/863->285 semuanya cocok aturan; semua target bertipe Class/Pillar; 934 entri.
- Fixture: SARIF nyata Semgrep 1.181.1 (4 result, baris 9/9/19/29 cocok app.js dan PROVENANCE, `semanticVersion`, uri `/src/app.js`). Tidak ada kunci, token, atau path mesin pribadi (kata "secret" hanya teks aturan). Tidak ada em dash di repo selain PDF literatur yang diabaikan git.
- Perubahan di luar lingkup: tidak ada (cli.py hanya menambah `ingest`).
