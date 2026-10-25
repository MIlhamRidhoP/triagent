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
- **A-02.** Inti ditulis dengan Python, `requires-python >=3.12`, diuji di 3.12 dan 3.13 (mesin pemilik 3.13); bahasa target analisis v1 adalah JavaScript dan TypeScript, benchmark berupa aplikasi Node.js (Express).
- **A-03.** Scanner pertama adalah Semgrep OSS karena lokal, berformat SARIF, dan tanpa akun. SonarCloud dan CodeQL menyusul. Di Windows, Semgrep dijalankan lewat image Docker resmi dengan versi dipin. Tes hanya memakai fixture SARIF.
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
- **A-14.** Status lifecycle dan hasil verifikasi adalah dua field terpisah; `verified` diturunkan dari `verification.result == exploitable` (R-01).
- **A-15.** Id Finding deterministik; duplikat disimpan dengan `duplicate_of`, tidak dibuang (R-02).
- **A-16.** Setiap panggilan LLM dicatat sebagai entitas `LlmCall` di audit log, termasuk yang gagal (R-03).
- **A-17.** Evaluasi v1 mengukur triase atas temuan scanner; deteksi tanpa scanner adalah roadmap (R-06).
- **A-18.** Tafsiran I-10: larangan panggilan berbayar berlaku untuk tes dan pengembangan repo ini; pemakaian produk dibatasi `budget` (sementara, menunggu O-05, R-04).
- **A-19.** Skema `Finding` Fase 1 menyimpang dari SPEC bagian 5 sesuai resolusi Fase 0: field `status` menjadi `lifecycle` (tanpa nilai `verified`, R-01); `cwe` berupa daftar (R-07); ada `duplicate_of` (R-02); `triage[]` hanya memuat `model_id`, `verdict`, `reason`, `confidence`, `call_id`, sedangkan `prompt_hash`, token, biaya, dan latensi pindah ke entitas `LlmCall` (R-03); `human_decision` memuat `actor` (`human` atau `rule`) dan `rule_id`. `verified` adalah properti turunan, bukan field masukan. JSON Schema hanya menjamin bentuk dan enum; aturan lintas-field (I-01, I-02, fix_validated) ditegakkan validator pydantic.
- **A-20.** Konfigurasi `.triagent.yml` Fase 1: `models` wajib (tidak ada bawaan); `redact: false` wajib disertai `redact_experiment` (I-03: hanya untuk eksperimen tercatat); `mode` yang memuat verify wajib `verify.enabled: true`; kunci tak dikenal ditolak. Nilai `scanners` dibatasi semgrep, sonarcloud, codeql.
- **A-21.** Hash kepala audit log disimpan di berkas samping `<log>.head` (hash terakhir dan jumlah entri). Berkas ini berada di folder yang sama sehingga penyerang yang bisa menulis log juga bisa menulisnya; perlindungan penuh butuh `--expected-head` dari metadata run yang disimpan di tempat lain. Belum ada penulis metadata run (Fase 3). Penghapusan log dan head sekaligus hanya terdeteksi lewat `--expected-head`; `verify` menolak log yang hilang, kosong tanpa head, atau berisi baris kosong.
- **A-22.** Batas yang diterima setelah review Fase 1 (siklus 1): (a) model immutable (`frozen`), `model_construct` dimatikan, `model_copy(update=...)` divalidasi ulang, `transition()` memvalidasi ulang masukan; `object.__setattr__` dan mutasi list (`triage`, `cwe`) tetap mungkin dan hanya dijaga grep gerbang atas `src/`; (b) `rule_id` belum dicek ke registri aturan dan `reason` belum diredaksi (I-09), ditutup di fase aturan suppress dan redaksi; (c) `actor` dicek saat runtime; (d) audit log dikunci OS (`<log>.lock`) dan head direkonsiliasi saat append, hanya penghapusan total log dan head tanpa `--expected-head` yang tak terdeteksi; (e) Python 3.12 baru terbukti saat CI GitHub jalan, orkestrator memeriksa run CI branch fase sebelum titik cek, gerbang tidak mem-parse ci.yml; (f) `append` O(n) karena membaca seluruh log.

## Pertanyaan terbuka

- **O-01.** Tiga profil model untuk benchmark (penyedia, ID, tier). Ditentukan di Fase 4 bersama pemilik; ID harus diverifikasi ke dokumentasi penyedia saat itu.
- **O-02.** Sumber literatur yang belum dibaca (lihat `docs/literature/INDEX.md`, bagian belum dipilah) dipakai atau tidak.
- **O-03.** Venue dan detail sitasi yang masih bertanda [CEK] di catatan literatur.
- **O-04.** Nilai akhir `GUARD_LIMIT` dan anggaran API untuk fase 4 sampai 6.
- **O-05.** Teks final I-10 untuk pemakaian produk (butuh persetujuan pemilik; usulan R-04 opsi A di `reports/phase-0/resolution.md`). SPEC.md tidak diubah.
- **O-06.** Dukungan Semgrep native di Windows: belum diketahui.
- **O-07.** Venue dan DOI paper huynh-uwa: belum diketahui (PDF tidak memuat venue maupun DOI).
- **O-08.** Pendanaan dan konflik kepentingan belum diperiksa untuk gnieciak-2025, huynh-uwa, rajapaksha-2024, dan belum terlihat di teks sifting-noise-2026, contextual-bias-2026, chasing-shadows-2026, koterba-2026 (hanya pernyataan tanpa konflik).
