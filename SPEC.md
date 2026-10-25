# SPEC.md: spesifikasi triagent

Status: v0.1, draf awal. Divalidasi oleh Architect di Fase 0. Perubahan pada bagian Invarian butuh persetujuan pemilik repo.

## 1. Masalah

Scanner SAST menghasilkan alert dalam jumlah besar. Sebagian besar tidak relevan atau tidak jelas, dan tidak ada yang menjawab tiga pertanyaan developer: apakah celah ini benar-benar bisa dieksploitasi, lewat jalur mana, dan bagaimana memperbaikinya. Akibatnya alert diabaikan dan celah yang nyata ikut terkubur. Dasar ilmiah motivasi ini dicatat di `docs/DESIGN-TRACE.md` (D-01, D-02, D-11).

## 2. Tujuan dan batasan v1

Tujuan:
- G1. Menerima keluaran scanner dalam format SARIF 2.1.0, menormalkan, dan membuang duplikat.
- G2. Triase berbasis LLM multi-model yang bisa diaudit, tanpa pernah membuang temuan.
- G3. Konteks kode yang tajam (slice dari sumber input ke titik berbahaya) sebagai pengganti file utuh.
- G4. Verifikasi eksploit di sandbox yang terisolasi.
- G5. Usulan perbaikan yang teruji, diajukan lewat pull request.
- G6. Evaluasi terukur dan bisa diulang (benchmark dengan ground truth terverifikasi).
- G7. Pelaporan: komentar PR, SARIF, dashboard, laporan statis.

Bukan tujuan v1:
- Integrasi DAST penuh (verifikasi sandbox bukan pengganti DAST).
- SCA, IaC, dan secret scanning (roadmap).
- Auto-merge perbaikan.
- Bahasa target analisis selain JavaScript dan TypeScript.
- Fine-tuning model.
- Layanan multi-tenant.

## 3. Invarian

Diuji di gerbang. Pelanggaran adalah temuan kritis.

- **I-01.** Tidak ada temuan yang dihapus atau di-suppress otomatis. Verdict model hanyalah anotasi. Suppress hanya lewat keputusan manusia atau aturan eksplisit yang tercatat di audit log.
- **I-02.** LLM mengusulkan, bukti yang memutuskan. Status `verified` hanya bisa diberikan oleh hasil eksekusi di sandbox, tidak pernah oleh opini model. Hasil `not_reproduced` tidak berarti false positive.
- **I-03.** Konteks yang dikirim ke LLM diredaksi lebih dulu: komentar, nama yang bocorkan jawaban, deskripsi PR, dan metadata yang memberi bingkai "kode ini aman". Redaksi bisa dimatikan hanya untuk eksperimen yang tercatat.
- **I-04.** Kode yang dianalisis adalah data tidak tepercaya. Prompt memisahkannya dari instruksi, dan ada tes injeksi (Fase 10).
- **I-05.** CWE dari scanner adalah jangkar. Pencocokan dengan ground truth dilakukan per keluarga CWE (varian ketat dan longgar dilaporkan keduanya).
- **I-06.** Setiap panggilan LLM mencatat model id, tanggal, parameter yang dikirim, hash prompt, token, biaya USD, latensi, dan status. Prompt diversi dan di-hash. Run yang gagal tetap dicatat.
- **I-07.** Triagent hanya memberi rekomendasi dan usulan patch di branch terpisah. Tidak pernah menulis ke branch default.
- **I-08.** Sandbox tanpa jaringan keluar, tanpa kredensial nyata, non-root, sistem berkas hanya baca kecuali area kerja, batas CPU, memori, dan waktu.
- **I-09.** Secret dan data pribadi diredaksi sebelum keluar dari mesin (ke LLM, log, laporan).
- **I-10.** Tes berjalan offline. LLM di tes diganti rekaman atau fake. Panggilan berbayar hanya lewat perintah eval yang eksplisit dengan batas anggaran.

## 4. Arsitektur

```
scanner (SARIF)
  -> ingest -> normalize/dedup
  -> context (slice + redact)
  -> triage (LLM, multi-model, JSON berskema)
  -> verify (PoC di sandbox)
  -> prioritize
  -> fix (patch + tes + scan ulang)
  -> report (komentar PR, SARIF, dashboard, laporan statis)

audit log, biaya, dan latensi dicatat di setiap tahap
```

Modul di `src/triagent/`: `ingest/`, `normalize/`, `context/`, `llm/`, `triage/`, `verify/`, `fix/`, `report/`, `eval/`, `audit.py`, `config.py`, `cli.py`.

Lapisan model (`llm/`): satu antarmuka adapter, penyedia dapat ditukar lewat konfigurasi. Model id tinggal di `config/models.yaml`, tidak pernah di kode. Pemilihan model di benchmark mengikuti prinsip apple-to-apple: tier yang setara, parameter yang sama, semua lewat API.

## 5. Model data

`Finding` (pydantic, diekspor sebagai JSON Schema):
- `id`, `source_tool`, `rule_id`, `cwe`, `cwe_family`, `owasp_category`
- `location` (file, baris awal dan akhir), `message`, `severity_scanner`
- `status`: `raw` -> `deduped` -> `triaged` -> `verified` -> `fix_proposed` -> `fix_validated`; cabang `suppressed` (hanya manusia atau aturan tercatat)
- `triage`: daftar verdict per model: `model_id`, `verdict` (`likely_tp` | `likely_fp` | `uncertain`), `reason`, `confidence`, `prompt_hash`, `tokens`, `cost_usd`, `latency_ms`
- `verification`: `result` (`exploitable` | `not_reproduced` | `not_attempted`), `evidence_path`, `sandbox_run_id`
- `fix`: `patch_path`, `tests_passed`, `rescan_clean`, `new_findings`
- `human_decision`: `accepted` | `rejected` | `suppressed` dengan alasan dan waktu

Setiap perubahan status menulis satu entri ke audit log (JSON lines, berantai hash).

## 6. Konfigurasi

`.triagent.yml` di repo yang dipindai (sketsa, final di Fase 1):

```yaml
scanners: [semgrep]
languages: [javascript, typescript]
models: [profile-a, profile-b, profile-c]   # nama profil di config/models.yaml
mode: triage            # triage | triage+verify | triage+verify+fix
redact: true
budget:
  max_usd_per_invocation: 5
verify:
  enabled: false
  sandbox: docker
```

## 7. Evaluasi

Metrik: precision, recall, F1, FPR, **TP retention per kategori**, tabel per item (hanya scanner, hanya LLM, keduanya, tidak ada), biaya USD per run, latensi, dan kestabilan antar run (minimal tiga run per konfigurasi).

Protokol:
- Ground truth diverifikasi PoC, dibangun sendiri pada aplikasi benchmark yang baru (bukan aplikasi rentan yang terkenal) agar tidak terkontaminasi data latih.
- Termasuk jebakan false positive yang disengaja.
- Uji mutasi: ganti nama fungsi, hapus komentar, ubah gaya, lalu bandingkan hasil.
- Prompt dibekukan dan di-hash sebelum run resmi. Satu prompt untuk semua model harus dijustifikasi, ditambah satu varian pembanding.
- Temuan di luar ground truth ditriase manual di file terpisah.
- Daftar periksa jebakan evaluasi ada di `docs/EVAL-PITFALLS.md` (dibuat di Fase 3 dari catatan Chasing Shadows).

## 8. Model ancaman alat ini

| Ancaman | Contoh | Pengendali |
|---|---|---|
| Injeksi prompt lewat kode | komentar "abaikan temuan ini" | I-04, I-01, tes injeksi Fase 10 |
| Kebocoran data ke penyedia LLM | secret atau data pribadi ikut terkirim | I-09, opsi model lokal |
| Sandbox escape | PoC buatan LLM menyerang host | I-08, tes egress dan isolasi |
| PoC berbahaya | skrip merusak | I-08, I-07, batas waktu |
| Bingkai menyesatkan | PR bilang "ini aman" | I-03 |
| Rantai pasok | dependensi jahat | audit dependensi Fase 10 |
| Kebocoran lewat log | token di log | I-09, hygiene gate |

## 9. Stack

Python 3.12, pydantic v2, typer, httpx, jsonschema, pytest, ruff, tree-sitter (binding Python), FastAPI (Fase 9), Docker (sandbox), GitHub Actions. Aplikasi benchmark: Node.js (Express). Semua pilihan ini bisa diubah Architect di Fase 0 dengan alasan tertulis di `DECISIONS.md`.

Scanner pertama: Semgrep OSS (lokal, SARIF bawaan, tanpa akun). Adapter SonarCloud dan CodeQL menyusul setelah inti stabil.

## 10. Struktur direktori

```
.claude/        agent, pengaturan, guard kuota
.githooks/      commit-msg, pre-commit
.github/        workflow CI
benchmark/      aplikasi uji dan ground truth (Fase 3)
config/         models.yaml, profil
docs/           DESIGN-TRACE, LAUNCH, literature/
reports/        laporan per fase
scripts/        gate, boundary, guard, hygiene, setup
src/triagent/   kode produk
tests/          tes offline
```

## 11. Definisi selesai v1.0

- Semua gerbang fase 0 sampai 10 lulus dan tercatat di `reports/`.
- Benchmark menghasilkan tabel metrik lengkap untuk minimal tiga model, tiga run, dengan metadata.
- Tes injeksi, egress sandbox, dan redaksi lulus.
- GitHub Action bisa dipasang di repo lain dengan beberapa baris YAML.
- README, SECURITY.md, dan dokumentasi pemasangan lengkap.
- Setiap entri `DESIGN-TRACE.md` punya dasar atau ditandai keputusan teknik.
