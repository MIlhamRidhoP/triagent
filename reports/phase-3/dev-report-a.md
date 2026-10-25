# Laporan developer Fase 3, tahap A (benchmark, PoC, mutasi)

## Yang dibuat
- `scripts/gates/phase-3.sh`, ditulis lebih dulu, memuat tahap A dan tahap B. `GATE_STAGE=A|B|all` memilih tahap. Kasus metrik tahap B dihitung tangan di komentar gerbang (4 varian CWE ketat/longgar x uncertain positif/negatif, toleransi baris 0 dan 2, basis scanner saja, kasus 0/0).
- Aplikasi benchmark `benchmark/app` (`fieldnotes-bench`, Express 4.22.3, ~830 baris JS orisinal): 13 TP dan 10 jebakan FP, 11 kategori, 4 TP berbingkai "aman" dalam komentar, 1 jebakan berbingkai "bahaya". Database diganti mesin SQL mini (`lib/minisql.js`).
- `benchmark/ground-truth.yaml` (BM-001..BM-023), skema `schemas/ground-truth.schema.json` (dihasilkan dari model pydantic, ikut `export-schema --check`).
- `benchmark/poc/` (satu skrip per item, plus `_selftest.js`, `internal-service.js`), `benchmark/docker/` (Dockerfile, `compose.yaml`, lock npm).
- Kode: `src/triagent/benchmark/{groundtruth,jsmini,mutate,poc}.py`; CLI `triagent benchmark validate|mutate|poc|selftest`. Dokumen: `benchmark/README.md` (peringatan sengaja rentan), `benchmark/mutate/README.md`. Tes: `tests/test_benchmark.py` (24 tes, tanpa Docker).
- DESIGN-TRACE D-36 sampai D-39, DECISIONS A-28.

## Keputusan
- R-08 dipenuhi dengan `docker compose` dan jaringan `internal: true` (app, layanan internal untuk SSRF, dan kontainer PoC). Semua kontainer non-root, rootfs baca-saja, `cap_drop ALL`, `no-new-privileges`, batas sumber daya. Aplikasi menolak start tanpa `BENCHMARK_SANDBOX=1`.
- Label dari PoC: TP harus keluar 0, jebakan harus keluar 1, dan tiap PoC wajib punya `attempts >= 1` dan bukti, supaya jebakan tidak lulus karena PoC macet. Tiap PoC punya cek kontrol (fungsi normal jalan) yang mengubah kegagalan jadi kode 2 (galat harness), bukan "tidak tereksploitasi".
- Field `anchor` (teks yang tahan mutasi) menjadi bukti independen pergeseran baris. Mutator berupa tokenizer JS sendiri, bukan parser penuh; kebenaran varian dibuktikan validasi, `node --check`, dan PoC pada varian.
- Kode mutasi dan runner ada di `src/triagent/benchmark/`, bukan di `benchmark/mutate/` (folder itu berisi README), supaya bisa diuji pytest dan dipanggil lewat CLI.

## Hasil (dijalankan)
- `GATE_STAGE=A bash scripts/gates/phase-3.sh`: 36 PASS, 0 FAIL (sekitar 4 menit, termasuk 3 kali 23 PoC di Docker: asli dan 2 varian).
- `pytest`: 234 lulus. `ruff check` dan `ruff format --check` bersih. `scripts/check-hygiene.sh` lulus. Tidak ada kontainer atau jaringan benchmark tersisa.
- `GATE_STAGE=B`: gagal sampai tahap B dikerjakan (11 FAIL; sengaja).

## Ragu atau belum teruji
- Belum ada run Semgrep pada benchmark (dilarang di gerbang): belum diketahui berapa item yang terdeteksi scanner. Item prototype pollution menunjuk fungsi merge; scanner yang menandai call site akan dianggap meleset di tingkat baris.
- Ground truth dilabel agent dan PoC, belum oleh manusia kedua (risiko sirkularitas).
- Pembangunan image (`npm ci`) butuh jaringan registry sekali; gerbang memicunya bila image belum ada. Di mesin tanpa jaringan dan tanpa cache image, gerbang tahap A gagal.
- Diuji hanya di Windows dengan Docker Desktop; jalur Linux (CI) belum dijalankan. Tes pytest tidak butuh Docker.
- Aturan `go-safe` pernah rentan pada `//app.local//evil` di rancangan awal; sudah ditutup dan PoC BM-019 memeriksanya.

## Verifikasi
```
bash scripts/gates/phase-3.sh            # GATE_STAGE=A untuk tahap A saja
python -m pytest -q tests/test_benchmark.py
python -m triagent benchmark validate
python -m triagent benchmark selftest --out /tmp/st.json
python -m triagent benchmark poc --out /tmp/poc.json
python -m triagent benchmark mutate --out /tmp/v1 --seed 1 --ops rename,strip-comments,style
```

## Asumsi baru
A-28 (a sampai e) di `DECISIONS.md`. Antarmuka tahap B yang dikontrakkan gerbang: `triagent eval score` dan `triagent eval run` (format di komentar kepala gerbang).
