# purba-2023: deteksi kerentanan dengan LLM, pola versus aliran data

Sumber: Purba, Ghosh, Radford, Chu (UNC Charlotte). Software Vulnerability Detection using Large Language Models. ISSREW 2023 (invited paper), DOI 10.1109/ISSREW60843.2023.00058.
Status verifikasi: dicek ke PDF pada 2026-10-26
Jenis: paper venue (workshop)

## Klaim utama dan metode
Empat LLM (GPT-3.5-Turbo dan versi 0613 dengan prompt langsung, Davinci dan CodeGen-2B yang di-fine-tune) pada dataset code gadgets (buffer overflow, C/C++) dan CVEfixes (SQL injection dan buffer overflow), set seimbang. Analisis kualitatif dengan varian kode buatan. Temuan: recall bagus, false positive sangat tinggi; model mengenali pola, bukan aliran data.

## Angka aman dikutip
- Tabel II (hlm. 5), code gadgets: Davinci presisi 60%, TPR 94%, FPR 62,67%, F1 73,23%; CodeGen presisi 49,75%, TPR 68%, FPR 68,67%. Pembanding statis (Flawfinder FPR 44,7%, RATS 42,2%, Checkmarx 43,1%) diambil dari paper lain (Li dkk.), bukan dijalankan ulang.
- Tabel I (hlm. 4): prompt langsung GPT-3.5-Turbo pada SQL injection CVEfixes recall hanya 2,27% (presisi 15,15%).
- Fine-tune CodeGen dengan 10.000 contoh (bukan 1.000) menaikkan F1 lebih dari 10 poin, terutama recall. Tabel IV (hlm. 6).
- Dari 2.512 kasus buffer overflow CVEfixes, 1.629 (65%) memuat minimal satu fungsi pustaka dari daftar code gadget. Bagian IV.C (hlm. 8).
- Kualitatif: model gagal pada validasi atau mitigasi dan masih menandai kode aman karena pola (memcpy, strncpy, like). Bagian IV.A, Gambar 2 sampai 5 (hlm. 6 sampai 7). Code slicing membantu (bagian IV.C).

## Angka tidak aman atau jangan dikutip
- Angka model usang (GPT-3.5, Davinci, CodeGen 2B); jangan dibandingkan dengan model 2026.
- Perbandingan dengan VulDeePecker, Flawfinder, RATS, Checkmarx bukan hasil eksperimen penulis.

## Batasan dan konflik kepentingan
Sampel uji kecil (150 sampai 300 per set), satu kali jalan tanpa ulang (hanya satu uji ensemble tiga run). CVEfixes punya masalah kualitas ("fix" yang hanya format) dan penulis memakainya apa adanya. Dataset ditata seimbang, tidak seperti proyek nyata. Didanai NSA grant H9823021-1-0259; tidak ada kepentingan komersial yang tertulis.

## Implikasi desain untuk triagent
Konteks berupa slice dari sumber ke sink, bukan file utuh (D-05). Menjadi dasar uji mutasi: varian kode yang mengubah aliran data tanpa mengubah pola mengungkap apakah LLM bernalar atau mencocokkan pola. Menegaskan LLM perlu pendamping analisis yang ketat.

## Hal yang masih perlu dicek
Nomor halaman memakai halaman PDF. Bagian pelatihan Davinci dan angka FPR antara Tabel I dan II belum diturunkan ulang secara mandiri.
