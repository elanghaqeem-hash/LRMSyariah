# PostgreSQL actual-database test plan — isolated synthetic and Bank UAT

The GitHub CI can run a real **ephemeral PostgreSQL 16 container** with completely synthetic principals. This validates actual PostgreSQL engine transactions, migration and triggers, **not the Bank DB or its security boundary**. The Bank on-premise UAT must repeat using Bank-controlled, non-owner restricted application roles.

## CI job

- Start PostgreSQL 16 service container, a throwaway database and test credentials with no bank data.
- `pip install -e '.[dev]' 'psycopg[binary]>=3.2,<4'`.
- `LRM_DATABASE_URL='postgresql+psycopg://lrm_ci:lrm_ci@localhost:5432/lrm_ci' alembic upgrade head` and repeat to confirm idempotence.
- Run `scripts/postgresql_smoke_test.py`, negative direct DML actor, run lifecycle, immutable approved run, audit event UPDATE/DELETE, ledger hash.
- For failures, block source merge; never equate isolated CI success to on-prem validation.

## Bank-controlled acceptance

1. Validate DB identity and isolation from production; obtain change ticket; encrypted pre-migration `pg_dump` + SHA-256 and restore-test in isolated DB.
2. Run Alembic 0001–0003 on authorised UAT role, check revision checksum/constraints/index/trigger inventory. No destructive schema rollback.
3. Test two independent database user logins (service writer with limited grants; read-only auditor), maker/checker through Bank IdP; session expiration and revocation, cross-role and SQL injection checks.
4. Inject two concurrent approvals for one revision and two simultaneous ledger inserts; verify serialisation, append-only, whole-chain integrity and IdP actor cannot impersonate another.
5. Validate immutable approved records with raw UPDATE/DELETE by **restricted** application role; verify audit DB owner and superuser access monitored separately. Test encrypted snapshot retrieval and backups/restores.
6. Complete signed performance/load target, RPO/RTO and DR evidence; compare row counts, event chain and run hash before/after restoration.

**Current Bank environment access:** no Bank VPN/DB DSN, credentials, external vault, or IdP connected. Any claim of Bank PostgreSQL UAT success is prohibited until actual logs and acceptance are captured.