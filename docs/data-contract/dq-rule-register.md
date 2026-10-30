# DQ rule registry (WP1)

Python source of truth: `src/lrm_data/dq.py`. Rules below are engineering controls; **not parameter factors or substitutes for Bank-approved quality thresholds**.

| ID | Severity | Owner | Requirement |
|---|---|---|---|
| DQ-FILE-001 | FAILED | IT/Data Owner | Safe `.xlsx` only; bounded archive, no formula/hidden/external link |
| DQ-SCHEMA-001 | FAILED | Data Owner | Complete versioned metadata, matching header and mandatory sources |
| DQ-VAL-001 | FAILED | Data Owner | Exact typed row, no float, range correctness, masked identifiers |
| DQ-DATE-001 | FAILED | SKMR | Consistent reporting date |
| DQ-CURRENCY-001 | FAILED | Treasury | Single approved reporting currency; no implicit FX conversion |
| DQ-DUP-001 | FAILED | Data Owner | No duplicate dataset/business key |
| DQ-REF-001 | FAILED | Finance | On-balance source GL key exists in NeracaHarian |
| DQ-MATURITY-001 | FAILED | SKMR | Invalid placement/deposit or reference maturity/effective date |
| DQ-AKAD-001 | FAILED | Sharia Compliance | Missing/unknown/unapproved akad |
| DQ-AKAD-002 | WARNING | Sharia Compliance | Regulatory product-to-akad mapping pending WP2; blocks calculation |
| DQ-AKAD-003 | FAILED | Sharia Compliance | Conflicting akad for one product_code across sources |
| DQ-MATURITY-002 | WARNING | SKMR | Overdue financing or payment schedule requiring review |
| DQ-SCOPE-001 | WARNING | Data Owner | Bank has not defined mandatory source set for run type |

`WARNING` must be explained/reviewed by Bank; it is not auto-approved. The bank's warning ownership and control escalation matrix remain `[VERIFY]` at mobilization.
| DQ-AKAD-004 | FAILED | Sharia Compliance | Missing, expired or mismatched approved WP2 mapping for an akad-bearing record |
| DQ-PARAM-001 | FAILED | SKMR | No explicit nonempty mandatory parameter set, or an unapproved/missing effective parameter |

**WP2 gateway:** `lrm_services.akad_gateway.validate_batch_with_mapping` replaces
`DQ-AKAD-002` warnings with a mapping result only after checking every akad-bearing
row against effective, checker-approved mappings. Unmapped rows trigger FAILED
`DQ-AKAD-004`. Independently, a missing Bank-approved list of mandatory parameter
IDs (or any missing ACTIVE parameter) triggers FAILED `DQ-PARAM-001`. The gateway
returns safe row-level mapping traces (rule ID, version, input SHA-256), never
customer identifiers. A PASS is **DQ-only**, not LCR/NSFR methodology certification.
