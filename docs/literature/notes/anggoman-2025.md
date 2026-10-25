# anggoman-2025: Review kode sadar-konteks untuk SQL injection

Sumber: Anggoman, C. R., Maulana, R., Setiawan, H., Al-Farabi, M. A. N. (Politeknik Siber dan Sandi Negara, Bogor). "Beyond Static Analysis: Detecting SQL Injection via Context-Aware Code Review in Web Applications". 2025 IEEE 2nd ICoCICs, hlm. 343 sampai 348, DOI 10.1109/ICOCICS68032.2025.11384074.
Status verifikasi: dicek ke PDF pada 2026-10-26
Jenis: paper venue (konferensi)

## Klaim utama dan metode
Review kode manual terstruktur (OWASP Code Review Guide) pada satu sistem manajemen perpustakaan open source berbasis PHP menemukan empat SQL injection kritis. Semuanya divalidasi dengan SQLMap (time-based blind) dan didaftarkan sebagai CVE. SonarCloud dan DeepSource pada konfigurasi default tidak mendeteksi satu pun. Tidak ada LLM yang dipakai, meski judulnya menyiratkan.

## Angka aman dikutip
- Empat kerentanan SQLi, deteksi 0 persen oleh DeepSource dan SonarCloud pada konfigurasi default. Abstrak (hlm. 343, PDF hlm. 1) dan bagian IV.E (PDF hlm. 5).
- Tabel I (PDF hlm. 5): contoh CVE-2025-25403, SonarCloud "Not Detected", DeepSource hanya "Irrelevant Logger Issues". Tidak ada true positive.
- Alat dijalankan dengan rule set keamanan default untuk bahasa sasaran pada basis kode yang sama (bagian III.D, PDF hlm. 3).

## Angka tidak aman atau jangan dikutip
- "0 persen" tidak boleh digeneralisasi ke semua proyek atau semua SAST: n = 4 temuan, satu aplikasi PHP, dua alat cloud, konfigurasi default. Tulis selalu dengan konteks itu.
- Jangan menulis bahwa review manual selalu mengalahkan alat otomatis: tidak ada metrik presisi atau recall manual, tidak ada kontrol terhadap alat lain.

## Batasan dan konflik kepentingan
Ground truth berasal dari review manual penulis sendiri. Prosedur menyebut review "dicross-validasi dengan hasil analisis statis" (PDF hlm. 3), jadi ada sedikit sirkularitas. Nama aplikasi tidak disebut di naskah. Tidak ada pendanaan yang saya temukan di PDF.

## Implikasi desain untuk triagent
Memberi contoh nyata false negative SAST pada SQLi sadar-konteks, sehingga triagent tidak boleh menganggap "tidak ada alert" sama dengan aman, dan perlu jalur verifikasi dengan bukti (PoC) serta peran manusia untuk kasus berisiko. Rujukan: D-11 di docs/DESIGN-TRACE.md.

## Hal yang masih perlu dicek
- Versi alat dan rule set persis tidak disebut. Seed menyebut kedua alat pada konfigurasi default, dan ini cocok dengan PDF.
- PDF "Implementing-and-Automating-Security-Scanning..." di folder bukan paper ini (DOI WCONF 2023). Dua salinan "Beyond-Static-Analysis" identik byte per byte.
