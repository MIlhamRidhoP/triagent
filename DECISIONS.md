# DECISIONS.md

Tiga bagian: keputusan terkunci (K), asumsi yang boleh diubah (A), dan pertanyaan terbuka (O). Agent menambahkan asumsi baru di bagian A dengan nomor berikutnya. Mengubah bagian K butuh persetujuan pemilik.

## Keputusan terkunci

- **K-01.** Posisi produk: LLM melengkapi scanner (augmentasi), bukan menggantikan. Dasar: `docs/DESIGN-TRACE.md` D-01.
- **K-02.** Invarian I-01 sampai I-10 di `SPEC.md` mengikat.
- **K-03.** Fable tidak dipakai untuk peran agent mana pun. Model tertinggi yang dipakai adalah Opus 5.5.
- **K-04.** Pembagian model: orkestrator dan developer Sonnet 5.5; reviewer dan architect Opus 5.5 effort medium; explorer Haiku 5.5. Developer naik ke Opus di fase 3, 7, 8, 10 dan setelah dua kegagalan gerbang.
- **K-05.** Kebijakan git: author commit adalah pemilik repo, tanpa atribusi Claude di commit maupun PR, hanya orkestrator yang commit dan push, hanya ke branch fase, tanpa force push.
- **K-06.** Repo ini terpisah dari tugas akhir dan paper pemilik. Hasil paper orang lain dipakai sebagai dasar desain dan pembanding, bukan dikutip sebagai hasil triagent.
- **K-07.** PDF literatur tidak pernah masuk git. Catatan ringkasan buatan sendiri boleh.
- **K-08.** Tidak ada tanda pisah panjang di dokumen repo.
- **K-09.** Tidak ada temuan yang dibuang otomatis (I-01), apa pun verdict modelnya.

## Asumsi (boleh diubah)

- **A-01.** Repo berdiri sendiri, bukan bagian dari repo tugas akhir.
- **A-02.** Inti ditulis dengan Python 3.12; bahasa target analisis v1 adalah JavaScript dan TypeScript, benchmark berupa aplikasi Node.js (Express).
- **A-03.** Scanner pertama adalah Semgrep OSS karena lokal, berformat SARIF, dan tanpa akun. SonarCloud dan CodeQL menyusul.
- **A-04.** README dalam bahasa Inggris (repo publik); dokumen proses dalam bahasa Indonesia.
- **A-05.** `GUARD_LIMIT` bawaan 45 (persen meter mingguan, nilai absolut, bukan pemakaian harian). Ubah di `.claude/guard/config.env` sesuai kebutuhan dan setelah meter mingguan reset.
- **A-06.** Batas biaya bawaan per perintah eval berbayar adalah 5 USD, anggaran total diisi pemilik di prompt peluncuran.
- **A-07.** Field `effort: medium` di frontmatter agent belum diverifikasi didukung oleh versi Claude Code yang dipakai. Bila tidak didukung, atur effort lewat pengaturan model sesi. Diperiksa di Fase 0.
- **A-08.** Nilai `model: opus`, `sonnet`, `haiku` adalah alias. Pastikan di `/agents` bahwa alias menunjuk ke Opus 5.5, Sonnet 5.5, dan Haiku 5.5. Bila tidak, ganti dengan ID model lengkap (`claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`).
- **A-09.** Format aturan izin di `.claude/settings.json` (deny untuk `git config`, force push, dan membaca `.env`) diverifikasi lewat `/permissions` di Fase 0.
- **A-10.** Guard bergantung pada status line CLI. Bila memakai ekstensi IDE, status line tidak berjalan dan guard buta; gunakan terminal. Di Windows gunakan Git Bash atau WSL dan pastikan `jq` terpasang.
- **A-11.** Hook `PreToolUse` diasumsikan juga berlaku untuk pemanggilan alat di dalam subagent. Belum diverifikasi; tes di Fase 0 dengan `GUARD_LIMIT` sengaja diset rendah.
- **A-12.** Lisensi belum dipilih. Tanpa lisensi, repo publik berarti semua hak dilindungi. Pemilik memutuskan sebelum rilis.
- **A-13.** Atribusi: `attribution.commit` dan `attribution.pr` dikosongkan. Trailer URL sesi dikelola kunci lain di beberapa versi, jadi hook `commit-msg` menjadi pengaman cadangan. Periksa `git log -1 --format=full` setelah commit pertama.

## Pertanyaan terbuka

- **O-01.** Tiga profil model untuk benchmark (penyedia, ID, tier). Ditentukan di Fase 4 bersama pemilik; ID harus diverifikasi ke dokumentasi penyedia saat itu.
- **O-02.** Sumber literatur yang belum dibaca (lihat `docs/literature/INDEX.md`, bagian belum dipilah) dipakai atau tidak.
- **O-03.** Venue dan detail sitasi yang masih bertanda [CEK] di catatan literatur.
- **O-04.** Nilai akhir `GUARD_LIMIT` dan anggaran API untuk fase 4 sampai 6.
