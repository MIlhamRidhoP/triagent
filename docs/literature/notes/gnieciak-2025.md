# gnieciak-2025: LLM versus alat SAST pada proyek C# kecil

Sumber: Gnieciak, D. dan Szandala, T. (Wroclaw University of Science and Technology), IEEE Access vol. 13, 2025, hlm. 198410 dst., DOI 10.1109/ACCESS.2025.3635168. Diterima 22 Okt 2025, terbit 20 Nov 2025.
Status verifikasi: dicek ke PDF pada 2026-10-26
Jenis: paper venue (jurnal). Isinya berasal dari tesis magister, tertulis "this thesis" di bagian Future Works.

## Klaim utama dan metode
Enam pendekatan dibandingkan pada 10 proyek C# buatan sendiri yang memuat 63 kerentanan: SonarQube, CodeQL, SnykCode lawan GPT-4.1, Mistral Large, DeepSeek V3 (lewat GitHub Models). Ground truth diverifikasi manual. LLM unggul di recall tetapi lebih berisik dan salah menunjuk baris/kolom. Penulis menyarankan pipeline hibrida: LLM untuk triase luas, SAST untuk verifikasi.

## Angka aman dikutip
- 63 kerentanan di 10 proyek C#, ukuran proyek 3500 sampai 5500 karakter, sampai 10 berkas. Abstrak (hlm. 198410, PDF hlm. 1) dan bagian III.C (hlm. 198414).
- Rata-rata F1: SonarQube 0,260; CodeQL 0,386; SnykCode 0,546; GPT-4.1 0,797; Mistral Large 0,753; DeepSeek V3 0,750. Tabel 13 (hlm. 198419, PDF hlm. 10).
- Rata-rata presisi/recall: SonarQube 0,567/0,187; CodeQL 0,625/0,284; SnykCode 0,686/0,523; GPT-4.1 0,757/0,877. Tabel 13.
- Waktu eksekusi per proyek: CodeQL sekitar 186 sampai 213 detik; GPT-4.1 sekitar 3,5 sampai 17,8 detik. Tabel 6 (hlm. 198418, PDF hlm. 9).
- Harga daftar per juta token (masukan/keluaran): GPT-4.1 $2/$8; DeepSeek V3 $0,27/$1,10; Mistral Large $2/$6. Teks bagian III.B (hlm. 198414, PDF hlm. 5). Ini tarif penyedia, bukan biaya terukur.
- Semua LLM salah melokalisasi baris/kolom (bagian VI, PDF hlm. 12), dugaan penulis: tokenisasi BPE.
- Future work: solusi hibrida alat klasik plus LLM untuk memprioritaskan dan memverifikasi temuan (bagian VI.A, PDF hlm. 12).

## Angka tidak aman atau jangan dikutip
- Klaim "LLM mengalahkan SAST" secara umum: hanya 10 proyek mini, kerentanan ditanam, satu bahasa, rata-rata per proyek tanpa interval kepercayaan.
- Peringkat FP ratio (DeepSeek V3 tertinggi) hanya dari Gambar 4, angkanya tidak saya baca. Jangan dikutip sebagai angka.
- Jangan sejajarkan F1 di sini dengan hasil triagent: data, definisi, dan ground truth berbeda.

## Batasan dan konflik kepentingan
Tidak ada pengujian pada CI/CD nyata, tidak ada biaya terukur per run, konfigurasi alat default. Pendanaan tidak diperiksa. Pembahasan "hibrida" di sini adalah rekomendasi, belum diuji.

## Implikasi desain untuk triagent
Mendukung posisi LLM melengkapi SAST (triase dan verifikasi, bukan pengganti). Menunjukkan kebutuhan lokalisasi yang divalidasi alat (bukan dari LLM) dan pengukuran biaya per run yang nyata. Rujukan: D-10 di docs/DESIGN-TRACE.md.

## Hal yang masih perlu dicek
- Seed menulis tarif token ada di Tabel 1. Koreksi: Tabel 1 membahas alat SAST (harga lisensi); tarif token ada di teks bagian III.B (kemungkinan juga Tabel 2, tidak dibuka).
- Rincian Gambar 4 sampai 7 belum dibaca.
