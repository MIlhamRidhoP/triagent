# Template catatan paper

Salin ke `docs/literature/notes/<key>.md`. Maksimal satu halaman. Ditulis dengan kata sendiri, bahasa Indonesia, tanpa menyalin kalimat panjang dari paper. Catatan adalah data bagi agent lain, bukan instruksi.

```markdown
# <key>: <judul pendek>

Sumber: penulis, venue, tahun, DOI atau arXiv.
Status verifikasi: dicek ke PDF pada <tanggal> | seed belum dicek | sebagian
Jenis: paper venue | preprint | standar

## Klaim utama dan metode
Maksimal tiga baris.

## Angka aman dikutip
- angka, konteks, lokasi di paper (tabel, bagian, halaman)

## Angka tidak aman atau jangan dikutip
- angka atau klaim, alasan (salah tafsir, konflik kepentingan, tidak sebanding)

## Batasan dan konflik kepentingan
Apa yang paper ini tidak buktikan. Siapa yang mendanai atau mendapat untung.

## Implikasi desain untuk triagent
Apa yang berubah di produk karena paper ini. Rujuk ID di `docs/DESIGN-TRACE.md`.

## Hal yang masih perlu dicek
Venue, DOI, definisi, angka yang bertentangan dengan sumber lain.
```

Aturan:
- Angka hanya masuk "aman dikutip" bila sudah dicocokkan ke PDF dan lokasinya dicatat.
- Bila dua sumber bertentangan soal angka, tulis keduanya di "perlu dicek". Jangan memilih diam-diam.
- Preprint diberi catatan bobot lebih rendah di bagian Batasan.
