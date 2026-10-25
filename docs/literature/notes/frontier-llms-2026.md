# frontier-llms-2026: apakah LLM frontier siap untuk keamanan siber

Sumber: Dahiya, Nehra, Dholariya, Shangari, Khatri (super-intel.ai). Are Frontier LLMs Ready for Cybersecurity? arXiv 2605.23243v5 (26 Jun 2026).
Status verifikasi: dicek ke PDF pada 2026-10-26
Jenis: preprint (bobot lebih rendah)

## Klaim utama dan metode
Benchmark dua mode: deteksi fungsi white-box (VulnLLM-R, C/Java/Python, 150 sampel) dan pengujian web black-box (5 aplikasi, 118 kerentanan). Enam model frontier dan dua model khusus domain milik penulis. Kesimpulan: false positive tinggi, cakupan black-box rendah tanpa metodologi, konfirmasi deterministik menekan false positive.

## Angka aman dikutip
- Tabel 2 (hlm. 7): FPR Gemini 3.1 Pro 0,278 (27,8%), TP 70, FP 20, F1 0,811, MCC 0,632. Kolom F1 adalah macro-F1 menurut seed (belum diverifikasi definisinya di teks).
- Tabel 2: Sonnet 4.6 FPR 0,431, Gemini 3 Flash 0,458; teks bagian 5.1 (hlm. 6) menyebut kisaran FPR frontier 15% sampai 46% (abstrak menulis 10 sampai 50%; konsistensi lemah).
- Tabel 5 (hlm. 8): Gemini 3.1 Pro dengan scaffold metodologi menemukan 48 dari 118 (recall 40,7%) dengan 45 FP (presisi 51,6%).
- Taksonomi temuan (bagian 3.2): TP, FP, technically invalid, no impact, informational, intended behavior, theoretical, environmental artifact, duplicate.
- Prinsip rancangan: LLM mengusulkan, pemeriksaan bukti deterministik yang memutuskan (bagian 6 dan 7, Gambar 1 P4).
- CWE-862 dan CWE-863 sering tertukar; juga CWE-327 dan 798, CWE-918 dan 601. Bagian 5.4 (hlm. 6 sampai 7).

## Angka tidak aman atau jangan dikutip
- "4 sampai 8 persen coverage", "4x", "FPR P4 di bawah 20%", "100+ zero-day", biaya 3 sampai 5 dolar: dikaitkan dengan produk penulis, tanpa rincian yang bisa diperiksa independen.
- Sebagian besar keunggulan model "Defense" penulis sendiri; jangan dikutip sebagai bukti umum.

## Batasan dan konflik kepentingan
Penulis dari vendor (super-intel.ai) yang menjual model Attack dan Defense; model mereka tampil terbaik di tabel. Data latih dibuat dari target benchmark yang sama (bagian 7), risiko kebocoran. Aplikasi uji sendiri, belum dirilis saat dibaca. Evaluasi terbatas pada aplikasi lokal. Preprint, tanpa review sejawat.

## Implikasi desain untuk triagent
Status "terverifikasi" hanya dari bukti eksekusi (D-04). Tabel keluarga CWE yang sering tertukar (D-06, Fase 2). Taksonomi temuan non-aksi bisa menjadi kategori triase.

## Hal yang masih perlu dicek
Definisi macro-F1 di Tabel 2. Selisih rentang FPR antara abstrak dan teks. Versi v5 bisa berubah lagi.
