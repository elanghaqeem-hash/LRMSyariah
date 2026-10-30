# WP2 engineering test evidence — 30 October 2026

**Executed:** `PYTHONPATH=src:. pytest -q` — **113 passed**, including the
previous 97 WP0/WP1 tests and 16 new WP2 integration tests. Local environment:
Python 3.13.x, SQLAlchemy 2.0.50, Alembic 1.18.4, SQLite in-memory.

**Coverage test:** `pytest tests -q --cov=lrm_engine --cov=lrm_data --cov=lrm_services
--cov-branch --cov-report=term-missing` — approximately **92%** branch-aware
implementation coverage. The `lrm_engine` primitives remain fully covered.
This is NOT 100% regulatory-rule coverage; LCR/NSFR formulas are not built.

**Migration:** PostgreSQL offline DDL generated using
`LRM_DATABASE_URL='postgresql+psycopg://offline:offline@localhost/lrm'
alembic upgrade head --sql`. This checks generation only, **NOT** live database
execution, rollback or concurrency.

**Security-negative scenarios:** maker self-approval, non-checker approval,
admin/auditor/ALCO write attempt, disabled identity, activation without verified
source hash, missing syariah review, direct-SQL SoD CHECK, direct-SQL approved
revision update/delete, duplicate same-date approval, missing required parameter,
missing/mismatched akad mapping and retroactive active version.

**Functional tests:** draft → submit → reject → resubmit → approve; exact decimal
precision; historical-as-of lookup; expired version cannot silently fall back;
retirement tombstone; parameter-set hash stable regardless of requested key order;
13-file synthetic integration with all akad-bearing rows mapped. All Bank
classification categories and rule IDs in these approval tests are synthetic.

**Not executed:** PostgreSQL DB-native trigger integration with actual DB
privileges, OIDC/SSO, migration rollback on PostgreSQL, adversarial concurrency,
SAST/DAST and GitHub CI. They remain explicit gates for WP6/WP12 and Bank UAT.
