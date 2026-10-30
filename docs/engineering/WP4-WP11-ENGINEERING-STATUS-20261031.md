# LRM Syariah — engineering progress (WP4–WP11)

**Not a certificate of regulatory readiness.** All numbers in tests are synthetic;
mandatory factors are supplied externally and require live WP2 regulatory approval,
valid legal citations and Bank confirmation. This code does not silently imply
that a legal factor, maturity rule or sharia classification is correct.

| WP | Engineering code in this branch | Not yet complete — production blockers |
|---|---|---|
| WP4 LCR | Pure Decimal HQLA, Level 2/2B caps, outflow/inflow, cap, trace, golden/edge tests | Annex-level POJK 20/2025 validation; adjusted-unwind treatment; actual Bank category mapping and data ingest |
| WP5 Recon | Three-layer GL vs detail vs engine with policy tolerance and fail on missing GL/date | Persistent exceptions, reviewed variance, binding to WP3 evidence, parallel run |
| WP6 UI | NOT IMPLEMENTED | Streamlit thin UI, OIDC proxy, Bank role UAT |
| WP7 Outputs | Deterministic ZIP audit-evidence draft | Verified APOLO/publication templates, signed outputs and export log |
| WP8 NSFR | ASF/RSF pure parameterized calculator with akad/source trace | Full asset/maturity treatment, bank golden papers, multi-currency/encumbrance |
| WP9 Stress/survival | Bank scenario overlays and parameterized 19-bucket ladder | Multi-horizon full library, governance, reverse stress, ILAAP data acquisition |
| WP10 DCR | Deterministic rate gap, runoff and smoothing-cost arithmetic | DPS/PER policy, calibration, ALCO workflows |
| WP11 ILAAP | Pseudonymized concentration analytics | KBMI templates, intraday data, risk appetite narrative and governance |
| WP12 Infra | NOT IMPLEMENTED | TLS, IdP, PostgreSQL production roles, security, backup/restore, DR validation |
| WP13 Training | NOT IMPLEMENTED | training, handover, quarter parallel run, model validation |

## Prevent unsafe regulatory output

- HQLA Level2 uses L2A-first allocation when both composition caps bind;
  **not certified POJK/Bank treatment**. Adjusted-unwind transactions abort.
- Factor approval labels alone are **not proof** of WP2 database approval.
  Bind actual `GovernanceService.parameter_snapshot()` before production calculation.
- `reproduce` requires original binary/version and independently checked source.
- Audit pack excludes source files; the ZIP is not an OJK report or submission.
- Caller-supplied DQ/recon PASS booleans are insufficient WP5 evidence.

## Local verification

`PYTHONPATH=src:. pytest -q` — 160 synthetic tests passed, coverage 91.68%.
No live Bank PostgreSQL, IdP, APOLO, independent model validation or production deployment.