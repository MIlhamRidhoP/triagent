# Provenance fixture SARIF

`semgrep-1.181.1-js-sample.sarif` adalah keluaran NYATA Semgrep OSS 1.181.1 (bukan ditulis tangan), dihasilkan pada 2026-10-26 untuk `tests/fixtures/js-sample/app.js` (contoh JavaScript buatan sendiri, sengaja rentan).

- Image Docker: `semgrep/semgrep@sha256:3db5c7af55eb1f512eac0abf0ab69a97b52c74b5e9a27314c221aee1a78d7ab2` (tag `latest` saat ditarik, versi diverifikasi dengan `semgrep --version` = 1.181.1).
- Perintah: `docker run --rm -v <js-sample>:/src -w /src <image> semgrep scan --config p/javascript --config p/nodejs --metrics=off --sarif --output /src/out.sarif /src`
- Aturan diambil dari registry Semgrep (`p/javascript`, `p/nodejs`) saat dijalankan. Isi paket aturan berubah dari waktu ke waktu, jadi menjalankan ulang bisa memberi hasil lain; tes memakai berkas yang di-commit, bukan menjalankan Semgrep.
- Hasil: 4 result pada `app.js` (dua XSS di baris 9, `eval` di baris 19, open redirect di baris 29). Command injection (`exec`) dan hash MD5 tidak terdeteksi oleh paket aturan ini.
- Catatan format: `tool.driver.semanticVersion` memuat versi (bukan `version`), `artifactLocation.uri` berupa `/src/app.js` (path di dalam container), dan `fingerprints.matchBasedId/v1` berisi teks placeholder "requires login".
- Berkas disimpan apa adanya, tanpa suntingan.

`../golden/semgrep-1.181.1-js-sample.findings.json` adalah keluaran `triagent ingest ... --strip-prefix /src` yang diperiksa tangan terhadap 4 result di atas.
