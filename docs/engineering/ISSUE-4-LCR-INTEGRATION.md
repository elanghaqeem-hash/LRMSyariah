# Issue #4 — End-to-end evidence-bound LCR engineering implementation

Status: **ENGINEERING IMPLEMENTED / REGULATORY RELEASE BLOCKED**.

## Integration flow

1. Read **all 13** strict WP1 `.xlsx` datasets at one position date/currency. DQ must be `PASS` (not WARNING), and all required source metadata, keys, AKAD, GL references and row validation checks must pass.
2. Resolve **effective, ACTIVE** WP2 akad mapping for every akad-bearing record. Mapping `lcr_category` is an explicitly bank-approved configuration, not an inferred category. Examples of the **technical encoding**, not recommended regulatory classifications: `HQLA:L1:<factor_id>`, `HQLA:L2A:<factor_id>`, `HQLA:L2B:<factor_id>`, `OUTFLOW:<factor_id>`, `INFLOW:<factor_id>`, `EXCLUDE`.
3. Resolve HQLA haircut, outflow, inflow and three cap parameters **from WP2 ACTIVE versions**, with actual verification metadata and a date-effective fingerprint. No regulatory values are populated by code. Cross-validate Bank-approved category against source type, use contractual maturity and 30-day financing instalments for candidate cashflows; disallow encumbered HQLA.
4. Compare raw detail **position gross amount** (not weighted cash flow) and engineering classification gross against GL anchor for every GL expressly listed in the Bank-approved scope. GL signs (+/-), accounting carrying-vs-market basis, scope SHA and zero/positive tolerances are explicitly supplied. GL items outside this approved LCR scope are reported as out-of-scope; **not** silently reconciled. The engineering gross comparison is not an independent valuation of cash flows.
5. Persist immutable 13-source hashes, DQ counts/status, GL-by-GL variances, snapshot version hashes, mapping revision IDs and signed scope references. An append-only ledger event anchors evidence to the WP3 run. No customer IDs or raw XLSX are written in evidence.
6. WP3 `validate()` and `approve()` for LCR **both demand matching immutable evidence**; booleans are insufficient. Reproduce with the same semver+git SHA by reconstructing the pure WP4 LCR calculator from the frozen gross/flow leg and factor snapshots.
7. A failed GL variance creates `lrm_lcr_recon_case` (OPEN); independent CHECKER may record review explanation (REVIEWED), but **cannot** override a failed report to PASS. Correction requires a new run and source, not an edit of approved evidence.

## Bank-specific acceptance conditions remaining

- **[VERIFY]** Bank-signed GL scope/sign, accounting carrying vs mark-to-market treatment, balance-side and FX conventions. Synthetically approved strings used in tests are **not** Bank or DPS approval evidence. External scope refs currently validated structurally; Bank identity/digital-signature validation must be bound to real OIDC/Document Vault.
- **[VERIFY]** Official Annex of POJK 20/2025, BUS-specific HQLA eligibility/haircut and unwind, exact 30-day contractual behavior, limit formula and exception categories. Adjusted unwind is **fail closed** until verified.
- **[VERIFY]** Actual source files stored in Bank-protected vault, hash and extract provenance validated, trusted Python service role and PostgreSQL restricted credentials. `lrm.actor_id` is trusted only under restricted app role.
- No independent Bank approved LCR working paper/golden sample, no one-quarter daily parallel run, and no SKMR/Finance/DPS independent model sign-off.
- No production PostgreSQL migration/UAT, no concurrency/SSO, no APOLO/publication official output, no approved RPO/RTO backup and restore.

The SQL migration explicitly disallows UPDATE/DELETE of evidence, enforces maker-owned draft insert, protects LCR transitions in the DB, and makes reviewed exceptions immutable. Existing generic WP3 governance tests use STRESS (their intent is transition/audit testing); dedicated LCR tests verify proof requirements, mismatch, expiry and failed reconciliation.

Regulatory reference for legal review: https://ojk.go.id/id/regulasi/Pages/POJK-20-Tahun-2025-Kewajiban-Pemenuhan-Rasio-Kecukupan-Likuiditas-dan-Rasio-Pendanaan-Stabil-Bersih-Bagi-BUS-UUS.aspx

No Bank production release or regulatory report is authorized by engineering CI success.