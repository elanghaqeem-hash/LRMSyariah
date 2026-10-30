# KB Bank Syariah — Liquidity Risk Management (WP0 + WP1 + WP2)

**Version:** `0.3.0` · **Date:** 30 October 2026 · **Owner:** RiseTIn engineering work package

**Engineering prototype only — NOT a production regulatory calculation system.** This package implements **WP0** foundational engine controls, **WP1** source data contracts / Excel upload validation, and **WP2** maker–checker governed regulatory parameters / akad mappings. The WP2 work uses a local SQLite test double, PostgreSQL Alembic migration source and static SQL generation, NOT a verified PostgreSQL deployment. It **does not** calculate, report, publish, approve, or certify LCR, NSFR, ILAAP, stress testing, survival period or DCR. All regulatory factors and Bank-specific akad mappings remain unapproved. Do not use it for an official Bank calculation/report.

## Completed work packages

| WP | Status | Deliverables |
|---|---|---|
| WP0 | Implemented locally | Pure `lrm_engine`, Decimal/canonical hash primitives, engine identity, seed guard, CI skeleton, ADR |
| WP1 | Implemented locally | 13 Pydantic source contracts, 14 JSON Schema exports, Excel loader, batch DQ, exception findings, synthetic `.xlsx` set, SIT-DQ |
| WP2 | Implemented locally, Bank approval pending | Parameter/mapping revisions, dates, SoD, DB constraints, PostgreSQL trigger migration, mapping DQ gateway, 16 tests |
| WP3–13 | Not implemented | Append-only hash audit, immutable calculation runs, LCR/NSFR/ILAAP, UI, security/deployment |

## Local development

Requires **Python >= 3.12** (local verification used Python 3.13.5) and environment-local packages. No network calls are performed by the application code.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'

# Generate 14 JSON Schema reference files and 13 purely synthetic Excel samples
python scripts/export_contract.py
python scripts/generate_synthetic_inputs.py

# Run input validation and print DQ-only summary
python scripts/validate_synthetic.py

# Quality tests, including the original 40 WP0 tests
pytest -q
pytest tests -q --cov=lrm_engine --cov=lrm_data --cov-branch --cov-report=term-missing
python scripts/check_regulatory_seeds.py
# Compile PostgreSQL migration SQL without opening a database connection
LRM_DATABASE_URL='postgresql+psycopg://offline:offline@localhost/lrm' alembic upgrade head --sql
mypy --strict src/lrm_engine
ruff check .
```

**PostgreSQL (Bank DEV/UAT only):** configure `LRM_DATABASE_URL` via the
Bank secret manager and run `alembic upgrade head` after database backup, change
control and DB role hardening. This was NOT executed in the local test
session. See `migrations/README.md`.

For environments without package installation, run examples with `PYTHONPATH=src:.` from repository root. CI also runs Bandit, pip-audit and CycloneDX after dependencies are available.

**Expected standalone WP1 synthetic report (without WP2 mappings):** status `WARNING`, 13 files, zero `FAILED` findings, 9 mapping warnings (`DQ-AKAD-002`), `calculation_allowed=false`, `submission_allowed=false`. This warning state is **intentional and mandatory**, not a failed code test. The report is saved to `artifacts/wp1-dq-report.json` and has only source hashes, rule IDs and non-sensitive messages.

## Source contract and DQ model

- Data schema: `src/lrm_data/schema.py`; documentation `docs/data-contract/README.md`.
- Excel parser: `src/lrm_data/loader.py`; accepts only safe, bounded `.xlsx` source bytes.
- Data quality: `src/lrm_data/dq.py` and `src/lrm_data/validation.py`, with rule register `docs/data-contract/dq-rule-register.md`.
- Every input contains an effective reporting date, source ID, version, source extraction timestamp, reporting currency and row-level currency.
- Currency mismatch / unmasked account identifier / unknown akad / conflicting product akad / missing GL anchor / invalid record aborts calculation.
- **Akad regulatory mapping is not approved for KB Bank Syariah**. WP2 implements
  maker–checker versioning and evidence gates but ships NO active mapping. WP1
  remains blocked until real Bank approval; synthetic test approvals are not
  regulatory authorizations. `DQ-AKAD-004` fails missing or mismatched mapping.
- WP2 further requires an explicit nonempty mandatory active regulatory parameter
  set (`DQ-PARAM-001`) even after every source record is mapped.
- The only Bank data contract that WP1 knows is the **provisional** schema proposed in the 30 October 2026 brief, not the Bank's actual extraction layout.

## Design protections

1. `lrm_engine` has no UI/DB/network imports; Python `Decimal` is used for all money and factors, no float coercion.
2. Regulatory seeds remain `DRAFT_UNVERIFIED`, with no approved live parameters.
3. Source files are **never uploaded off device/network** by application code. Inputs are processed locally; the demo only reads bundled synthetic XLSX.
4. Exception findings omit values/PII. Customer/facility IDs must already be source-masked. Bank-specific data ownership, source controls and operational DLP remain outstanding.
5. No real Bank data, customer data, credentials, or production values belong in the repository.
6. File hashes provide evidence linking raw upload bytes to DQ findings. Trusted archival, append-only audit, approved immutable calculation runs and `reproduce(run_id)` are **WP3**, not WP1.
7. File/source data is **not** reconciled by amount in WP1. WP5 is the three-layer reconciliation work package.

## Mandatory release gates

Before use on Bank data: Bank-confirmed product codebook, akad mapping and DPS reference; real GL data/layout; approved extraction and conversion policy; requested file set and cut-off; input volume; regulatory text/appendix verification; privacy approval; WP2–WP13; UAT, model validation, parallel run and formal change authorization.

`docs/verify-regulations.md` tracks `[VERIFY]` issues. WP2 implements the
mechanism for evidence attestation, not verification of regulatory content. Earlier RiseTIn proposals for Bank Banten conventional banking are background only; sharia classification rules and rates are **not imported from those artifacts**.

## WP2 usage and limits

Core modules:

- `src/lrm_services/models.py`: PostgreSQL-targeted principal and revision ORM;
  service+DB CHECK constraints enforce checker != maker; approved rows immutable.
- `src/lrm_services/governance.py`: MAKER draft / submit; CHECKER reject / approve;
  effective-date lookup, retirement tombstone and parameter snapshot hash.
- `src/lrm_engine/akad/classifier.py`: pure DB-free akad resolution.
- `src/lrm_services/akad_gateway.py`: WP1+WP2 integration, effective mapping
  coverage and mandatory parameter gate.
- `migrations/versions/0001_wp2_governance.py`: Alembic PG schema and
  direct-SQL SoD/immutability trigger. **No PG runtime test has been run**.
- `docs/methodology/akad-and-parameters.md` and `docs/test-evidence-wp2.md`.

**All test users, category codes and approval evidence are synthetic.** Creating
Bank-approved parameter values and actual product mapping requires official
regulation/source review plus Bank/DPS signoff. The service constructor currently
accepts an actor subject ID for testing; it is NOT connected to authenticated
Bank OIDC/SSO claims. Do not expose to production or a public API until WP6
completes an identity trust boundary. WP3 still must implement append-only hash
chain audit, calculation-run snapshots and reproduction.

## Next

**WP3 — Append-only audit log, Calculation Run state machine, immutable approved
run snapshots and reproducibility.** Deploy only after Bank security and model
risk governance review, real PostgreSQL integration and UAT.
