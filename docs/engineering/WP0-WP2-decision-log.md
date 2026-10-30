# Decision Log (ADR)

| ID | Date | Decision | Rationale | Status |
|---|---|---|---|---|
| ADR-0001 | 2026-10-30 | Engine is pure Python, importing no UI, DB or I/O framework | Traceable, testable and reproducible calculation | ACCEPTED for WP0 |
| ADR-0002 | 2026-10-30 | Only `Decimal`/canonical decimal strings accepted for money and factors; float rejected | Prevent precision drift | ACCEPTED for WP0 |
| ADR-0003 | 2026-10-30 | No regulatory factor or threshold loaded in WP0 | Official appendix and Bank approval pending | ACCEPTED |
| ADR-0004 | 2026-10-30 | Immutable approved result modeled later as immutable snapshot + separate supersession link/event | Avoid contradiction between APPROVED immutability and changing status to SUPERSEDED | PROPOSED WP3 |
| ADR-0005 | 2026-10-30 | Treat Bank Banten conventional proposal as prior context only, not a sharia regulatory baseline | Different regulatory basis | ACCEPTED |
| ADR-0006 | 2026-10-30 | Intraday ILAAP reporting requirements to be assessed during mobilization; do not assume Phase 2 excludes compliance | SEOJK 26/2025 includes intraday liquidity report | OPEN [VERIFY] |
| ADR-0007 | 2026-10-30 | Use full schema versioned file contract in WP1; do not hard-code bank field positions | Phase 2 data-warehouse reuse | IMPLEMENTED WP1 (Bank signoff pending) |
| ADR-0008 | 2026-10-30 | Use environment-injected semver + full git SHA in engine identity, never a guessed commit hash | Audit trail and source reproducibility | ACCEPTED |
| ADR-0009 | 2026-10-30 | No GitHub repository/deployment changes in WP0 package delivery | No confirmed project repository/production destination | OPEN |

| ADR-0010 | 2026-10-30 | WP1 requires exactly two visible `.xlsx` worksheets (`__meta__`, `data`), a 1.0 metadata version and strict canonical headers | Deterministic source provenance; forbid silent source mapping | ACCEPTED (provisional Bank contract) |
| ADR-0011 | 2026-10-30 | All record types contain an explicit source currency; batch must reconcile row/source/reporting currency; no FX conversion in WP1 | No unverified FX conversion or cross-currency ratios | ACCEPTED |
| ADR-0012 | 2026-10-30 | Known akad vocabulary is provisional; no regulator-approved product mapping until WP2. Missing approval warns DQ-AKAD-002 but blocks calculation and approval | Regulatory rule cannot be silently inferred from product or Bank prior templates | ACCEPTED |
| ADR-0013 | 2026-10-30 | GL anchor/source and capital/reference-only rows are not forced to invent a commercial akad; every engine-eligible balance/cashflow row requires explicit akad | Faithfully model source roles and keep future engine boundary clear | ACCEPTED; Bank signoff pending |
| ADR-0014 | 2026-10-30 | Excel file formula, macro, hidden row/column and external link prohibited; bounded parsing limits are provisional | Reduce unsafe upload surface and hidden calculations; require load testing | ACCEPTED; adjust after Bank volume signoff |
| ADR-0015 | 2026-10-30 | DQ error messages contain only source hash, dataset, field, rule and Excel row, not source values | Minimize disclosure in logs and exception reports | ACCEPTED |
| ADR-0016 | 2026-10-30 | GL cross-reference check verifies code existence only; amount reconciliation and sign conventions deferred to WP5 | Prevent false claim of financial reconciled source | ACCEPTED |
| ADR-0017 | 2026-10-30 | Store source extraction timestamp with offset and reporting date separately; intraday transaction source fields require future extension | Avoid confusing daily position with transaction-time measurement | ACCEPTED |
| ADR-0018 | 2026-10-30 | Four-eyed waiver/approval is NOT simulated in WP1; only WP2 Bank-verified effective mapping can resolve DQ-AKAD-002 | Enforce fail-closed and preserve governance distinction | ACCEPTED |

## Unknowns before deployment

Exact KB Syariah source proposal dated 29 Oct 2026 not provided; current bank
working papers, input volumes, IdP claims, report templates, approved tolerance,
and official clause-level parameter verification are pending.

### WP1 open Bank/Regulator verification items

- `[VERIFY-BANK-DATA-001]`: actual core banking, Treasury, and GL file layout and field mapping to schema 1.0, including installment schedule format and late/overdue exception handling.
- `[VERIFY-BANK-DATA-002]`: approved akad vocabulary/product mapping, segmentation, masked-ID/token method and syariah review reference (DPS/Kepatuhan Syariah).
- `[VERIFY-BANK-DATA-003]`: FX conversion basis/cut-off, precision, allowed currencies and source system; WP1 intentionally supports matching currencies only.
- `[VERIFY-BANK-DATA-004]`: per-run mandatory source file set, batch cut-off, duplicate key policy and signed GL sign conventions/tolerances.
- `[VERIFY-BANK-DATA-005]`: input volume and throughput, max workbook sizes, retention, and secured deployment environment.
- `[VERIFY-REG-001]`: current OJK/BI official appendix for HQLA GWM/PLM, eligible instruments, haircut and NSFR ASF/RSF; no value activated.
- `[VERIFY-REG-002]`: recognized ratings, LPS stability and product-specific early withdrawal/funding treatment, and whether new fields are needed in schema contract.
- `[VERIFY-BANK-GROUP-001]`: parent consolidation output file/data basis, not addressed until WP7.

### WP2 decisions — 30 October 2026

| ID | Decision | Reason / gate |
|---|---|---|
| ADR-0019 | Governance revisions for PARAMETER and MAPPING use one versioned effective-dated PostgreSQL register | One controlled maker–checker lifecycle and replayable historical definitions; WP3 adds immutable calculation-run snapshots |
| ADR-0020 | The highest approved `effective_from` at or before the reporting date wins; an expired newer revision does not reactivate an older one | Deterministic temporal semantics, no silent fallback; later backdated approval forbidden |
| ADR-0021 | Approved ACTIVE and RETIRED revisions cannot be edited/deleted; retirement is an independently approved tombstone | Preserve historical reports and reviewer trace; DB trigger and service control |
| ADR-0022 | Parameter approval requires independent CHECKER attestation of document hash + exact legal reference; mapping approval requires Sharia/DPS review reference | Prevent DRAFT_UNVERIFIED reaching ACTIVE without recorded Bank governance; source existence/accuracy still must be validated by Bank |
| ADR-0023 | Do not use the existing WP1 mapping warning as an approval bypass; instead require a fully approved mapping for every akad-bearing row | No partial coverage: mapping miss is DQ FAILED; no inferred regulatory category |
| ADR-0024 | A nonempty Bank-defined list of approved effective regulatory parameters is additionally necessary before DQ gate opens | Prevent mapping-only PASS from being confused with calculation eligibility |
| ADR-0025 | Known classifier fields for non-product sources (e.g. counterparty type/code and instrument type) are provisional; Bank must approve source key schema | Current contract may be too granular and may omit attributes required by OJK |
| ADR-0026 | Phase 1 service uses registered principal roles; transactional PostgreSQL trigger checks authenticated application context; direct IdP integration is deferred to WP6 | WP2 not production-secure standalone: no OIDC trust boundary, provisioning or comprehensive access controls yet |
| ADR-0027 | Seed file remains empty for akad mapping and null-valued DRAFT_UNVERIFIED for regulatory factors | Do not import conventional Bank Banten rules or fabricate KB Syariah parameter values |
| ADR-0028 | Local SQLite integration tests and offline PostgreSQL migration SQL generation prove neither actual PostgreSQL execution nor end-to-end security | Must run migration/rollback, role SoD and concurrency tests on real PostgreSQL UAT before signoff |
