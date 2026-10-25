# koterba-2026: tiga puluh LLM versus Semgrep pada OWASP Benchmark Java

Sumber: Koterba, Lukaczyk, Ksiek (Cracow University of Technology). Leveraging Large Language Models for advanced static code analysis: Assessing the feasibility of AI superseding traditional vulnerability detection methods. Information and Software Technology 198, 2026, 108213, DOI 10.1016/j.infsof.2026.108213. Berkas PDF: Leveraging Large Language Models for advanced static code analysis.pdf.
Status verifikasi: dicek ke PDF pada 2026-10-26 (teks diekstrak dengan pdftotext; tabel berupa teks berantakan dan tidak dibaca per sel)
Jenis: paper venue (akses terbuka, CC BY-NC)

## Klaim utama dan metode
Membandingkan 30 LLM (Gemini 3 Pro, Sonnet 4.5, DeepSeek R1, dan lainnya) dengan Semgrep, ShiftLeft Scan, dan CodeQL pada OWASP Benchmark v1.2 (Java, 11 kelas kerentanan) dan satu dataset Java buatan sendiri yang tidak dipublikasikan. Model diminta memberi kelas, baris, dan tingkat keyakinan; yang dipakai hanya keyakinan tinggi dan sedang. Biaya dan waktu API ikut diukur.

## Angka aman dikutip
- Semgrep F1 0,66 dan Gemini 3 Pro F1 0,88 pada OWASP Benchmark. Abstrak (hlm. 1) dan bagian 4 (sekitar hlm. 8; perkiraan).
- OWASP Benchmark v1.2: 2740 berkas, 1415 rentan, 1325 tidak rentan. Bagian 3 (hlm. 5; perkiraan).
- Pada dataset sendiri Semgrep turun dari F1 0,66 ke 0,42; presisinya tertinggi (0,83) tetapi recall sekitar 0,29. Bagian 5 (hlm. 13; ulang di hlm. 18; nomor halaman perkiraan).
- Biaya menganalisis 2740 berkas dengan Gemini 3 Pro melebihi 122 dolar, model termahal. Bagian 4, Gambar 7 (hlm. 8; perkiraan).

## Angka tidak aman atau jangan dikutip
- Tabel 4 (per model): teks tabel dari PDF berantakan dan baris Semgrep tampak berbeda dari teks (F1 0,53 di sel yang terbaca). Jangan kutip angka per sel sebelum tabel dilihat langsung.
- Klaim bahwa LLM "melampaui" SAST dan mungkin review manual: simpulan penulis, bukan hasil yang diuji.

## Batasan dan konflik kepentingan
OWASP Benchmark berasal dari 2016, hanya Java, dan hampir pasti ada di data latih sejumlah model; penulis mengakuinya. Dataset sendiri kecil (242 sampel), dibuat bersama mahasiswa, dan tidak dirilis, jadi tidak bisa direplikasi. Prompt dibuat dengan metode "proprietary" lewat penyempurnaan iteratif memakai model o1. Jawaban model diubah ke JSON oleh GPT-4o-mini dan biayanya tidak dihitung. Temuan di luar 11 kelas tidak dihitung. Pernyataan konflik: tidak ada. Pendanaan: belum diketahui (hanya terlihat peran "funding acquisition" di CRediT).

## Implikasi desain untuk triagent
Rujukan untuk memilih model benchmark dan alasan mencatat biaya dan latensi per model (D-09). Pilihan tier model yang sebanding tetap keputusan pemilik. Hasil pada Semgrep (presisi tinggi, recall rendah di kode tak dikenal) mendukung tidak menganggap "tidak ada alert" sama dengan aman.

## Hal yang masih perlu dicek
Nilai Tabel 4 dan Gambar 3 (baca visual). Nama baris dan versi Semgrep serta rule set tidak terlihat di teks yang dibaca. Pendanaan.
