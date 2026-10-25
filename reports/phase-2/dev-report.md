# Laporan developer Fase 2

## Yang dibuat
- `scripts/gates/phase-2.sh` ditulis dan disimpan SEBELUM kode apa pun (gerbang memakai hitungan independen dari parser, kasus sintetis hitung tangan, dan SARIF cacat).
- `src/triagent/ingest/sarif.py` (parser SARIF 2.1.x ke `Finding`), `ingest/semgrep.py` (adapter Docker, image dipin digest, versi 1.181.1).
- `src/triagent/normalize/cwe.py` + `data/cwe-families.yaml` (934 pemetaan dari MITRE CWE v4.20, view 1000, sha256 dan aturan tercatat di `meta`), `normalize/dedup.py`, `normalize/__init__.py` (`normalize_findings`).
- `scripts/build_cwe_families.py`: pembangun tabel dari XML MITRE (dijalankan dengan `python -I`).
- CLI `triagent ingest SARIF|--run-semgrep DIR [--out] [--audit-log] [--strip-prefix] [--line-window] [--no-dedup]`. Kode keluar 1: dokumen bukan SARIF; 2: ada result bukan-objek (keluaran tetap ditulis).
- Fixture NYATA: `tests/fixtures/sarif/semgrep-1.181.1-js-sample.sarif` dari Semgrep 1.181.1 lewat Docker pada `tests/fixtures/js-sample/app.js` (4 result), `PROVENANCE.md` memuat digest dan perintah, golden `tests/fixtures/golden/*.findings.json` diperiksa tangan.
- Tes baru: `test_sarif.py`, `test_cwe.py`, `test_dedup.py`, `test_semgrep.py`, `test_ingest_cli.py` (total 209 tes, offline).

## Keputusan (rinci di DECISIONS A-23 sampai A-27, DESIGN-TRACE D-31 sampai D-35)
- Id deterministik dari (tool, rule, file, potongan kode ternormalisasi, kemunculan). Map `fingerprints` diabaikan karena Semgrep mengisinya "requires login" (temuan dari fixture nyata).
- Keluarga CWE = Class/Pillar terdekat di hierarki MITRE. Diverifikasi dari data: 79->74, 95->74, 89->943, 78->77, 601->610, 862 dan 863 ->285. Satu-satunya data manual adalah kelompok 862/863, dan pembangun menyatakannya gagal bila MITRE mengubah induknya. Tidak ada pasangan dari ingatan.
- Dedup: berkas sama + baris bertumpuk (jendela 2) + keluarga beririsan; aturan yang sama harus bertumpuk persis; hasil tidak bergantung urutan masukan. Pada fixture nyata, dua alert XSS baris 9 (`raw-html-format`, `direct-response-write`) menjadi satu duplikat; kanonik dipilih lewat rule_id karena severity dan baris sama.
- Docker: kutipan pembaruan R-05 perlu dicatat, Semgrep mengisi `tool.driver.semanticVersion`, bukan `version`. Docker Desktop awalnya mati; saya menyalakannya (Start-Process) untuk menarik image.

## Diragukan atau belum teruji
- `line_window=2` dan aturan kanonik adalah keputusan teknik tanpa validasi di benchmark; keluarga CWE longgar menyatukan XSS dan Eval Injection (keduanya CWE-74) walau beda kerentanan. Dedup hanya menandai, jadi risikonya anotasi salah, bukan hilangnya temuan, tetapi fase triase jangan mewarisi verdict kanonik tanpa pertimbangan.
- Hanya satu fixture nyata (JavaScript, 4 result, tanpa `partialFingerprints`). Jalur `partialFingerprints`, `ruleIndex`, `artifacts[].index`, dan tag CWE bentuk CodeQL hanya diuji dengan SARIF sintetis. Taksonomi/relationships SARIF belum dibaca.
- Adapter Docker diuji dengan runner palsu di tes; sekali dijalankan nyata secara manual (`triagent ingest --run-semgrep tests/fixtures/js-sample`) dan hasilnya identik dengan golden. Itu butuh jaringan (registri aturan) sehingga tidak ada di gerbang. Hasil paket aturan bisa berubah di masa depan.
- Git Bash mengubah argumen `/src` menjadi path Windows; gerbang mengatur `MSYS_NO_PATHCONV=1`. Pengguna Git Bash perlu hal yang sama untuk `--strip-prefix /src`.
- Heredoc dengan escape `\n` di tool Bash rusak lagi; berkas dibuat lewat Write/Edit.

## Verifikasi
```
bash scripts/gate.sh 2
.venv/Scripts/python -m pytest -q          # 209 passed
.venv/Scripts/python -m ruff check src tests && .venv/Scripts/python -m ruff format --check src tests
# opsional, butuh Docker dan jaringan:
MSYS_NO_PATHCONV=1 .venv/Scripts/python -m triagent ingest --run-semgrep tests/fixtures/js-sample --out /tmp/o.json
```

## Asumsi baru
A-23 sampai A-27 dan O-09 di `DECISIONS.md`. SPEC.md tidak diubah. Berkas MITRE yang diunduh (`cwec_v4.20.xml`, sha256 tercatat di tabel) tidak disimpan di repo; hanya hasil turunannya.
