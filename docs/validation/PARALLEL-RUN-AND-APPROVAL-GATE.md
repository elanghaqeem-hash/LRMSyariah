# Bank-controlled real-data validation, 1-quarter parallel run and approvals

Project: KB Bank Syariah · LRMSyariah · opened 31 October 2026. STATUS: NOT STARTED with real Bank data.

## Secure evidence prerequisites

**Never place bank working papers, GL extracts, customer identifiers, contract inventories, approval files, signatures or confidential architecture into public GitHub.** Upload these to the Bank's restricted data room with vault references and SHA-256 only in issue comments. Obtain the approved report position dates, governed rates, FX source, maker/checker principals and segregation of duties.

## Daily parallel-run protocol

- Proposed 1 consecutive reporting quarter **after** source/parameter/IdP availability; do not backfill synthetic dates to imply historical operation.
- Each reporting date record: `reporting_date`, `bank_working_paper_ref`, `bank_sha256`, `engine_commit_sha`, `engine_parameter_revision`, `akad_revision`, `source_batch_hash`, `bank_hqla`, `engine_hqla`, `bank_outflows`, `engine_outflows`, `bank_inflows`, `engine_inflows`, `bank_nco`, `engine_nco`, `bank_lcr`, `engine_lcr`, `delta_amount`, `delta_ratio_pp`, `reconciliation_status`, `exception_ref`, `correction_ref`, `maker_ref`, `checker_ref`, `risk_acceptance_ref`.
- Controls: immutable daily snapshot, data completeness, source extract lineage, independent GL reconciliation, date matching, factor effective dating, trace to ledger and source source agreements.
- Root cause any difference, do not automatically assume approved tolerance. Bank signoff sets **materiality and precision**; zero unexplained P0 variances; rerun corrected version through supersession with unmodified historical run.
- Weekly independent review of exception register; at end of quarter reconcile each official workpaper by category and sign against signed GL scope.

## Independent model validation

1. Validator confirms **independence from calculation author, maker, checker and deployer**.
2. Compare detailed POJK Lampiran I rule ID and classification, local circulars/FAQ, SFT/unwind evidence, eligibility/haircut and official disclosure.
3. Challenge SFT tenor boundary day 30/31; zero/negative/large denomination; 2B first/second cap, multi-currency, collateral double counting, pledged deposits, DCR retail categories, performing finance, GL sign.
4. Execute Bank golden dataset reconciliation and daily quarter holdout, record findings and remediation evidence.
5. Approve/reject by documented signed letter/e-signature; a CI green badge cannot substitute for this.

## Signoff matrix (to be completed by authorised Bank staff)

| Authority | Required written decision | Current | Evidence ref |
|---|---|---|---|
| SKMR / CRO delegate | Methodology, risk thresholds, model validation results, parallel-run variance acceptance | PENDING | — |
| Finance / CFO delegate | Ledger/GL, sign/valuation basis, data reconciliation, daily and quarterly accounting reconciliation | PENDING | — |
| Dewan Pengawas Syariah / Syariah Compliance | Contractual akad, DCR/PER, SFT and LCR Sharia mapping | PENDING | — |
| IT / InfoSec / CISO delegate | PostgreSQL actual Bank environment, SSO, tenant isolation if relevant, secrets, backups, DR, IT security | PENDING | — |
| Model Validation independent | Challenge testing, methods, OJK rule coverage and Bank reference calculations | PENDING | — |
| Change Advisory / Production Owner | Business go/no-go and cutover record | PENDING | — |

**Release gate:** Official OJK reporting and Bank production must remain HOLD until these checks and approvals are evidenced and approved. No self-certification by development team.