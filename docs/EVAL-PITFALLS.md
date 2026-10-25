# EVAL-PITFALLS: daftar periksa evaluasi triagent

Dasar: catatan `docs/literature/notes/chasing-shadows-2026.md` (P1 sampai P9, definisi dari
Lampiran B paper itu, sudah dicek ke PDF) dan `reports/phase-3/lit-eval-design.md`. Setiap run
evaluasi resmi harus melewati daftar ini dan menyimpan metadata di `report.json`. Angka dari
paper tidak disalin ke sini; hanya definisi dan arahan.

## Jebakan P1 sampai P9

### P1 Keracunan data lewat scraping
Data latih diambil dari internet tanpa penyaringan sehingga bisa diracuni. Tidak berlaku
langsung untuk triagent karena kita memakai model terkelola dan tidak melatih model. Dicatat
sebagai tidak berlaku.

### P2 Label buatan LLM tanpa validasi
Label tidak akurat yang dihasilkan LLM tanpa validasi. Pengendali: label ground truth benchmark
bersumber dari PoC yang dijalankan (`label_source: poc`), bukan dari LLM, dan pelabelnya dicatat
(`labeled_by`). Risiko sisa: pelabel tunggal (lihat A-28).

### P3 Kebocoran data
Informasi data uji ada di data latih model. Pengendali: korpus baru buatan sendiri (`fieldnotes-bench`),
tanggal korpus tercatat di `corpus_date` dan di metadata run, dan tanggalnya dibandingkan dengan
batas pelatihan model yang diuji. Varian mutasi (ganti nama, hapus komentar) dipakai untuk melihat
seberapa besar hasil bergantung pada teks yang mungkin dihafal. Hasil pada aplikasi rentan terkenal
tidak boleh disejajarkan dengan hasil pada benchmark ini.

### P4 Model collapse akibat data latih sintetis
Model dilatih pada data sintetis hasil model. Tidak berlaku karena tidak ada pelatihan. Dicatat
sebagai tidak berlaku.

### P5 Korelasi palsu atau fitur tak relevan
Model memakai petunjuk yang tidak relevan, termasuk petunjuk seperti nama variabel. Pengendali:
nama berkas dan variabel benchmark diperiksa agar tidak membocorkan jawaban, komentar bingkai
(`comment_framing`) sengaja ada untuk mengukur pengaruhnya, dan uji mutasi menghapus komentar dan
mengganti nama untuk membandingkan hasil.

### P6 Pemotongan konteks
Masukan dipotong oleh batas konteks sehingga model tidak melihat seluruh bukti. Pengendali:
batas konteks dicatat (`context_limit_tokens`) dan jumlah panggilan yang terpotong dicatat
(`context_truncated_calls`).

### P7 Sensitivitas prompt
Satu prompt tetap dipakai untuk semua model tanpa justifikasi atau variasi. Pengendali: hash
prompt dicatat (`prompt_hash`), prompt dibekukan sebelum run resmi, satu prompt untuk semua model
harus dijustifikasi dan ditambah satu varian pembanding. Aturan pembekuan adalah keputusan teknik.

### P8 Kekeliruan proksi
Klaim digeneralisasi ke model, bahasa, atau scanner yang tidak diuji. Pengendali: klaim hanya
untuk model, scanner (Semgrep OSS), bahasa (JavaScript) dan korpus yang benar-benar diuji.
Metadata run menyebut semuanya.

### P9 Ambiguitas model
ID model, snapshot, commit, kuantisasi tidak lengkap, atau tidak jelas lewat API atau web.
Pengendali: `triagent eval run` menolak rekaman tanpa `model_id`, `model_snapshot`, `api_route`,
`scanner_version`, `ruleset`, `prompt_hash`, `temperature`, `context_limit_tokens`, `corpus_date`.
Versi triagent dan hash ground truth dicatat otomatis.

## Metadata wajib per run (`report.json`, bagian `metadata`)
`model_id`, `model_snapshot`, `api_route`, `scanner`, `scanner_version`, `ruleset`, `prompt_hash`,
`temperature`, `context_limit_tokens`, `corpus_date`, `label_source`, `ground_truth_sha256`,
`triagent_version`, `mode`, `line_tolerance`, `context_truncated_calls` (sumber label: PoC); plus `cost` dan
`latency` dari catatan panggilan (I-06).

## Definisi metrik (resolusi R-06: v1 mengukur triase atas temuan scanner)
- **Cocok**: berkas sama, rentang baris bertumpuk setelah item dilebarkan `toleransi baris`
  (dikonfigurasi, bawaan 2), dan CWE sama. Varian **ketat**: id CWE persis sama. Varian
  **longgar**: keluarga CWE sama (tabel `normalize/cwe.py`, I-05). Keduanya dilaporkan bersamaan.
- **Prediksi positif**: `likely_tp`; `uncertain` dihitung positif pada varian
  `uncertain_positive` dan negatif pada `uncertain_negative`. Keduanya dilaporkan. Perlakuan
  `uncertain` adalah keputusan teknik.
- **Item TP**: tanpa temuan cocok adalah `fn_missed` (scanner meleset); ada temuan positif
  adalah `tp`; semua temuan cocok negatif adalah `fn_lost` (triase membuang TP).
- **Item jebakan FP**: tanpa temuan cocok adalah `not_flagged` (di luar FP dan TN); ada temuan
  positif adalah `fp`; semua negatif adalah `tn`.
- precision = tp/(tp+fp); recall = tp/(tp+fn); F1 = 2tp/(2tp+fp+fn); FPR = fp/(fp+tn);
  **TP retention** = tp/(tp+fn_lost), hanya atas TP yang terdeteksi scanner, juga per kategori.
  Rasio dengan penyebut nol bernilai `null`.
- **Pencocokan satu-ke-satu**: satu temuan diberikan ke paling banyak satu item, dipilih menurut jarak baris terkecil, lalu CWE ketat sebelum keluarga, lalu id item terkecil. Satu temuan adalah satu prediksi; dihitung untuk dua item akan menggelembungkan TP dan FP. Temuan dengan `duplicate_of` dilewati. Gunakan `--strip-prefix` agar path SARIF cocok dengan path ground truth; laporan memuat `matched_findings_total` dan peringatan bila nol temuan cocok.
- **Petunjuk label pada nama (P5)**: `triagent benchmark check-names` menolak kata safe, trap, vuln, secure, benign, exploit, fp, tp pada identifier, literal string, dan nama berkas (kode tanpa komentar) di aplikasi dan semua varian mutasi. Rename mutasi tidak menyentuh properti, kunci objek, dan literal string.
- **Metadata rekaman**: hanya kunci wajib dan opsional yang terdokumentasi masuk laporan; kunci lain dibuang dan namanya dicatat di `dropped_meta_keys`.
- **Temuan tidak terlabel**: temuan yang tidak cocok item mana pun dilaporkan di
  `unlabeled_findings`, tidak dihitung sebagai FP; adjudikasi manual dilakukan di berkas terpisah
  (keputusan teknik).
- **Kestabilan**: minimal tiga run per konfigurasi, laporkan sebaran. Ambang kestabilan adalah
  keputusan teknik (A-29), bukan angka dari paper.
- **Baris dasar**: tanpa `--verdicts`, semua temuan dianggap positif (scanner saja).

## Angka dan klaim yang tidak boleh dipakai
- Jangan membandingkan langsung F1 atau presisi kita dengan paper lain: definisi dan ground truth
  berbeda, dan sebagian memakai metrik per proyek, bukan per alert.
- Jangan memakai angka "identifikasi FP" yang presisinya rendah, angka serangan bias yang
  mencampur kasus lolos baseline, FDR IRIS sebagai presisi, angka dari sampel sangat kecil,
  klaim "LLM mengalahkan SAST" tanpa uji signifikansi, atau angka produk vendor.
- Tabel I dan II di chasing-shadows-2026 bukan kinerja deteksi kerentanan. Angka per sel
  koterba-2026 tidak aman dikutip. Definisi kolom di Tabel 4 sifting-noise-2026 dan definisi
  macro-F1 frontier-llms-2026 belum diverifikasi.
- Jangan menyejajarkan hasil pada aplikasi OWASP (kemungkinan terlatih) dengan hasil pada
  benchmark baru, dan jangan menggeneralisasi ke model, bahasa, atau scanner yang tidak diuji.
- Selisih kecil antar konfigurasi tidak diklaim tanpa sebaran antar run.
