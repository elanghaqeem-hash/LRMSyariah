# Baseline audit — open technical deliverables (31 October 2026)

This file is a non-confidential engineering summary. Detailed bank proposal material is intentionally excluded from this PUBLIC GitHub repository.

## Current evidence

- WP0–WP2 local unit/integration suite: **113 passed** with `PYTHONPATH=src python -m pytest -q`.
- WP0: Decimal/canonical hash foundation, CI blueprint.
- WP1: 13 source contracts, 14 JSON Schema exports, XLSX loader, DQ, synthetic fixtures.
- WP2: governed parameter and akad mapping revisions, maker–checker workflow, Alembic PostgreSQL migration source.
- Local SQLite governance tests are NOT evidence of real PostgreSQL integration.
- No approved regulatory factor, active bank product mapping, live bank SSO or production data.

## Scope gaps before production

1. WP3 — append-only audit log, hash chain, immutable Calculation Run, bit-for-bit reproducibility.
2. WP4 — verified bank-syariah LCR HQLA/outflow/inflow/cap engine and independent golden tests.
3. WP5 — detail-to-GL-to-output reconciliation and exception workflow.
4. WP6–7 — UI, OIDC/RBAC and approval; daily/monthly and publication regulatory exports.
5. WP8 — NSFR ASF/RSF and regulatory workpapers.
6. WP9–11 — stress scenarios, 19-bucket survival, DCR and ILAAP support.
7. WP12–13 — security hardening, DEV/UAT/PROD, restore/rollback, model validation, training.
8. Bank-dependent gates — mapping/DPS sign-off, regulatory appendix confirmation, account cut-offs and tolerance, UAT, minimum one-quarter parallel run and production approval.

## Release decision

**HOLD / NO-GO** for official ratios or Bank production. This import is a code consolidation, not validation of compliance, model correctness or bank acceptance.
