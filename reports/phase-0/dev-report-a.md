# Dev report Fase 0, batch A

Catatan jadi di `docs/literature/notes/`: iris-2025, sifting-noise-2026, contextual-bias-2026, chasing-shadows-2026, frontier-llms-2026, purba-2023, tamberg-bahsi-2025. Semuanya "dicek ke PDF pada 2026-10-26". Tool Read untuk PDF tidak jalan (pdftoppm tidak ada), jadi teks diambil dengan `pdftotext`/PyMuPDF di folder scratchpad, dan tabel berupa gambar dirender dan dilihat langsung (Tamberg Tabel 1/5/6/7, Sifting Tabel 4, Frontier Tabel 2/5). Tidak ada file lain diubah.

## Koreksi pemetaan PDF
- iris-2025: sesuai (6217_IRIS_...pdf), yakin.
- sifting-noise-2026, contextual-bias-2026, chasing-shadows-2026, frontier-llms-2026: sesuai nama file di peta, yakin (penulis dan judul cocok di halaman 1).
- purba-2023: `Software-Vulnerability-Detection-using-Large-Language-Models.pdf`, yakin (Purba dkk., ISSREW 2023, DOI cocok).
- tamberg-bahsi-2025: BUKAN `Large-Language-Models-Versus-Static-Code-Analysis-Tools-...pdf`. File itu adalah Gnieciak dan Szandala (IEEE Access, DOI 10.1109/ACCESS.2025.3635168), yaitu key gnieciak-2025 (batch B). Tamberg dan Bahsi adalah `Harnessing-Large-Language-Models-for-Software-Vulnerability-Detection-A-Comprehensive-Benchmarking.pdf` (DOI 10.1109/ACCESS.2025.3541146), yakin. Peta untuk gnieciak-2025 ("kandidat lemah: Harnessing...") juga perlu ditukar. Perlu diberi tahu pengembang batch B.

## Koreksi terhadap SEED-VERIFIED
- IRIS: angka 22,50% dan 45,83% ada di Tabel 1, bukan Tabel 2.
- Sifting: konflik "92%" versus "98,3%" selesai. 98,3% adalah FP awal gabungan SAST, 6,3% sisa FPR, 92,1% persentase penurunan. Venue: ISSTA 2026 (Proc. ACM Softw. Eng. 3, DOI 10.1145/3832100), tercantum di v3. 93,3% adalah recall pada sampel 50 dengan presisi 70,0%.
- Chasing Shadows: definisi P-nomor seed meleset. P5 adalah korelasi palsu, P8 kekeliruan proksi/generalisasi model, P9 ambiguitas model (ID, snapshot, kuantisasi); P9 paling umum (73,6%). Definisi benar sudah dicatat.
- Contextual bias: seed benar soal 97% (32/33) dan 28/29; terverifikasi dari Tabel III dan hlm. 7.
- Frontier: abstrak menulis FPR 10 sampai 50%, teks 15 sampai 46%; FPR Gemini 3.1 Pro 27,8% terverifikasi (Tabel 2). Paper juga mengutip paper contextual-bias sebagai "Mitropoulos et al., 2026".

## Yang diragukan
- Definisi kolom F1 "macro-F1" di Tabel 2 Frontier belum terverifikasi.
- Definisi kolom Tabel 4 Sifting (Iden. FP, Corr. Ret.) dan n per baris belum dihitung ulang.
- Nomor halaman memakai halaman PDF; untuk Sifting dipakai format ISSTA009:n.
- Pendanaan dan konflik kepentingan tidak terlihat di teks untuk Sifting, Contextual, Chasing; ditulis "belum diketahui".
- Hygiene (em dash) sudah diperiksa dengan grep, bersih; `scripts/check-hygiene.sh` belum dijalankan.

## Verifikasi
`grep -c "" docs/literature/notes/{iris-2025,sifting-noise-2026,contextual-bias-2026,chasing-shadows-2026,frontier-llms-2026,purba-2023,tamberg-bahsi-2025}.md`
`bash scripts/check-hygiene.sh`

Asumsi baru: tidak ada.
