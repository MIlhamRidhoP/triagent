# rajapaksha-2024: Deteksi kode rentan berbasis ML berlabel analyzer statis

Sumber: Rajapaksha, S., Senanayake, J., Kalutarage, H., Al-Kadri, M. O. (Robert Gordon University dan UDST). "Enhancing Security Assurance in Software Development: AI-Based Vulnerable Code Detection with Static Analysis". LNCS 14399 (ESORICS 2023 workshops), Springer 2024, hlm. 341 sampai 356, DOI 10.1007/978-3-031-54129-2_20.
Status verifikasi: dicek ke PDF pada 2026-10-26 (PDF adalah accepted manuscript; nomor halaman PDF digeser satu dari penomoran internal naskah)
Jenis: paper venue (prosiding workshop)

## Klaim utama dan metode
Model ML (BoW dan n-gram, Random Forest biner, XGBoost multi-kelas 20 CWE) dilatih pada 600.000 sampel C/C++ yang dilabeli oleh Cppcheck dan Flawfinder, dengan penjelasan LIME dan portal web. Modelnya meniru analyzer statis, bukan mengevaluasi terhadap kebenaran dasar independen.

## Angka aman dikutip
- 600.000 sampel C/C++ dari SATE IV (sintetis) plus repositori GitHub publik (bagian 3.1, PDF hlm. 7).
- Aturan label: rentan bila salah satu dari Cppcheck atau Flawfinder menandai; jinak bila keduanya jinak; sampel jinak diseimbangkan (bagian 3.1, PDF hlm. 7).
- F1 biner 0,96 (RF, fitur BoW), Tabel 1 (PDF hlm. 11). F1 multi-kelas 0,85 (XGB, BoW, 20 kelas CWE), Tabel 2 (PDF hlm. 12). Pembagian data 80:20 (PDF hlm. 10).
- Latensi rata-rata per sampel: RF 175,968 ms, XGB 14,37 ms, LR 8,378 ms, MLP 36,41 ms (Tabel 4, PDF hlm. 13).
- Hanya 12 CWE dengan lebih dari 20.000 sampel: F1 keseluruhan 0,89 (Tabel 3, PDF hlm. 13).

## Angka tidak aman atau jangan dikutip
- F1 0,96 dan 0,85 adalah kesesuaian dengan label buatan alat, bukan akurasi terhadap kerentanan nyata. Jangan menaruhnya sejajar dengan hasil triagent di satu tabel.
- Klaim "sangat generalisabel" di abstrak: pada bagian hasil yang saya baca tidak ada evaluasi lintas dataset. Jangan dikutip.

## Batasan dan konflik kepentingan
Label diverifikasi "dengan pengetahuan ahli" tetapi cakupan verifikasi tidak dirinci. Potensi kebocoran dan duplikasi antara train dan test belum dibahas. Hanya C/C++, lewat portal web, bukan CI/CD. Pendanaan tidak diperiksa.

## Implikasi desain untuk triagent
Peringatan bahwa model yang dilatih dari keluaran SAST mewarisi false negative dan false positive scanner, jadi ground truth triagent harus independen. Latensi tinggi untuk RF menunjukkan bahwa biaya inferensi perlu dicatat. Tidak ada baris di docs/DESIGN-TRACE.md yang bergantung langsung padanya (hanya kontras, lihat INDEX).

## Hal yang masih perlu dicek
- Tahun terbit 2024 (workshop digelar 2023), sesuai catatan seed.
- Pendanaan dan pernyataan konflik belum diperiksa.
