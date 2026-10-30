# PostgreSQL governance migration (WP2)

`LRM_DATABASE_URL` must come from the Bank-approved secret channel; never place it
in a repository or CLI history. Apply only in DEV/UAT after DB backup and change
approval: `alembic upgrade head`. The first migration creates the two WP2 tables,
foreign keys, SoD CHECK constraints, effective-date indexes and native PostgreSQL
trigger preventing direct SQL UPDATE/DELETE of approved rows. It checks the
transaction-local `lrm.actor_id` against the registered CHECKER principal.

The Bank must restrict connection credentials and PostgreSQL table owner,
DDL, and privileged roles. `SET LOCAL` context alone is not cryptographic
identity assurance: WP6 must derive actor subjects from verified OIDC claims and
prevent end-user DB access. An internal application role with arbitrary SQL
access can attempt to forge session context, so independently restrict SQL
execution to the trusted service boundary. WP3 adds chain-hashed append-only
audit; do not claim WP2 alone provides immutable audit evidence.

SQLite is used only for local service-layer/unit tests and is **not a supported
production DB**. Native PostgreSQL migrations must be tested in Bank UAT.
