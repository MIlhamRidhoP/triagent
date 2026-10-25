# SEED-VERIFIED.md: titik awal literatur

Ini ringkasan awal dari analisis literatur sebelumnya, disimpan supaya Fase 0 tidak mulai dari nol. **Ini bukan sumber.** Semua angka di sini wajib dicocokkan ke PDF saat catatan paper resmi ditulis, lalu dipindahkan ke `notes/<key>.md`. Item bertanda [CEK] punya ketidakpastian yang diketahui.

## Sudah pernah dicocokkan ke PDF (tetap cek ulang saat membuat catatan)

**iris-2025** (Li, Dutta, Naik, ICLR 2025)
- CodeQL Detection Rate 22,50% (27/120). IRIS dengan GPT-4: 45,83% (55/120). Tabel 2 dan abstrak.
- Hanya CodeQL yang diaugmentasi (satu tool SAST). Bekerja di luar pipeline CI/CD.
- Dasar posisi "LLM melengkapi SAST".

**tamberg-bahsi-2025** (IEEE Access 2025, 10.1109/ACCESS.2025.3541146)
- SpotBugs-FSB F1 0,655 (presisi 0,869, recall 0,526). GPT-4 dengan CoT 8 langkah F1 0,672. Tabel 1 hlm. 7, Tabel 6 hlm. 11.
- Membandingkan, tidak menggabungkan SAST dan LLM. Kata "hybrid" di paper itu berarti statis plus dinamis.

**koterba-2026** (Inf. Softw. Technol. 198, 2026, 10.1016/j.infsof.2026.108213)
- Semgrep F1 0,66, Gemini 3 Pro F1 0,88. Abstrak dan hasil.
- Kerangka "AI menggantikan SAST": triagent berbeda posisi (melengkapi), jelaskan perbedaannya.

**huynh-uwa** (Huynh dkk., UWA)
- F1 terbaik 0,16 untuk mengklasifikasikan TIPE kerentanan (CWE), bukan untuk deteksi. Abstrak dan kesimpulan.
- [CEK] venue: daftar pustakanya menulis SecITC hlm. 275 sampai 288, tidak cocok dengan sumber lain. Jangan menyalin format dari paper ini.

**gnieciak-2025** (IEEE Access 2025, 10.1109/ACCESS.2025.3635168)
- Future work eksplisit: hibrida SAST dan LLM untuk prioritisasi dan verifikasi (bagian VI.A).
- Melaporkan waktu eksekusi (Tabel 6) dan tarif harga token (Tabel 1), bukan biaya terukur per run. Itu celah yang diisi triagent.

**anggoman-2025** (ICoCICs 2025, 10.1109/ICOCICS68032.2025.11384074)
- SonarCloud dan DeepSource pada konfigurasi default mendeteksi 0%. Abstrak. Konteks: objek uji spesifik, jangan digeneralisasi ke semua proyek.

**madani-2025** (FLLM 2025)
- 6,2% adalah porsi studi yang membahas fase deployment (Gambar 2), bukan tingkat adopsi.

**purba-2023** (ISSREW 2023, 10.1109/ISSREW60843.2023.00058)
- LLM tidak mengerti aliran data; varian kode menunjukkan model mengenali pola kerentanan yang samar. Bagian IV, Gambar 2 sampai 5.
- Dasar slicing dan uji mutasi.

**rajapaksha-2024** (LNCS 14399, 2024, hlm. 341 sampai 356, 10.1007/978-3-031-54129-2_20)
- Random Forest (biner F1 0,96) dan XGBoost (multi-kelas CWE F1 0,85) pada 600.000 sampel C/C++. Label dari Cppcheck dan Flawfinder. Lewat portal web, bukan CI/CD.
- Jangan menaruh F1 0,96 sejajar dengan hasil triagent di satu tabel: ground truth dan data berbeda.
- Tahun terbit 2024 (workshop digelar 2023).

**jin-2025** (ICAIBD 2025, 10.1109/ICAIBD64986.2025.11082007)
- Lima pendekatan: Base Application, Static Analysis Augmentation, Knowledge Enhancement, Fine-tuning Based, Hybrid Feature Fusion. Definisi Static Analysis Augmentation di bagian III.B hlm. 3.
- [CEK] satu catatan lama menyebut Jin belum diaudit ke PDF. Cocokkan ulang.

**bedoya-2024** (Int. J. Inf. Secur. 23, 3765 sampai 3788, 2024, 10.1007/s10207-024-00909-w)
- LLM menyusun attack-defense tree untuk threat modelling di tahap desain (bagian 4.2), ditambah security chaos engineering. Satu use case ritel di AWS. Tanpa metrik deteksi.
- LLM tidak menganalisis keluaran SAST atau DAST di paper ini.

**nocera-2023** (SEAA 2023, 10.1109/SEAA60479.2023.00069)
- 164.980 commit, 200 proyek Python, rata-rata sekitar 11 security concern per commit (SonarQube).

**zakkiya-2025** (ICoAILO 2025, 10.1109/ICoAILO66760.2025.11156083) dan **aleksieva-petrova-2023** (DSA 2023, 10.1109/DSA59317.2023.00017)
- Model SSDLC 8 fase action-oriented di Zakkiya diadaptasi dari Aleksieva-Petrova dan Petrov.
- Kerangka prompting enam elemen (Context, Task, Instruction, Clarify, Refine, Warning) adalah kontribusi Zakkiya sendiri, bukan dari Aleksieva-Petrova. Jangan tertukar saat menulis sitasi.

## Dari pembahasan paper sebelumnya (cek ulang ke PDF)

**sifting-noise-2026** (Xiong dan Zhang, arXiv 2601.22952, versi 3)
- Tiga kerangka agen (Aider, OpenHands, SWE-agent) dengan Claude Sonnet 4, DeepSeek Chat, GPT-5. Hanya penyaringan false positive, di luar pipeline, tidak membandingkan dengan deteksi LLM mandiri.
- OWASP Benchmark: false positive turun sampai 6,3%. [CEK] **angka awalnya tercatat bertentangan** di catatan lama (di atas 92% versus 98,3%). Buka tabelnya di PDF sebelum mengutip.
- SonarQube Community 9.9.8: FPR 94,6% (Java, hanya VULNERABILITY, tanpa hotspot). TP retention keseluruhan 77,7%, tetapi TP kategori injeksi hampir tidak terbuang sementara kategori kebijakan dan kriptografi kehilangan lebih dari separuh. Ini dasar ukur TP retention per kategori.
- Ada tiga mode gagal (FM1, FM2, FM3) yang bisa dijadikan daftar uji. Metrik RQ2 memakai false positive sebagai kelas positif. Ukuran n di Tabel 4 sebenarnya 41 sampai 50 per baris.
- Jangan membandingkan angka 93,3% (Java nyata) dengan presisi hasil triagent: data dan definisi berbeda.
- [CEK] venue: satu catatan menyebut ISSTA 2026, yang lain hanya arXiv.

**contextual-bias-2026** (Alexopoulos dkk., arXiv 2603.18740)
- Sitasi yang benar: Alexopoulos dkk. 2026 (bukan Mitropoulos).
- Bingkai "kode aman" paling merusak. Deteksi per file nyaris tidak membedakan kode rentan dan yang sudah ditambal. Redaksi metadata adalah pertahanan.
- Klaim 97% sudah termasuk 4 kasus baseline; untuk serangan murni angkanya 28 dari 29.

**chasing-shadows-2026** (Evertz dkk., NDSS 2026)
- Sembilan jebakan (P1 sampai P9) sebagai daftar periksa evaluasi. Dari catatan lama: P2 ground truth dibantu AI, P3 kontaminasi data, P5 petunjuk di kode, P7 satu prompt untuk semua model (perlu justifikasi dan satu varian), P8 klaim berlebihan, P9 model preview dan run tanpa metadata. [CEK] definisi tepat tiap P di PDF sebelum ditulis ke `docs/EVAL-PITFALLS.md`.

**frontier-llms-2026** (Dahiya dkk., arXiv 2605.23243, preprint)
- Preprint: bobot lebih rendah. Ada konflik kepentingan dan aplikasi uji juga dipakai untuk pelatihan.
- Aman: TP, FP, FPR, MCC; FPR Gemini 3.1 Pro 27,8% pada VulnLLM-R; Tabel 5; taksonomi di bagian 3.2; prinsip "LLM mengusulkan, bukti yang memutuskan". Kolom F1 di Tabel 2 adalah macro-F1.
- Jangan dikutip: "4 sampai 8 persen coverage", "4x", "FPR P4 di bawah 20%", 100+ zero-day, biaya 3 sampai 5 dolar.
- CWE-862 dan CWE-863 sering tertukar (bagian 5.4).

**nist-ssdf-800-218**
- Standar. Dipakai sebagai acuan konsep praktik pengembangan aman di pemetaan kepatuhan (Fase 9).
