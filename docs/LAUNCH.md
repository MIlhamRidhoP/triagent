# LAUNCH.md: cara menjalankan

Pemilik hanya perlu menempel beberapa prompt pendek. Semua aturan ada di `CLAUDE.md`, `SPEC.md`, dan `PLAN.md`.

## Persiapan sekali di awal

1. Clone repo dan masuk ke foldernya. Gunakan terminal (bukan ekstensi IDE), supaya guard kuota bisa membaca status line.
2. Pastikan identitas git benar sebelum commit pertama:
   ```bash
   git config user.name "Nama Kamu"
   git config user.email "email-github-kamu-atau-noreply"
   ```
3. Jalankan:
   ```bash
   bash scripts/setup.sh
   bash scripts/install-guard.sh
   bash scripts/guard-selftest.sh
   ```
4. Atur batas kuota di `.claude/guard/config.env` (`GUARD_LIMIT`). Angkanya adalah persen meter mingguan secara absolut. Setelah reset mingguan, meter kembali ke 0.
5. Taruh PDF literatur di `docs/literature/pdf/` (diabaikan git). Penamaan yang disarankan ada di `docs/literature/pdf/README.md`.
6. Jalankan Claude Code dari terminal dengan model Sonnet sebagai sesi utama:
   ```bash
   claude --model sonnet
   ```
7. Cek manual satu kali di dalam Claude Code:
   - `/agents`: pastikan reviewer dan architect memakai Opus 5.5, developer Sonnet 5.5, explorer Haiku 5.5, dan tidak ada Fable.
   - `/permissions`: pastikan aturan deny di `.claude/settings.json` terbaca.
   - Bila alias model tidak menunjuk ke versi yang benar, ganti dengan ID lengkap (lihat `DECISIONS.md` A-08).
8. Siapkan kunci API hanya saat dibutuhkan (Fase 4 ke atas). Salin `.env.example` menjadi `.env` dan isi. File `.env` diabaikan git.

## Prompt 1: fase 0 sampai titik cek C1

```
Baca CLAUDE.md, SPEC.md, PLAN.md, dan DECISIONS.md. Kamu adalah orkestrator.
Kerjakan fase 0 sampai fase 3 mengikuti PLAN.md dan alur di CLAUDE.md. Berhenti di
titik cek C1 dan kirim satu laporan singkat. Jangan mulai fase 4. Jangan ada
panggilan API berbayar. Catat pemakaian kuota per fase di PLAN.md. Jika guard
kuota menghentikan sesi, simpan keadaan di PLAN.md dan laporkan.
```

## Prompt 2: setelah C1, menuju C2

Isi anggaran API terlebih dulu (angka dolar total untuk fase 4 sampai 6).

```
Lanjut. Merge branch fase 0 sampai 3 ke main sesuai aturan git di CLAUDE.md.
Kerjakan fase 4 sampai 6 dan berhenti di titik cek C2. Anggaran API total untuk
fase ini: ISI_DOLAR USD. Jangan melewatinya. Jika anggaran tidak cukup untuk
validasi nyata, gunakan rekaman dan laporkan.
```

## Prompt 3: setelah C2, menuju C3

```
Lanjut. Merge fase 4 sampai 6 ke main. Kerjakan fase 7 dan 8, berhenti di titik
cek C3. Fase 7 memakai developer Opus dan wajib lulus tes egress sandbox sebelum
apa pun dijalankan terhadap kode target. Anggaran API: ISI_DOLAR USD.
```

## Prompt 4: setelah C3, menuju C4

```
Lanjut. Merge fase 7 dan 8 ke main. Kerjakan fase 9 dan 10, berhenti di titik
cek C4 dengan laporan serah terima akhir.
```

## Bila sesi berhenti di tengah jalan

Guard kuota, batas konteks, atau gerbang yang gagal bisa menghentikan sesi. Mulai sesi baru dan tempel:

```
Baca CLAUDE.md dan PLAN.md bagian "Status berjalan". Lanjutkan dari langkah
terakhir yang lulus. Jangan mengulang pekerjaan yang sudah lulus gerbang.
```

## Hal yang dilakukan pemilik

- Membalas "lanjut" atau koreksi singkat di tiap titik cek.
- Mengisi anggaran API dan kunci saat diminta.
- Memeriksa `git log -1 --format=full` setelah commit pertama: author harus kamu, tanpa trailer.
- Memutuskan lisensi sebelum rilis publik.
