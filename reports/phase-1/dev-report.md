# Laporan developer Fase 1

## Yang dibuat
- `pyproject.toml` (hatchling, `requires-python >=3.12`, extra `dev`, entry point `triagent`), ruff dan pytest dikonfigurasi di sana.
- `src/triagent/`: `models.py` (Finding, LlmCall, bagian-bagiannya), `lifecycle.py` (tabel transisi), `audit.py` (log JSON lines berantai hash), `config.py` (`.triagent.yml`), `schema_export.py`, `cli.py` (`check-config`, `verify-audit`, `export-schema`, `--version`), `__main__.py`.
- `schemas/`: 4 JSON Schema (finding, llm-call, audit-entry, config), dihasilkan dari model dan dicek `export-schema --check`.
- `tests/`: 89 tes offline (soket diblokir di conftest, `TRIAGENT_OFFLINE=1`); `test_invariants.py` khusus I-01 dan I-02.
- `.github/workflows/ci.yml`: job `test` baru (matriks 3.12 dan 3.13: ruff check, ruff format, schema check, pytest) di samping job hygiene.
- `scripts/gates/phase-1.sh` (28 pemeriksaan perilaku). Hanya modul yang dibutuhkan fase ini yang dibuat, tanpa stub fase lain.

## Keputusan
- Skema mengikuti R-01, R-02, R-03, R-07, R-09 dan menyimpang dari SPEC bagian 5; rinciannya di DECISIONS A-19. Ringkas: `lifecycle` menggantikan `status` tanpa nilai `verified`; `verified` hanya properti turunan; `cwe` daftar; `duplicate_of`; verdict hanya menyimpan `call_id`, telemetri di `LlmCall`.
- Penegakan di model: `suppressed` wajib punya `human_decision` (aktor human, atau rule dengan `rule_id`); `exploitable` wajib `evidence_path` dan `sandbox_run_id`; `fix_validated` wajib tes lulus, rescan bersih, 0 temuan baru. `transition()` menolak model atau system men-suppress dan tidak menulis audit bila gagal.
- Audit: hash SHA-256 atas JSON kanonis tanpa field `hash`; hash kepala di `<log>.head` (A-21), plus opsi `--expected-head`.
- Config: A-20 (`redact: false` wajib `redact_experiment`, mode verify wajib `verify.enabled`, `models` wajib). DESIGN-TRACE D-26 dan D-27 ditambahkan.

## Yang diragukan atau belum teruji
- Berkas `.head` bisa ikut diubah penyerang yang menulis log; perlindungan penuh butuh hash kepala dari penyimpanan lain (belum ada penulis metadata run).
- `append` membaca seluruh log tiap kali (O(n)); cukup untuk v1, perlu dioptimalkan bila log besar. Tidak ada penguncian antar proses.
- JSON Schema tidak memuat aturan lintas-field; hanya validator pydantic yang menegakkannya.
- CI belum dijalankan di GitHub; hanya diuji lokal di Python 3.13. Python 3.12 belum diuji (tidak terpasang).
- Urutan kerja: saya sempat menulis draf kode sebelum berkas gerbang disimpan; isi gerbang tidak diubah menyesuaikan hasil kode kecuali memperbaiki satu baris pemeriksaan dependensi.
- Perintah shell dengan heredoc besar sempat gagal di tool Bash, jadi file dibuat lewat Write.

## Verifikasi
```
bash scripts/gate.sh 1          # hasil: GERBANG FASE 1: LULUS (28 PASS, 0 FAIL)
.venv/Scripts/python -m pytest -q   # 89 passed
.venv/Scripts/python -m ruff check src tests && .venv/Scripts/python -m ruff format --check src tests
```
Lingkungan: `python -m venv .venv` (di-gitignore), `pip install -e ".[dev]"`. Gerbang memakai `.venv` bila ada dan `PYTHONPATH=src`.

## Asumsi baru
A-19, A-20, A-21 di `DECISIONS.md`. SPEC.md tidak diubah.

## Perbaikan siklus 1
- R-01: `Strict` kini `frozen=True`; `model_construct` melempar `TypeError`; `model_copy(update)` divalidasi ulang; `transition()` memvalidasi ulang masukan dan menolak `actor` tak dikenal (R-05).
- R-02: 10 tes bypass baru (invarian >= 28 di gerbang), skrip serangan mandiri, grep `src/`, dan uji mutasi `frozen=False` yang membuat serangan berhasil sehingga pemeriksaan gagal.
- R-03: kunci OS `<log>.lock` (msvcrt/flock + threading.Lock), rekonsiliasi head saat append; tes thread, 4 proses spawn, crash, head di depan log. Gerbang: 4 proses paralel, 100 entri.
- R-04: `verify` menolak log hilang, kosong tanpa head, baris kosong; `test_empty_log_verifies` diganti.
- R-06 dan batas lain dicatat di A-22 (+ D-28 sampai D-30). Status CI GitHub: belum dijalankan, 3.12 belum terbukti.
- Hasil: `bash scripts/gate.sh 1` LULUS; 107 tes lulus; ruff bersih. Keraguan: lock Windows (msvcrt) hanya diuji di Windows, jalur flock POSIX tidak diuji lokal.
