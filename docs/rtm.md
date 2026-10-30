# LRM Requirement Traceability Matrix (interim WP2)

**R01–R20** correspond to the 30 October 2026 master prompt. `Implemented WP1` below means validated source contract and DQ **only** — not regulatory formula/methodology compliance.

| Requirement | Target WP | Status at WP2 | Rule/code | Evidence |
|---|---|---|---|---|
| R01 LCR daily HQLA & NCO | 4 | NOT IMPLEMENTED | LCR/engine placeholder | WP4 tests pending |
| R02 Akad-first classification | 2 | IMPLEMENTED governance + pure classification, mapping data NOT Bank-approved | DQ-AKAD-001/002/003/004 | `test_wp2_governance.py` + SIT-DQ |
| R03 HQLA L2/L2B caps | 4 | NOT IMPLEMENTED | `[VERIFY]` official annex | WP4 golden pending |
| R04 Inflow cap | 4 | NOT IMPLEMENTED | `[VERIFY]` official annex | WP4 golden pending |
| R05 NSFR ASF/RSF | 8 | NOT IMPLEMENTED | NSFR/engine placeholder | WP8 golden pending |
| R06 Regulatory threshold phases | 2 | IMPLEMENTED parameter mechanism, regulatory thresholds still unverified/unseeded | Effective date lookup and null seed guard | `test_wp2_governance.py` |
| R07 Sharia stress scenario | 9 | NOT IMPLEMENTED | Stress placeholder | WP9 pending |
| R08 Survival period buckets | 9 | PARTIAL: generic time bucket primitive | WP0 time bucket helper | `test_time_buckets.py` |
| R09 DCR / rate gap | 10 | NOT IMPLEMENTED | DCR placeholder | WP10 pending |
| R10 Upload schema, akad and DQ | 1 | **IMPLEMENTED provisional** | Source models, loader, DQ rule registry | 57 WP1 tests, report JSON |
| R11 Detail/GL reconciliation | 5 | PARTIAL: GL key reference check ONLY | DQ-REF-001 | SIT-DQ GL reference |
| R12 Maker–checker | 2 | IMPLEMENTED service+DB constraints/migration; PostgreSQL live test pending | WP2 status transition + four-eyes | `test_wp2_governance.py` |
| R13 Append-only hash audit | 3 | NOT IMPLEMENTED | WP3 | tamper test pending |
| R14 SSO/OIDC/RBAC | 6 | NOT IMPLEMENTED | WP6 | SEC-AUTH pending |
| R15 Regulatory LCR/NSFR output | 7/8 | NOT IMPLEMENTED | WP7/8 | UAT-OUT pending |
| R16 Calculation run reproducibility | 3 | PARTIAL: canonical hash primitive | WP0 canonical SHA-256 | `test_canonical.py` |
| R17 Parent consolidation output | 7 | NOT IMPLEMENTED | WP7 | UAT-CONSOL pending |
| R18 Quarterly publication | 7 | NOT IMPLEMENTED | WP7 | UAT-PUB pending |
| R19 Masking/minimization | 1/12 | PARTIAL: masked ID input + sanitized error messages | DQ-VAL-001 | `test_wp1_schema.py`, `test_wp1_loader.py` |
| R20 Supply-chain/SBOM | 0/12 | CI configured; not independently run | WP0 CI | CI execution pending |

### Engineering requirements implemented

| Requirement | Evidence |
|---|---|
| Decoupled calculation engine from file parsing | `test_engine_imports.py` |
| Exact Decimal no binary floats | `test_decimal.py`, `test_wp1_schema.py`, `test_wp1_loader.py` |
| Versioned file metadata, 13 contracts | `test_wp1_loader.py` (parameterized) + 14 JSON schemas |
| Source SHA-256 and masked DQ findings | `test_wp1_loader.py` + `artifacts/wp1-dq-report.json` |
| Batch one date/currency and GL existence | `test_wp1_batch.py` |
| Regulatory mapping missing blocks workflow | `test_wp1_batch.py` (WARNING with calculation/submission blocked) |

**Regulatory LCR/NSFR rule coverage 100% is NOT claimed.** These mandatory
calculation rules do not exist in WP2. The governance integration tests are
synthetic and are not Bank approval or PostgreSQL deployment evidence.

### WP2 added trace cases

| Control | Source | Tests | Current status |
|---|---|---|---|
| GOV-APPROVE-001 | Maker–checker distinct role; PostgreSQL/SQLite SoD CHECK | `test_parameter_requires_independent_checker_evidence`, `test_db_check_constraint_maker_cannot_self_approve_even_via_sql` | LOCAL PASS; PostgreSQL UAT OPEN |
| GOV-REV-001 | Version + effective dating + no backdated rewrites | `test_latest_as_of_versions_and_retirement_tombstone`, `test_backdated_approved_revision_rejected` | LOCAL PASS |
| GOV-IMMUT-001 | Approved versions immutable, separate retirement tombstone | `test_approved_revisions_immutable_even_via_direct_sql` | LOCAL SQLite PASS; PostgreSQL UAT OPEN |
| GOV-EVIDENCE-001 | Regulatory source SHA/reference and Sharia review reference | `test_parameter_requires_independent_checker_evidence`, `test_mapping_requires_dps_evidence_and_match` | LOCAL PASS; verification by Bank OPEN |
| DQ-AKAD-004 | 100% mapped akad-bearing rows | `test_service_integration_mapping_coverage_all_synthetic_rows` | LOCAL synthetic PASS; Bank map OPEN |
| DQ-PARAM-001 | Approved mandatory parameter set exists | `test_parameter_snapshot_is_canonical_order_invariant` | LOCAL synthetic PASS; Bank mandatory param list OPEN |
