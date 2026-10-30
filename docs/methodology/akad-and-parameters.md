# WP2 methodology — Akad and regulatory parameter governance

Scope **R02, R06, R12** and `DQ-AKAD-002/004`, `DQ-PARAM-001`. These are
**governance controls**, not OJK calculation formulas, and do not claim
compliance with the annexes of POJK 20/2025.

## Status and lifecycle

`DRAFT_UNVERIFIED` (created by MAKER) → `PENDING` (submitted by same MAKER)
→ `ACTIVE` (approved by distinct CHECKER with evidence). A checker may reject
`PENDING` to `DRAFT_UNVERIFIED` with a mandatory reason. `ACTIVE` rows cannot be
modified or deleted. Retirement is a separate MAKER + CHECKER-approved `RETIRED`
tombstone, which prevents older versions from silently becoming current.
Administrator, Auditor and ALCO cannot draft, submit or approve; they have no
write privileges at the service-layer boundary. Distinct checker ID is checked
both in service and DB schema/trigger. Bank-approved identity enrolment and OIDC
mapping are WP6.

## Version and effective date semantics

`(kind, item_key, version)` is unique; approved revisions with the same
`effective_from` are forbidden. The latest approved `effective_from` not later
than report date determines the applicable version. If that version is expired
or retired, no older revision is used. Later approvals starting on/before the
latest approved start are rejected (no retroactive rewriting). A calculated
report must pin exact source versions and hashes, added in WP3.

## Parameter governance

`value` is a finite canonical decimal string (`float` forbidden). `unit`,
`effective_from/to`, `legal_basis` and change reason are required. There is NO
preloaded regulatory factor. The checker must provide a 64-char hex SHA-256
fingerprint of the verified source document and concrete verification reference.
Software confirms format and independent attestation only; **Bank personnel must
actually compare the official rule and evidence outside this prototype**.
`parameter_snapshot` returns the exact required version set and deterministic
SHA-256 fingerprint. Missing required parameters fail closed.

## Akad classification

Each mapping identifies `(dataset_type, source_key)` and defines one Bank-approved
`akad`, balance side, LCR category, NSFR category, rule ID and effective dates.
The product/akad code and category are not inferred by the software. The
checker records the Bank-approved Sharia Compliance/DPS review reference.
`src/lrm_engine/akad/classifier.py` is pure and returns `(category, rule_id,
version)` on an exact match. A dataset is blocked if even one akad-bearing
record is unmapped or mismatched.

`PenempatanBankLain` and `KewajibanAntarBank` currently use `counterparty_code`
as classification key, pending Bank confirmation that a different tenor/akad/
segment dimension is required. No transaction amounts/customer identifiers
appear in mapping traces.

## Limits

No regulatory mapping/parameter is verified by RiseTIn in this development
package; synthetic approval test fixtures are explicitly NOT PROD authorizations.
No Bank IdP, PostgreSQL runtime, tamper-evident audit, calculation-run approval,
LCR engine, NSFR engine, API, UI, or production deployment exists here.
