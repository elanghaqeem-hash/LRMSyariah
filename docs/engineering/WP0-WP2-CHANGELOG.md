# Changelog

All dates local to Indonesia (WIB). Regulatory interpretation and Bank data mapping remain subject to verification.

## 0.3.0 — 2026-10-30 — WP2 (Local engineering)

### Implemented
- SQLAlchemy 2 governance registry with principal roles, revisioned parameter and akad mapping objects, effective dates and immutable approved versions.
- Service workflow for MAKER submission, independent CHECKER approval/rejection, and approved retirement tombstones; version snapshot SHA-256 for regulatory parameters.
- PostgreSQL Alembic migration with SoD CHECK, unique active start dates, immutable approved rows and transaction-local checker-role trigger; offline SQL compilation validated.
- Pure-engine bank-provided akad classifier and WP1 integration gateway requiring complete mapping AND approved mandatory parameters before DQ PASS.
- Explicit synthetic-only approval tests; 16 WP2 integration cases (113 total local tests). Updated methodology, RTM, ADR and regulated parameter guard.

### Not yet proven / open
- Regulatory factor and DPS mapping content is NOT validated; no active regulatory values or mappings are shipped.
- SQLite tests and offline PostgreSQL DDL generation do NOT establish PostgreSQL UAT, production SSO, controlled DB privileges, concurrent approvals or CI/security-scan success.
- WP3 calculation run archives and hash-chain audit remain unimplemented.

## 0.2.0 — 2026-10-30 — WP1 (Local engineering)

### Added
- 13 typed bank-syariah datasets in `lrm_data/schema.py`, strict row-level currency and masked customer identifiers; `decimal.Decimal` exact-money validation and installment JSON parsing.
- ISO effective date, extraction timestamp, source provenance and schema 1.0 file metadata.
- `.xlsx` loader with limits and rejection of formulas, hidden rows/sheets, macros/external links, corrupt files, and unknown schema columns.
- DQ registry and deterministic batch findings for date/currency, duplicate key, GL existence, provisional akad, product-code consistency, and maturity.
- 13 Excel files of **synthetic** data, 14 exported JSON schemas, and CLI evidence generator.
- 57 WP1 unit/integration tests added (97 total including WP0 tests); reporting on exercised local runtime. Added WP1 SIT to CI workflow.
- Full documentation: source contract, DQ rule register, methodology, implementation decisions and RTM.

### Limitations (deliberate)
- Product-to-akad and regulatory-category mapping **not approved**: dataset emits DQ-AKAD-002, blocks calculation and submission.
- No Bank source-file actual mappings, no automatic FX conversions, no LCR/NSFR calculations or regulatory output.
- Dependency audit, SAST and CI on Python 3.12 not run in local environment; require GitHub CI execution.

## 0.1.0 — 2026-10-30 — WP0 (Local engineering)

- Established pure Python `lrm_engine` with exact Decimal, canonical data hashes, bucket/date primitives and declared engine build identity.
- Introduced unverified regulatory seed guard, CI foundation, docs, RTM and ADR.
- 40 WP0 tests passing locally; no approved LCR/NSFR/ILAAP parameters.
