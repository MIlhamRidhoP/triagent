# Dasar literatur: desain benchmark dan harness evaluasi triase (Fase 3)

Pertanyaan: metrik, protokol, isi metadata run dan EVAL-PITFALLS.md, dan batas klaim dari angka paper lain.

Jawaban singkat: Literatur mendukung (a) FPR/sisa FPR dan TP retention per kategori CWE sebagai metrik utama triase, (b) pencatatan model persis, lebih dari satu varian prompt, kontrol kontaminasi, validasi label tanpa LLM, (c) pemetaan CWE longgar lewat hierarki, dan (d) bukti eksekusi sebagai penentu status. Literatur tidak menentukan jumlah run, ambang kestabilan, perlakuan verdict uncertain, uji mutasi, atau jebakan FP yang disengaja sebagai prosedur; itu keputusan teknik. Semua catatan yang dipakai berstatus dicek ke PDF (tidak ada yang seed).

## Dasar

(1) Metrik
- sifting-noise-2026 (dicek ke PDF): FPR diukur sebagai porsi kasus tidak rentan yang tetap ditandai (baseline gabungan SAST 98,3%, sisa FPR setelah agen 6,3%; Tabel 3). TP retention dilaporkan per CWE: miss rate rendah untuk kelas injeksi, tinggi untuk CWE-327/328/501/614 (bagian 5.2). Mendukung TP retention per kategori dan larangan membuang temuan otomatis (D-02). Definisi kolom "Iden. FP" dan "Corr. Ret." di Tabel 4 belum dicek, jangan ditiru.
- sifting-noise-2026: dua metrik berbeda dilaporkan terpisah (penurunan FPR versus TP retention), menunjukkan FPR saja tidak cukup. Dukungan untuk melaporkan keduanya berdampingan.
- tamberg-bahsi-2025 (dicek ke PDF): presisi, recall, F1 dihitung dari TP/FP/TN/FN (Tabel 1). Pemetaan CWE mengikuti hierarki CWE-1000 (induk dan anak dihitung benar, bagian III). Mendukung varian longgar per keluarga CWE.
- frontier-llms-2026 (dicek ke PDF, preprint): CWE yang sering tertukar (862/863, 327/798, 918/601; bagian 5.4) dan taksonomi temuan non-aksi (bagian 3.2). Mendukung varian longgar per keluarga dan kategori non-TP. Definisi macro-F1 belum diverifikasi.
- huynh-uwa (dicek ke PDF, naskah tanpa venue): penentuan tipe CWE oleh LLM lemah, dan skenario salah CWE tetap dihitung benar memberi hasil lebih tinggi. Mendukung pelaporan ketat dan longgar secara terpisah, bukan memilih satu.
- Verdict uncertain: tidak ada dukungan di catatan. Keputusan teknik.
- Definisi ketat versus longgar secara operasional dan pembagian keluarga CWE triagent: hanya prinsip yang didukung; rinciannya keputusan teknik.

(2) Protokol
- Banyak varian prompt: chasing-shadows-2026 P7 (satu prompt tetap tanpa justifikasi atau variasi). Pembekuan prompt per run didukung secara tidak langsung (menghindari prompt berubah diam-diam), tetapi catatan hanya mengharuskan justifikasi atau variasi; aturan pembekuan = keputusan teknik.
- Kontaminasi: chasing-shadows-2026 P3 (65,2% paper terkena atau mungkin terkena, hlm. 6 sampai 7) dan saran memakai korpus baru (D-15). sifting-noise-2026 memakai alert OSS-Fuzz pasca batas pelatihan dan menandai OWASP sebagai kemungkinan terlatih. koterba-2026 dan tamberg-bahsi-2025 mengakui risiko yang sama pada OWASP/Juliet (tamberg memitigasi dengan penamaan ulang). Mendukung korpus baru dan pemisahan benchmark sintetis dari hasil utama.
- Validasi label tanpa LLM: chasing-shadows-2026 P2. Ground truth manual penulis punya risiko sirkularitas atau bias (anggoman-2025; sifting-noise-2026 menyebut label Vul4J sebagian besar dari penulis pertama). Mendukung label dari PoC atau commit patch dan pencatatan siapa melabeli.
- Kestabilan antar run dan jumlah run: sifting-noise-2026 hanya memakai temperature 0 sebagai mitigasi; tamberg-bahsi-2025 juga temperature 0. Tidak ada angka kestabilan di catatan. Jumlah run dan ukuran sebaran = keputusan teknik. tamberg-bahsi-2025 dan gnieciak-2025 mencatat selisih kecil tanpa interval kepercayaan, dasar untuk melaporkan sebaran dan tidak mengklaim selisih kecil.
- Jebakan FP disengaja: sifting-noise-2026 (dicek ke PDF) menyebut tiga mode gagal (FM1 atribusi CWE salah, FM2 model ancaman terlalu konservatif, FM3 pencocokan pola permukaan) sebagai calon kasus uji. Jebakan bingkai: contextual-bias-2026 (preprint) menunjukkan bingkai "bebas bug" menurunkan deteksi GPT-4o-mini dari 97,2% ke 3,6% (Tabel II) dan redaksi metadata memulihkan sebagian; mendukung kasus uji komentar/PR yang menyesatkan.
- Uji mutasi: tidak ada dukungan di catatan. Keputusan teknik. Terkait P5 (petunjuk seperti nama variabel) hanya sebagai alasan mengubah nama, dan tamberg-bahsi-2025 memakai penamaan ulang untuk kontaminasi.
- Temuan di luar ground truth: koterba-2026 tidak menghitung temuan di luar 11 kelas; iris-2025 mencatat FDR adalah batas atas karena kerentanan nyata belum dikenal bisa terhitung FP; contextual-bias-2026 mencatat sebagian FPR adalah bug asli lain. Mendukung memisahkan "tidak terlabel" dari "salah", bukan menghitungnya FP langsung. Prosedur adjudikasinya keputusan teknik.

(3) Metadata run dan EVAL-PITFALLS.md (chasing-shadows-2026, bagian Angka aman dikutip dan Implikasi)
- P1 data latih diracuni scraping: tidak relevan langsung untuk pemakaian model terkelola, cukup catat sebagai tidak berlaku.
- P2 label LLM tanpa validasi: label ground truth harus bersumber bukan-LLM, catat sumber label.
- P3 kebocoran data: catat tanggal/sumber korpus dan hubungannya dengan batas pelatihan model.
- P4 model collapse data sintetis: tidak berlaku bila tidak ada pelatihan; tulis tidak berlaku.
- P5 korelasi palsu, termasuk petunjuk seperti nama variabel: periksa nama berkas/variabel pada korpus.
- P6 pemotongan konteks: catat batas konteks dan apakah ada pemotongan per kasus.
- P7 sensitivitas prompt: catat versi/hash prompt dan jalankan lebih dari satu varian.
- P8 kekeliruan proksi (generalisasi ke model yang tidak diuji): klaim hanya untuk model yang diuji.
- P9 ambiguitas model: catat ID model, snapshot, jalur (API atau web), versi alat, commit. Prevalensi 73,6% ditambah 12,5% parsial, tidak ada yang membahas (hlm. 7 sampai 8). Contoh recall tiga snapshot berbeda (Tabel I) adalah tugas non-keamanan.
- Tambahan non-P didukung catatan lain: versi scanner dan rule set (koterba-2026 mencatat versi Semgrep tidak terlihat; anggoman-2025 versi alat tidak disebut), biaya dan waktu per run (koterba-2026, tamberg-bahsi-2025, gnieciak-2025), temperature (sifting-noise-2026).

(4) Yang tidak boleh diklaim dari angka paper lain
- Jangan membandingkan langsung dengan F1 atau presisi paper lain: gnieciak-2025 dan sifting-noise-2026 menyatakan definisi dan ground truth berbeda; iris-2025 memakai metrik per proyek, bukan per alert.
- Jangan memakai 93,3% "FP identification" (presisi hanya 70,0%), 97% serangan bias (mencampur kasus lolos baseline), FDR 84,82% IRIS sebagai presisi, "0 persen" anggoman (n = 4), klaim "LLM mengalahkan SAST" (selisih kecil, tanpa signifikansi), dan angka produk penulis di frontier-llms-2026 (vendor, kebocoran data latih).
- Angka Tabel I dan II di chasing-shadows-2026 bukan kinerja deteksi kerentanan. Angka per sel Tabel 4 koterba-2026 tidak aman.
- Hasil OWASP (kemungkinan terlatih) jangan disejajarkan dengan hasil pada aplikasi baru (sifting-noise-2026).
- Jangan menggeneralisasi ke model, bahasa, atau SAST yang tidak diuji (P8; iris-2025 hanya CodeQL dan Java).

## Celah
Tidak ada dukungan di catatan untuk: perlakuan verdict uncertain, jumlah run dan ambang kestabilan, aturan pembekuan prompt, uji mutasi, prosedur adjudikasi temuan di luar ground truth, rumus ketat/longgar per keluarga CWE, ukuran sampel minimum. Tidak ada pertentangan antar catatan yang ditemukan; satu inkonsistensi internal: rentang FPR abstrak versus teks di frontier-llms-2026 (jangan dikutip).

## Usulan baris DESIGN-TRACE
- D-07 (EVAL-PITFALLS): checklist P1 sampai P9 sesuai definisi catatan chasing-shadows-2026; metadata run wajib: ID dan snapshot model, jalur API, versi scanner dan rule set, hash prompt, temperature, batas konteks, sumber label, tanggal korpus, biaya dan waktu. Dasar: chasing-shadows-2026 (P2, P3, P6 sampai P9), sifting-noise-2026, koterba-2026.
- Metrik: laporkan sisa FPR, TP retention per CWE, presisi/recall, ketat dan longgar (hierarki CWE-1000) bersamaan. Dasar: sifting-noise-2026, tamberg-bahsi-2025, huynh-uwa.
- Keputusan teknik (tanpa dasar literatur): verdict uncertain, jumlah run dan ukuran sebaran, pembekuan prompt, uji mutasi, adjudikasi temuan di luar ground truth.
