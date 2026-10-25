# tamberg-bahsi-2025: LLM versus alat analisis statis Java

Sumber: Tamberg dan Bahsi (TalTech). Harnessing Large Language Models for Software Vulnerability Detection: A Comprehensive Benchmarking Study. IEEE Access 13, 2025, DOI 10.1109/ACCESS.2025.3541146. Berkas PDF: Harnessing-Large-Language-Models-...Benchmarking.pdf.
Status verifikasi: dicek ke PDF pada 2026-10-26. Teks PDF dicek lewat pdftotext; angka Tabel 1, 5, 6, 7 tidak terekstrak sebagai teks, jadi dibaca visual dari render halaman (PyMuPDF, 110 dpi) dan semua angka di bawah cocok dengan gambar tabel. Nomor halaman di bawah adalah halaman PDF; halaman jurnal berbeda (Tabel 1 di 29704, Tabel 5 dan 6 di 29708, Tabel 7 di 29709).
Jenis: paper venue

## Klaim utama dan metode
Membandingkan CodeQL (tiga konfigurasi) dan SpotBugs (dengan dan tanpa Find Security Bugs) melawan GPT-4 turbo, GPT-4, dan Claude 3 Opus dengan banyak strategi prompt (CoT, dataflow, RCI, self-consistency) pada 578 file Juliet Java (17 CWE, setengah rentan). LLM unggul di recall dan F1 tetapi lebih banyak false positive. Kata "hybrid" di paper berarti statis plus dinamis, bukan SAST plus LLM.

## Angka aman dikutip
- SpotBugs-fsb: TP 152, FP 23, TN 266, FN 137; akurasi 0,723, presisi 0,869, recall 0,526, F1 0,655. Tabel 1 (hlm. 7).
- CodeQL-d presisi 0,938 tetapi recall 0,263 dan F1 0,411; CodeQL-esq F1 0,61. Tabel 1.
- GPT-4 dengan CoT 8 langkah: TP 174, FP 55, presisi 0,76, recall 0,602, F1 0,672, biaya 23,32 dolar, 2 jam. Tabel 5 dan 6 (hlm. 11).
- GPT-4 turbo dataflow+RCI: F1 0,662, presisi 0,75, biaya 34,58 dolar, 20,5 jam. Tabel 6 (hlm. 11). Alat statis memakan di bawah satu menit dan 0 dolar.
- Claude 3 Opus CoT 8 langkah presisi 0,884 (tertinggi di antara LLM), recall 0,474. Tabel 6.
- Pemetaan CWE mengikuti pandangan Research Concepts CWE-1000 (induk dan anak dihitung benar, kecuali induk berjenis pillar). Bagian III (hlm. 6).
- Kedua jenis alat gagal total (F1 0) pada enam CWE masing-masing, dan lima di antaranya sama (CWE-256, 523, 549, 566, 606), jadi celahnya sebagian besar tumpang tindih. Hanya sebagian kecil saling melengkapi: CodeQL-esq 0 di CWE-81 sedangkan SpotBugs-fsb 1; SpotBugs-fsb 0 di CWE-190 sedangkan CodeQL-esq 0,583. Tabel 7 (hlm. 12) dan Bagian IV.C (hlm. 11).

## Angka tidak aman atau jangan dikutip
- Selisih F1 0,672 versus 0,655 sangat kecil dan tanpa uji signifikansi; jangan klaim "LLM mengalahkan SAST" tanpa catatan.
- Biaya dan waktu per dataset 578 file, bukan per proyek nyata; paper sendiri menyebut waktu tidak andal.

## Batasan dan konflik kepentingan
Dataset sintetis (Juliet), tingkat file, setengah rentan; mungkin ada di data latih LLM (dimitigasi dengan penamaan ulang). Hanya Java, temperature 0. Tidak menggabungkan SAST dengan LLM; keduanya hanya dibandingkan. Didanai Kementerian Pendidikan Estonia (EXAI); tidak ada konflik komersial tertulis.

## Implikasi desain untuk triagent
Evaluasi scanner saja versus scanner dengan LLM pada dataset yang sama, termasuk biaya dan waktu (D-08). Pemetaan keluarga CWE yang longgar dalam penilaian. Catat bahwa celah antar-alat hanya sebagian saling melengkapi (sebagian besar tumpang tindih).

## Hal yang masih perlu dicek
Seed menyebut "Tabel 1 hlm. 7, Tabel 6 hlm. 11": cocok dengan halaman PDF. Nomor halaman jurnal berbeda (29704 dan 29708).
