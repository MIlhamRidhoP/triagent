# contextual-bias-2026: bias bingkai pada review kode keamanan oleh LLM

Sumber: Alexopoulos, Alexopoulos, Spinellis, Mitropoulos. Measuring and Exploiting Contextual Bias in LLM-Assisted Security Code Review. arXiv 2603.18740v4 (23 Sep 2026). Sitasi yang benar: Alexopoulos dkk. 2026 (Mitropoulos adalah penulis terakhir; paper lain mengutipnya sebagai "Mitropoulos et al.").
Status verifikasi: dicek ke PDF pada 2026-10-26
Jenis: preprint (bobot lebih rendah dari paper venue)

## Klaim utama dan metode
Studi eksploratif enam LLM di bawah lima kondisi bingkai pada 250 pasang file rentan dan tertambal (CrossVul), lalu serangan injeksi metadata PR (reintroduksi 33 CVE di 20 proyek) terhadap Claude Code dan CodeRabbit. Serangan templat tidak efektif; serangan penyempurnaan iteratif oleh LLM efektif. Redaksi metadata mengembalikan deteksi.

## Angka aman dikutip
- Deteksi GPT-4o-mini pada kode rentan turun dari 240/247 (97,2%) kondisi netral ke 9/247 (3,6%) dengan bingkai "bebas bug" kuat. Bagian RQ1 B.1, Tabel II (hlm. 5 sampai 6).
- Tanpa bingkai, FPR tampak pada file tertambal minimal 88% di semua model kecuali Claude 3.5 Haiku (68,4%); dari 240 sampel yang dianalisis manual, 181 (75%) benar-benar false positive. RQ1 B.2.
- Serangan penyempurnaan: Claude Code 17/17, CodeRabbit 15/16, total 32/33 (97%). Tabel III dan ringkasan RQ3 (hlm. 9). Serangan templat: tidak membalik satu pun dari 16 penolakan Claude Code; CodeRabbit satu dari 13 dan tidak bertahan saat diulang (RQ2).
- Baseline tanpa bias: 16/17 ditolak Claude Code, 13/16 CodeRabbit (hlm. 7). Empat kasus diterima di baseline (1 Claude, 3 CodeRabbit, yang tiga akibat bug upstream CodeRabbit), jadi serangan murni 28 dari 29.
- Redaksi deskripsi PR (D-1) memulihkan 16 dari 32 kasus; redaksi seluruh metadata commit (D-2) memulihkan 12 dari 16 sisanya. Bagian RQ3, Tabel III (hlm. 9 sampai 10).

## Angka tidak aman atau jangan dikutip
- FPR 88% atau lebih adalah batas atas (sebagian alarm adalah bug asli lain di file).
- 97% mencampur kasus yang sudah lolos di baseline; jangan sebut sebagai efektivitas bersih.

## Batasan dan konflik kepentingan
Hanya dua tool ACR; penyerang memakai LLM yang sama dengan pipeline di studi Claude Code. Tidak diuji pada reviewer manusia. Pelabelan manual oleh dua penulis. Pendanaan belum diketahui. Preprint belum direview sejawat.

## Implikasi desain untuk triagent
Redaksi konteks sebelum dikirim ke LLM, termasuk bingkai "kode aman", komentar, dan deskripsi PR (D-03). Jangan beri LLM metadata yang bisa dimanipulasi sebagai bukti.

## Hal yang masih perlu dicek
Venue akhir. Angka Tabel II per model selain GPT-4o-mini belum dicocokkan satu per satu.
