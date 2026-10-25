# Resolusi Fase 1 (siklus 1)

Dasar: semua butir di bawah adalah keputusan teknik, tanpa dasar literatur. Tidak ada yang mengubah invarian atau keputusan terkunci; semuanya menegakkan I-01, I-02, I-06 yang sudah ada.

R-01: valid. Validator lintas-field hanya jalan saat konstruksi; penugasan, `model_construct`, dan juga `model_copy(update=...)` (tidak disebut reviewer, sama bocornya) melewatinya.
Opsi A: `frozen=True` di `Strict` (semua model, termasuk nested `Verification`, `Fix`, `HumanDecision`); override `model_construct` di `Strict` agar melempar `TypeError`; override `model_copy` agar `update` divalidasi ulang lewat `model_validate({**self.model_dump(), **update})`; `transition()` memvalidasi ulang `finding` masukan sebelum apa pun. Murah, tidak mengubah skema JSON.
Opsi B: `validate_assignment=True` plus validator dijalankan ulang. Nested tetap bisa diubah (`f.verification.result = ...` tidak memicu validator Finding), dan aturan lintas-field bisa gagal di tengah dua penugasan berurutan. Lebih rapuh.
Rekomendasi: A. Model immutable cocok dengan `transition()` yang sudah mengembalikan objek baru. `object.__setattr__` dan mutasi list (`triage`, `cwe`) tetap mungkin; dicatat sebagai batas (lihat bawah) karena tidak menyentuh lifecycle atau `verified`.
Selesai bila: penugasan `lifecycle`, `human_decision`, `verification.result`, `fix.tests_passed` melempar `ValidationError`; `Finding.model_construct(...)` melempar `TypeError`; `model_copy(update={"lifecycle": "suppressed"})` melempar `ValidationError`; `transition()` atas Finding yang dirusak via `object.__setattr__` melempar dan tidak menulis audit.

R-02: valid. Gerbang hanya menghitung tes.
Opsi A: tambah tes di `tests/test_invariants.py` untuk tiap jalur pada R-01 dan naikkan ambang gerbang ke >= 18. Opsi B: A ditambah skrip serangan mandiri di `scripts/gates/phase-1.sh` (tidak bergantung berkas tes) dan grep yang gagal bila `src/` memuat `model_construct` atau `object.__setattr__`.
Rekomendasi: B. Gerbang harus menangkap regresi walau tes dihapus atau dilemahkan.
Selesai bila: gerbang punya pemeriksaan "serangan penugasan/construct/copy ditolak" dan "src tanpa bypass"; membalik `frozen=False` sementara membuat gerbang FAIL.

R-03: valid, ditambah: `os.replace` di Windows gagal bila `.head` sedang dibuka proses lain.
Opsi A: kunci OS pada berkas `<log>.lock` dengan stdlib: `fcntl.flock(LOCK_EX)` di POSIX, `msvcrt.locking(fd, LK_NBLCK, 1)` dalam loop retry dengan batas waktu (galat `AuditError`) di Windows, dibungkus `threading.Lock` per path. `append` dan `verify` memegang kunci. Di dalam kunci, `append` merekonsiliasi head: head (atau GENESIS/0 bila tidak ada) tepat satu entri di belakang log dan entri terakhir terhubung rantainya, berarti crash di antara tulis log dan head, jadi head diperbaiki lalu lanjut; head di depan log atau tidak cocok, berarti `AuditError`, menolak menulis. Urutan tetap: tulis baris, fsync, lalu head via tmp dan `os.replace`. Tanpa dependensi baru.
Opsi B: paket `filelock`. Lebih sedikit kode platform, tetapi dependensi baru dan rekonsiliasi head tetap harus ditulis.
Rekomendasi: A. Berkas lock tidak dihapus agar tidak ada kunci basi; kunci OS lepas otomatis saat proses mati.
Selesai bila: tes 4 proses (`multiprocessing` spawn, jalan di Windows) x 25 append menghasilkan 100 entri, seq 0..99 unik, `verify` ok; tes thread serupa; tes crash (patch `_write_head` melempar setelah tulis log) lalu append berikutnya memperbaiki head dan `verify` ok; tes head di depan log membuat `append` melempar. Gerbang: 4 proses latar belakang ditambah `wait`, lalu `verify-audit` lulus dan jumlah entri 100.

R-04: valid.
Opsi A: `verify` gagal bila berkas log tidak ada, atau ada tetapi nol entri tanpa head (keadaan yang tidak pernah dibuat `append`); baris kosong selain baris akhir setelah newline terakhir menjadi galat. Opsi B: hanya dokumentasi.
Rekomendasi: A, ditambah catatan di A-21: penghapusan log dan head sekaligus hanya terdeteksi lewat `--expected-head`. `test_empty_log_verifies` diganti sesuai perilaku baru.
Selesai bila: `verify-audit` keluar non-nol untuk berkas hilang, berkas kosong tanpa head, dan baris kosong yang disisipkan; ketiga kasus juga diuji di gerbang bagian 7.

R-05: sebagian. Celah nyata hanya `actor` tanpa cek runtime; registri aturan dan redaksi belum ada di fase ini.
Opsi A: `transition()` menolak `actor` di luar `get_args(Actor)`; validasi `rule_id` dan redaksi `reason` ditunda. Opsi B: membuat registri aturan sekarang, di luar lingkup fase.
Rekomendasi: A. Catat di `DECISIONS.md` sebagai A-22: `rule_id` belum dicek ke registri aturan, `reason` belum diredaksi (I-09), ditutup saat fase aturan suppress dan redaksi; tambah entri D di DESIGN-TRACE sebagai keputusan teknik.
Selesai bila: tes `actor="admin"` melempar `TransitionError` tanpa entri audit; A-22 ada.

R-06: valid, minor.
Opsi A: gerbang mem-parse `ci.yml` dengan `yaml` dan memeriksa matriks serta langkah. Opsi B: catat batas: 3.12 baru terbukti saat CI GitHub jalan; orkestrator memeriksa hasil run CI branch fase sebelum titik cek.
Rekomendasi: B. Parse YAML tetap bukan bukti perilaku.
Selesai bila: `DECISIONS.md` mencatat batas ini (gabung di A-22) dan dev-report menyebut status run CI.

Batas yang cukup dicatat (A-22): `object.__setattr__` dan mutasi list di model; `rule_id` tanpa registri; `reason` tanpa redaksi; penghapusan total log dan head tanpa `--expected-head`; 3.12 belum terbukti lokal; `append` O(n).
