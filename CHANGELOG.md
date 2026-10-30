# Changelog — LRMSyariah

Seluruh perubahan teknis substantif yang telah di-commit ke repository harus dicatat di sini.

## [Unreleased]

### Added — 2026-10-30
- Inisialisasi repository pusat proyek LRM Syariah.
- Panduan penggunaan repository dan kebijakan single source of truth.
- Instruksi untuk coding agent di `AGENTS.md`.
- `.gitignore` untuk mengurangi risiko ikut terunggahnya rahasia, data lokal, dan artefak build.
- Log keputusan awal di `docs/decision-log.md`.

### Imported — 2026-10-31 (engineering baseline)
- Mengimpor source WP0–WP2: Decimal engine foundation, 13 Pydantic source contracts, loader XLSX, DQ/exception validation, parameter dan akad mapping governance, Alembic migrations dan synthetic fixtures.
- Menambahkan test suite, GitHub Actions workflow, dokumentasi metodologi awal, review gate serta ringkasan audit untuk evaluasi kelanjutan WP3–WP13.
- Mempertahankan AGENTS.md, aturan keamanan repo public, dan riwayat decision-log awal.
- Pengujian lokal pada source paket: `PYTHONPATH=src python -m pytest -q` → 113 lulus; PostgreSQL/SSO/SAST/UAT aktual belum terbukti.

### Not yet implemented
- WP4–WP13, official LCR/NSFR calculation, regulatory outputs, production deployment, Bank UAT, independent model validation, dan parallel run.

### WP3 — 2026-10-31
- Added deterministic CalculationRun lifecycle, SHA-256 input/parameter/result snapshots and reproducibility.
- Added append-only hash-chain AuditEvent ledger and PostgreSQL migration 0002.
- Synthetic local tests: 126 passed (113 prior + 13 WP3). PostgreSQL end-to-end/Bank UAT pending.
- Release gate remains HOLD: WP5 reconciliation evidence, WP6 OIDC, Bank model validation and live infrastructure.
