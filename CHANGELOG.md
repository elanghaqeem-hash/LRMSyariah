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

### Analytical prototypes — 2026-10-31 (nonregulatory)
- Added candidate pure LCR, ASF/RSF NSFR, 19-bucket survival, shock stress, DCR, ILAAP concentration calculations with all factors external and evidence tagged.
- Added GL three-layer reconciliation and deterministic sanitized audit ZIP prototype.
- Engineering tests local: 160 passed, 91.68% measured coverage. No OJK filing certification, Bank source mapping or OIDC / PostgreSQL UAT.
- Complete WP4–WP13 remains gated; details in docs/engineering/WP4-WP11-ENGINEERING-STATUS-20261031.md.

### Issue #4 — 2026-10-31: Evidence-bound LCR end-to-end engineering
- Full 13-file governed WP1 DQ and WP2 effective date akad + factor snapshot to pure WP4 LCR; no regulatory coefficients hardcoded.
- Bank-declared GL scope/sign and tolerance; source-to-GL/classifier gross reconciliation with persistent exception cases.
- Immutable input/parameter/source/mapping/DQ/recon proof bound to WP3 LCR CalculationRun, PostgreSQL migration 0003 plus legacy boolean bypass prevention and synthetic tests.
- Reporting/model/adjusted-unwind/SSO/production gate remain HOLD pending regulator annex detail and Bank sign-off.

### POJK 20/2025 Annex I regulatory gap review — 2026-10-31
- Added source-anchored LCR control matrix for 20 categories and explicit Bank evidence HOLD.
- Replaced simplified HQLA cap allocation with exact Annex I III.C two-deduction calculation (no unwind path), 15/85, 15/60 and 2/3 ratios using Decimal.
- Enforce official HQLA cap factors 40% and 15%, L1/L2A haircut arithmetic; SFT unwind continues to fail closed until approved transaction ledger.
- Added isolated real PostgreSQL 16 CI smoke, synthetic negative tests, independent validation/parallel-run framework. Bank PostgreSQL/working papers/signoff NOT available.

### SFT short-term unwind + LCR differential testing (31 Oct 2026)
- Added Bank-evidence-gated SFT/repo/collateral exchange ledger with strict 30-day matured-settled tests, post-haircut adjustment, collateral double-count controls and hash/source-bound proof.
- Added append-only SFT run ledger and Alembic migration 0004 with PG/SQLite guards, maker/checker immutable verification and actual ephemeral PG smoke.
- Added differential comparison against separately approved, date/currency-matched LCR paper with all mandatory summary measures and rule category amounts; synthetic golden tests and Bank UAT secure CLI.
- No actual Bank working papers, collateral custody/GL secured funding reconciliation, independent Bank signatures, daily quarter parallel run or production approval; regulatory release HOLD.
