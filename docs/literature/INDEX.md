# INDEX.md: indeks literatur

PDF asli tidak ada di git. Taruh di `docs/literature/pdf/` (diabaikan git) dengan nama `<key>.pdf`. Agent bekerja dari catatan di `docs/literature/notes/<key>.md` yang dibuat dengan `NOTE-TEMPLATE.md`, bukan dari PDF.

Prioritas: `core` (wajib punya catatan sebelum Fase 0 lulus), `pendukung` (catatan bila dibutuhkan), `belum` (belum dipilah).
Status: `seed` (ada di `SEED-VERIFIED.md`, belum dicatat penuh), `dicatat` (catatan sudah ditulis dan dicek ke PDF), `belum-dibaca`.

Catatan penting: baris di tabel utama harus tetap berformat lima kolom, karena `scripts/gates/phase-0.sh` membacanya.

## Tabel utama

| key | paper | prioritas | status | dipakai di |
|---|---|---|---|---|
| iris-2025 | Li, Dutta, Naik. IRIS: LLM-Assisted Static Analysis for Detecting Security Vulnerabilities (ICLR 2025) | core | dicatat | D-01 |
| sifting-noise-2026 | Xiong dan Zhang. Sifting the Noise: A Comparative Study of LLM Agents in Vulnerability False Positive Filtering (arXiv 2601.22952) | core | dicatat | D-02, D-04 |
| contextual-bias-2026 | Alexopoulos dkk. Measuring and Exploiting Contextual Bias in LLM-Assisted Security Code Review (arXiv 2603.18740) | core | dicatat | D-03 |
| chasing-shadows-2026 | Evertz dkk. Chasing Shadows: Pitfalls in LLM Security Research (NDSS 2026) | core | dicatat | D-07, D-15 |
| frontier-llms-2026 | Dahiya dkk. Are Frontier LLMs Ready for Cybersecurity? Evidence for Vertical Foundation Models from Dual-Mode Vulnerability Benchmarks (arXiv 2605.23243, preprint) | core | dicatat | D-04, D-06 |
| purba-2023 | Purba dkk. (ISSREW 2023), LLM dan kerentanan, pola versus aliran data | core | dicatat | D-05 |
| tamberg-bahsi-2025 | Tamberg dan Bahsi (IEEE Access 2025), SAST versus LLM | core | dicatat | D-08 |
| koterba-2026 | Koterba dkk. (Information and Software Technology 198, 2026), komparasi LLM dan SAST | core | dicatat | D-09 |
| gnieciak-2025 | Gnieciak dan Szandala (IEEE Access 2025), benchmark sistematis deteksi kerentanan | core | dicatat | D-10 |
| huynh-uwa | Huynh dkk. (UWA), LLM untuk klasifikasi tipe kerentanan | core | dicatat | D-06 |
| anggoman-2025 | Anggoman dkk. (ICoCICs 2025), konfigurasi default scanner | core | dicatat | D-11 |
| jin-2025 | Jin (ICAIBD 2025), taksonomi pendekatan LLM untuk kerentanan | core | dicatat | D-12 |
| bedoya-2024 | Bedoya dkk. (Int. J. Inf. Secur. 2024), LLM, DevSecOps, dan security chaos engineering | core | dicatat | D-13 |
| nist-ssdf-800-218 | NIST SP 800-218, Secure Software Development Framework | pendukung | belum-dibaca | D-14 |
| zakkiya-2025 | Zakkiya dkk. (ICoAILO 2025), model SSDLC 8 fase dan kerangka prompting | pendukung | seed | D-14 |
| aleksieva-petrova-2023 | Aleksieva-Petrova dan Petrov (DSA 2023), model SSDLC | pendukung | seed | D-14 |
| nocera-2023 | Nocera dkk. (SEAA 2023), studi concern keamanan di proyek open source | pendukung | seed | motivasi |
| madani-2025 | Madani (FLLM 2025), tinjauan LLM dan SDLC | pendukung | seed | motivasi |
| rajapaksha-2024 | Rajapaksha dkk. (LNCS 14399, 2024), ML klasik untuk deteksi kerentanan | pendukung | dicatat | kontras |

## Berkas di folder PDF pengguna yang belum dipilah

Tabel ini hanya daftar nama (terpotong seperti terlihat di file explorer) dan sengaja berformat tiga kolom. Fase 0 memilah: tentukan key, prioritas, lalu pindahkan barisnya ke tabel utama bila dipakai.

| nama file (terpotong) | dugaan topik dari judul | catatan |
|---|---|---|
| Action-Research-on-the-DevSecOps-... | DevSecOps | belum dibaca |
| AI-Driven Quality Assurance for Secur... | AI untuk QA SSDLC | belum dibaca |
| AI-driven Security as Code for softwar... | security as code | belum dibaca |
| AI-Powered-Code-Reviews-Leveraging... | review kode dengan AI | belum dibaca |
| A-Unified-Framework-for-Automating... | kerangka otomasi | belum dibaca |
| Evaluating-Security-and-Quality-of-B... | evaluasi kualitas dan keamanan | belum dibaca |
| Implementing-and-Automating-Secu... | otomasi keamanan | belum dibaca |
| Multi-Agent-LLM-Collaboration-for... | kolaborasi multi-agent | belum dibaca |
| Poster-AI-Driven-Security-Investigati... | poster riset | belum dibaca |
| S2-2025-475798-bibliography | daftar pustaka | belum dibaca |
| Security-at-Scale-Ethical-Container-Ex... | keamanan kontainer | belum dibaca |
| Security-Evaluation-of-Insurance-Port... | evaluasi keamanan portal | belum dibaca |
| SOK-Exploring-Hallucinations-and-Se... | halusinasi LLM dan keamanan | belum dibaca |
| VulDetect-A-novel-technique-for-det... | teknik deteksi | belum dibaca |

Berkas yang sudah dipetakan ke key (lihat `reports/phase-0/pdf-map.md`) dikeluarkan dari tabel ini. Tiga di antaranya, zakkiya-2025, madani-2025, dan nocera-2023, dikenali lewat DOI saja dan belum punya catatan.

Dua berkas di folder pengguna bersifat dokumen kampus (analisis keamanan SIA) dan bukan literatur desain. Abaikan untuk repo ini.

## Penamaan PDF yang disarankan

| nama file asli (terpotong) | ganti nama menjadi |
|---|---|
| 6217_IRIS_LLM_Assisted_Static_LLM-as... | iris-2025.pdf |
| Sifting the Noise A Comparative Study... | sifting-noise-2026.pdf |
| Measuring and Exploiting Contextual... | contextual-bias-2026.pdf |
| Chasing Shadows Pitfalls in LLM Secur... | chasing-shadows-2026.pdf |
| Are Frontier LLMs Ready for Cybersec... | frontier-llms-2026.pdf |
| NIST.SP.800-218.pdf | nist-ssdf-800-218.pdf |
| RAJAPAKSHA 2024 Enhancing security... | rajapaksha-2024.pdf |

Berkas lain: beri nama `<penulis-pertama>-<tahun>.pdf` setelah penulis dan tahunnya dipastikan dari halaman pertama.
