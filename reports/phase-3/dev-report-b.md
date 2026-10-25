# Laporan developer Fase 3, tahap B (harness evaluasi)

## Yang dibuat
- `src/triagent/eval/metrics.py`: `score()` menghitung empat varian (CWE ketat/longgar x uncertain positif/negatif) dengan precision, recall, F1, FPR, TP retention total dan per kategori, tabel per item (outcome `tp`, `fn_lost`, `fn_missed`, `fp`, `tn`, `not_flagged`), dan `unlabeled_findings`. Pencocokan CWE memakai `normalize/cwe.py`.
- `src/triagent/eval/run.py`: `run_recorded()` memutar rekaman (verdict, biaya, latensi, terpotong), menolak metadata tak lengkap, hash prompt salah, panggilan ganda atau hilang, lalu menulis `report.json` (deterministik, kunci terurut) dan `report.md`.
- CLI `triagent eval score` dan `triagent eval run` persis sesuai kontrak di komentar gerbang. Tidak ada impor jaringan atau SDK LLM (I-10).
- `tests/test_eval.py` (10 tes, angka dihitung tangan di docstring, kasus sama dengan gerbang).
- `docs/EVAL-PITFALLS.md` (P1 sampai P9 sesuai catatan chasing-shadows-2026, metadata wajib, definisi R-06, daftar klaim yang tidak boleh dipakai).
- DESIGN-TRACE D-40 sampai D-42, DECISIONS A-29.

## Keputusan
- Kontrak gerbang tidak diubah dan gerbang tidak dilonggarkan. Hanya format rekaman yang ditetapkan konkret (lihat A-29f); `LlmCall` penuh baru ada di Fase 4.
- `fn_missed` masuk recall tetapi bukan TP retention; `not_flagged` tidak masuk FPR (A-29c).

## Ragu atau belum teruji
- Ambang kestabilan antar run belum ditetapkan (belum diketahui); jumlah minimal tiga run hanya dicatat di dokumen, belum ditegakkan kode.
- Koreksi siklus 1: di rancangan awal satu temuan dihitung untuk setiap item yang cocok, dan itu terjadi nyata pada BM-011/BM-022 (config.js baris 7 dan 8, toleransi 2). Sudah diganti pencocokan satu-ke-satu (A-29b).
- Belum diuji pada keluaran Semgrep nyata atas benchmark.

## Verifikasi
```
bash scripts/gate.sh 3
python -m pytest -q tests/test_eval.py
```
