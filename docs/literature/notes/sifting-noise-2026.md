# sifting-noise-2026: agen LLM untuk menyaring false positive SAST

Sumber: Xiong dan Zhang (Monash). Sifting the Noise. Proc. ACM Softw. Eng. 3, ISSTA, Artikel ISSTA009, Oktober 2026, DOI 10.1145/3832100; arXiv 2601.22952v3 (23 Jul 2026).
Status verifikasi: dicek ke PDF pada 2026-10-26
Jenis: paper venue (versi v3 yang dibaca mencantumkan ISSTA 2026; nomor halaman jurnal ISSTA009:n)

## Klaim utama dan metode
Membandingkan tiga kerangka agen (Aider, OpenHands, SWE-agent) dengan tiga model (Claude Sonnet 4, DeepSeek Chat, GPT-5) untuk menyaring false positive alert SAST, pada OWASP Benchmark Java, 50 alert CodeQL dari Vul4J, dan 50 alert OSS-Fuzz C/C++ pasca batas pelatihan. Hasil sangat bergantung pada model dan kategori CWE.

## Angka aman dikutip
- Konflik angka terselesaikan: baseline FP rate gabungan SAST 98,3% (1.303 dari 1.325 kasus tidak rentan ditandai minimal satu tool); setelah agen SWE-agent + Claude Sonnet 4 sisa FPR 6,3%, yaitu penurunan 92,1%. Angka "di atas 92%" di abstrak adalah persentase penurunan, bukan FPR awal. Bagian 4.1.2 dan Tabel 3 (ISSTA009:12).
- Vanilla prompting Claude Sonnet 4: sisa FPR 23,0%. Tabel 3.
- SonarQube Community v9.9.8 menandai 94,6% kasus tidak rentan (FPR). Tabel 2 (ISSTA009:11); versi di bagian setup.
- TP retention SWE-agent + Claude: 77,7% (314 dari 1.411 yang selesai diberi label FP keliru; miss rate 22,25%). Miss rate rendah untuk injeksi (CWE-78 2,38%, CWE-89 1,10%, CWE-79 0,41%), tinggi untuk CWE-327 (77,17%), CWE-328 (84,50%), CWE-501 (77,11%), CWE-614 (50,00%). Bagian 5.2 (ISSTA009:18).
- OSS-Fuzz, SWE-agent + Claude penuh: presisi 95,5%, recall 95,5%; ablasi tanpa multi-turn atau tanpa lintas file turun jauh. Tabel 5 (ISSTA009:15). Sampel 50 alert.
- Tiga mode gagal: FM1 atribusi CWE salah, FM2 model ancaman terlalu konservatif, FM3 pencocokan pola permukaan. Bagian 4.4.2 dan Tabel 7 (ISSTA009:15 sampai 17).

## Angka tidak aman atau jangan dikutip
- 93,3% "FP identification": ini recall tertinggi (OpenHands + GPT-5) pada sampel 50 alert Vul4J dengan presisi hanya 70,0% dan label sebagian besar dari penulis pertama. Tabel 4 (ISSTA009:13). Jangan dibandingkan dengan presisi triagent.
- Jangan menjajarkan angka OWASP (benchmark sintetis, kemungkinan terlatih) dengan hasil di aplikasi baru triagent.

## Batasan dan konflik kepentingan
Hanya penyaringan FP, di luar pipeline CI/CD, tidak membandingkan dengan deteksi LLM mandiri. Metrik per alert, bukan nilai keamanan lain di kode yang sama. Non-determinisme dimitigasi dengan temperature 0. Pendanaan dan konflik kepentingan belum diketahui (tidak terlihat di teks).

## Implikasi desain untuk triagent
Dasar larangan membuang temuan otomatis dan pengukuran TP retention per kategori (D-02). Bukti eksekusi sebagai penentu status (D-04). Ketiga mode gagal bisa jadi daftar uji kasus jebakan di benchmark.

## Hal yang masih perlu dicek
Tabel 4 menyebut kolom Iden. FP dan Corr. Ret.; definisi tepatnya perlu dibaca lagi sebelum dikutip. Ukuran n per baris Tabel 4 (seed: 41 sampai 50) belum dihitung ulang.
