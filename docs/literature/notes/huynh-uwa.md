# huynh-uwa: Deteksi kerentanan kode dengan LLM dan rekayasa prompt

Sumber: Huynh, L., Zhang, Y., Jayasundera, D., Jeon, W., Kim, H., Bi, T., Hong, J. B. (University of Western Australia dan Sungkyunkwan University). "Detecting Code Vulnerabilities using LLMs". Tahun sekitar 2025 (daftar pustaka memuat rujukan yang diakses Feb 2025). DOI dan venue tidak tertera di PDF.
Status verifikasi: dicek ke PDF pada 2026-10-26
Jenis: preprint atau naskah tanpa venue yang teridentifikasi. Bobot lebih rendah.

## Klaim utama dan metode
Kerangka deteksi kerentanan C/C++ dengan beberapa strategi prompt (baseline, role, zero-shot CoT, CO-STAR, Dynamic) pada dataset DiverseVul, diuji dengan GPT-3.5, GPT-4o, Gemini 2.0 Flash, Llama 3.1. Prompt dinamis menaikkan F1 GPT-3.5 sampai 100% (relatif), tetapi efeknya mengecil pada model lebih baru. Semua model buruk dalam menebak jenis CWE.

## Angka aman dikutip
- F1 terbaik hanya 0,16 untuk mengidentifikasi tipe kerentanan (CWE). Abstrak (PDF hlm. 1) dan kesimpulan VII (PDF hlm. 12). Ini tentang klasifikasi CWE, bukan deteksi ada/tidaknya kerentanan.
- Skenario human-in-the-loop (salah CWE tetap dihitung benar): akurasi sekitar 50% untuk kedua model yang dilaporkan (kesimpulan, PDF hlm. 12).
- Performa sampai 3,5 kali lebih baik pada 25 CWE teratas dibanding CWE lain (kesimpulan, hlm. 12; diskusi, hlm. 9).
- Akurasi turun saat konteks kode makin besar (kesimpulan, hlm. 12).
- Perbaikan awal: GPT-4o memperbaiki 45,77% kode rentan, GPT-3.5 21,56%, diverifikasi detektor ICD pada Purple Llama (diskusi IV, PDF hlm. 9, Gambar 8). Dilabeli penulis sebagai eksperimen awal.

## Angka tidak aman atau jangan dikutip
- "Naik sampai 100%" adalah peningkatan relatif dari dasar yang rendah pada GPT-3.5, jangan ditulis sebagai F1 absolut.
- Jangan menyalin format venue dari paper ini (lihat bagian cek).

## Batasan dan konflik kepentingan
Hanya C/C++ dan satu dataset (DiverseVul, label dari commit, bukan alert SAST). Tidak membandingkan dengan SAST dalam pipeline. Pendanaan tidak diperiksa. Persentase patch hanya satu dataset kecil.

## Implikasi desain untuk triagent
Alasan tidak mengandalkan LLM untuk menentukan CWE sendirian: CWE sebaiknya datang dari aturan scanner dan LLM hanya menimbang temuan. Mendukung verifikasi perbaikan oleh alat, bukan klaim LLM. Rujukan: D-06 di docs/DESIGN-TRACE.md.

## Hal yang masih perlu dicek
- Venue dan DOI tidak ada di PDF. Seed menyebut daftar pustakanya mencantumkan SecITC hlm. 275 sampai 288: itu memang entri di daftar pustaka (Springer 2022, ditemukan di bagian referensi), jadi itu rujukan yang dikutip paper ini, bukan venue-nya. Cari venue di sumber lain sebelum disitir.
