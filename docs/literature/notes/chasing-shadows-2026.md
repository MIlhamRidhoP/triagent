# chasing-shadows-2026: sembilan jebakan riset keamanan berbasis LLM

Sumber: Evertz dkk. (CISPA dan mitra). Chasing Shadows: Pitfalls in LLM Security Research. NDSS 2026, DOI 10.14722/ndss.2026.241749; arXiv 2512.09549v2 (15 Des 2025).
Status verifikasi: dicek ke PDF pada 2026-10-26
Jenis: paper venue

## Klaim utama dan metode
Mengidentifikasi sembilan jebakan (P1 sampai P9) di seluruh alur kerja LLM, lalu menilai prevalensinya pada 72 paper keamanan dan rekayasa perangkat lunak (2023 sampai 2024) oleh 15 peneliti. Semua paper memuat minimal satu jebakan; hanya 15,71% jebakan yang ada dibahas penulisnya. Ada situs panduan llmpitfalls.org.

## Angka aman dikutip
- Definisi tepat (Lampiran B, kriteria "applies"): P1 keracunan data lewat scraping internet; P2 label tidak akurat buatan LLM tanpa validasi; P3 kebocoran data (info tes ada di data latih); P4 model collapse dari data latih sintetis; P5 korelasi palsu atau fitur tak relevan (termasuk petunjuk seperti nama variabel); P6 pemotongan konteks; P7 sensitivitas prompt (satu prompt tetap untuk semua model tanpa justifikasi atau variasi); P8 kekeliruan proksi atau pengganti (generalisasi klaim ke model yang tidak diuji); P9 ambiguitas model (ID, snapshot, commit, kuantisasi tidak lengkap, atau tidak jelas API versus web).
- 72 paper; 15,71% jebakan yang ada didiskusikan. Abstrak dan bagian prevalensi (hlm. 7).
- P9 paling umum: 73,6% Present (53 paper) ditambah 12,5% Partly; tidak ada yang membahasnya. Hlm. 7 sampai 8.
- P3: 65,2% (47 paper) terkena atau kemungkinan terkena. P7: 31,9% (23 paper). P8: 47,2% (34 paper). Hlm. 6 sampai 7.
- Topik Vulnerability Detection rata-rata 23,70% jebakan per paper, Vulnerability Repair 27,78%. Hlm. 7.
- Contoh P9: tiga snapshot GPT memberi recall berbeda jauh (82,05%, 41,03%, 61,54%) pada deteksi ujaran kebencian. Tabel I (hlm. 8). Ini tugas non-keamanan.

## Angka tidak aman atau jangan dikutip
- Angka Tabel I dan II (eksperimen ilustrasi) bukan tentang deteksi kerentanan; jangan dipakai sebagai bukti kinerja.
- Catatan seed menyebut definisi P-nomor dari ingatan; yang benar ada di atas. P8 bukan sekadar "klaim berlebihan" dan P9 bukan hanya "model preview" (lihat definisi).

## Batasan dan konflik kepentingan
Penilaian prevalensi subjektif meski ada protokol review ganda; hanya paper 2023 sampai 2024 di venue terpilih. Pendanaan belum diketahui.

## Implikasi desain untuk triagent
Daftar periksa jebakan untuk harness evaluasi (D-07): catat ID dan snapshot model persis dan jalur (API), jalankan lebih dari satu varian prompt (P7), tangani batas konteks (P6), cek kebocoran dengan korpus baru (P3, mendukung D-15), validasi label tanpa LLM (P2). Bahan untuk `docs/EVAL-PITFALLS.md`.

## Hal yang masih perlu dicek
Nomor halaman memakai halaman PDF. Versi NDSS final bisa berbeda dari arXiv v2.
