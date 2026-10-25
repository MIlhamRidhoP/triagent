# bedoya-2024: DevSecOps dengan LLM dan Security Chaos Engineering

Sumber: Bedoya, M., Palacios, S., Diaz-Lopez, D., Laverde, E., Nespoli, P. (Universidad del Rosario dan University of Murcia). Int. J. Inf. Secur. 23, hlm. 3765 sampai 3788, terbit 5 Okt 2024, DOI 10.1007/s10207-024-00909-w.
Status verifikasi: dicek ke PDF pada 2026-10-26
Jenis: paper venue (jurnal)

## Klaim utama dan metode
Usulan alur tiga tahap: elicitasi kebutuhan, LLM menyusun attack-defense tree dari user story dan topologi (threat modelling di tahap desain), lalu eksperimen Security Chaos Engineering (SCE) dari cabang pohon itu. Diperagakan pada satu use case perusahaan ritel di AWS. Tanpa evaluasi kuantitatif.

## Angka aman dikutip
- Publikasi: IJIS 23:3765 sampai 3788, 2024 (halaman 1 PDF).
- LLM menyusun attack-defense tree pada Stage 2 (bagian 4.2, PDF hlm. 9 sampai 11). Pengujian memakai GPT-3.5 dan GPT-4.
- GPT-3.5 tidak mampu membuat pohon spesifik dan cenderung mengulang serangan (bagian 4.2, PDF hlm. 10).
- Use case ritel di AWS (bagian 5, PDF hlm. 12 sampai 15), memakai ChatGPT-4 untuk menyusun dan memberi peringkat risiko cabang.
- Kesimpulan: usulan adalah lapisan keamanan tambahan di atas alat SAST, SCA, DAST (bagian 7, PDF hlm. 22).

## Angka tidak aman atau jangan dikutip
- Biaya "sekitar 20 dolar per bulan" untuk ChatGPT-4 (bagian pembahasan, PDF hlm. 21): anekdot langganan konsumen saat penulisan, bukan biaya per run.
- Tidak ada metrik deteksi di paper. Jangan dikutip sebagai bukti efektivitas.

## Batasan dan konflik kepentingan
Satu use case, satu skenario, tidak ada pengukuran terhadap alat SAST/DAST. Peringkat risiko dari LLM tidak divalidasi. Pendanaan: Open Access oleh Colombia Consortium (tidak ada konflik komersial yang ditemukan). LLM tidak membaca atau menganalisis keluaran SAST maupun DAST di paper ini.

## Implikasi desain untuk triagent
Paper ini tentang fase desain, bukan triase alert, jadi bukan dasar langsung. Dapat dirujuk sebagai pengingat bahwa terlalu bergantung pada alat SAST/DAST membuat celah (bagian 4.4), dan untuk gagasan manusia di dalam loop. Rujukan: D-13 di docs/DESIGN-TRACE.md.

## Hal yang masih perlu dicek
- Rincian Tabel 3 dan Gambar 5 tidak dibaca. Penomoran bagian pembahasan diambil dari teks, belum dilihat visual.
