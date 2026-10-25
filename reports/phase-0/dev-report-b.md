# Dev report Fase 0, batch B

## Catatan yang jadi
Enam catatan di `docs/literature/notes/`: `gnieciak-2025.md`, `huynh-uwa.md`, `anggoman-2025.md`, `jin-2025.md`, `bedoya-2024.md`, `rajapaksha-2024.md`. Semuanya berstatus "dicek ke PDF pada 2026-10-26". Tool Read tidak bisa merender PDF (tanpa poppler), jadi saya mengekstrak teks dengan `pdftotext` dan PyMuPDF, dan merender halaman tabel Gnieciak sebagai gambar untuk membaca Tabel 6 dan 13.

## Koreksi pemetaan PDF
| key | file sebenarnya | yakin |
|---|---|---|
| gnieciak-2025 | Large-Language-Models-Versus-Static-Code-Analysis-Tools-A-Systematic-Benchmark-for-Vulnerability.pdf (DOI ...3635168 cocok) | ya |
| huynh-uwa | Detecting Code Vulnerabilities using LLMs.pdf | ya (penulis UWA cocok) |
| anggoman-2025 | Beyond-Static-Analysis-Detecting-SQL-Injection-via-Context-Aware-Code-Review-in-Web-Applications.pdf (salinan "(1)" identik byte per byte; DOI cocok) | ya |
| jin-2025 | Large-Language-Models-for-Vulnerability-Detection-in-Static-Code-Analysis-A-Survey.pdf (DOI cocok) | ya |
| bedoya-2024 | Enhancing DevSecOps Practice ... Security Chaos Engineering.pdf | ya |
| rajapaksha-2024 | RAJAPAKSHA 2024 Enhancing security assurance (AAM).pdf (accepted manuscript) | ya |

Untuk batch A: `Harnessing-Large-Language-Models-...-Comprehensive-Benchmarking.pdf` ternyata Tamberg dan Bahsi (DOI 10.1109/ACCESS.2025.3541146), jadi itu PDF tamberg-bahsi-2025, bukan "Large-Language-Models-Versus-...". Juga "Implementing-and-Automating-Security-Scanning..." bukan Anggoman (DOI WCONF 2023). Dari pencarian DOI: purba-2023 = `Software-Vulnerability-Detection-using-Large-Language-Models.pdf` (ISSREW...00058); koterba-2026 = `Leveraging Large Language Models for advanced static code analysis.pdf` (infsof.2026.108213); zakkiya = `A-Guideline-...pdf` (DOI cocok); madani = `Towards-the-Integration-...pdf` (DOI cocok); nocera = `A-Large-scale-Fine-grained-...pdf` (DOI cocok). Hanya dicek lewat DOI, bukan halaman 1.

## Koreksi terhadap SEED-VERIFIED
- Gnieciak: tarif token ada di teks bagian III.B (hlm. 198414), bukan Tabel 1 (Tabel 1 adalah harga lisensi alat SAST).
- Jin: definisi Static Analysis Augmentation ada di bagian IV.B, bukan III.B.
- Huynh: tidak ada venue/DOI di PDF; "SecITC hlm. 275 sampai 288" adalah entri daftar pustaka (rujukan), bukan venue paper ini.
- Anggoman: tidak ada LLM di paper (review manual).

## Hal yang diragukan
- Nomor halaman Jin memakai PDF hlm. dan halaman IEEE hanya untuk satu titik.
- Rajapaksha: PDF accepted manuscript, halaman PDF = halaman naskah + 1.
- Pendanaan Gnieciak, Huynh, Rajapaksha tidak diperiksa. Huynh kemungkinan preprint, venue belum diketahui (perlu masuk pertanyaan terbuka DECISIONS.md oleh orkestrator).
- ID DESIGN-TRACE tidak diisi karena saya tidak membaca berkas itu; orkestrator perlu memetakan.
