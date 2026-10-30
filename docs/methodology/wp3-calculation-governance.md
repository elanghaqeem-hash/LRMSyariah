# WP3 — Calculation Run, immutable approval and audit ledger (R13/R16)

**Scope**: engineering control, not validated LCR/NSFR regulation. The executable
run lifecycle is DRAFT → VALIDATED → SUBMITTED → APPROVED or REJECTED. New corrected
runs point to an earlier APPROVED run by `supersedes_run_id`; old APPROVED rows
must never be rewritten. Unique predecessor links prevent double supersession.

## Cryptographic provenance and reproduction

- Canonical UTF-8 JSON (sorted keys; reject float, NaN, naive timestamp).
- `input_sha256`, `parameter_sha256`, `result_sha256` are SHA-256 of canonical blobs.
- `engine_version` is strict `semver+gitSHA`; mapping/parameter version labels are recorded.
- Only APPROVED runs can be reproduced with the **same exact engine binary/version**.
- `reproduce(run_id, calculator=..., engine_version=...)` reexecutes the supplied
  deterministic calculator against immutable source/parameter snapshot; verifies
  input/parameter hash and compares freshly calculated output SHA-256.
- Required: independently validated calculator, verified WP2 active parameter
  versions, complete input-file manifest (filename, size, uploader, SHA), genuine
  DQ/recon evidence and storage/retention controls **before Bank production**.
- Current `dq_passed` / `reconciliation_passed` inputs are trusted service calls,
  not a fully integrated DQ/recon evidence repository (WP5 pending).

## Ledger assurance

Event sequence starts at 1. Each event binds sequence, UTC ISO timestamp, actor,
event type, object ID, sanitized metadata and prior event SHA; first `previous_hash`
is 64 zeros. `verify_ledger(session)` detects sequence/hash mismatch. Database
triggers prohibit UPDATE/DELETE, but DB owner/superuser could override them.
Use restricted roles without schema owner/TRUNCATE/DDL privileges, mandatory
SIEM forwarding, externally anchored periodic tip hashes and tested restore.

The PostgreSQL trigger requires transaction-local `lrm.actor_id`; **only the
trusted service sets this from verified IdP claims** (WP6). Never expose DB role
or session parameter setting to end users. SQLite is testing only. PostgreSQL
migration `0002_wp3` requires independent test of direct SQL denial, concurrency,
backup/restore and failover. No rollback/downgrade destroys audit events.

## Open release gates

1. [VERIFY] official factor/methodology trace, production effective-dated snapshot.
2. WP5 evidence-referenced DQ and GL reconciliation; no caller-supplied PASS.
3. WP6 verified OIDC subject and per-request transaction isolation.
4. Tested PostgreSQL migration, change record and DBA sign-off.
5. WORM/external hash-chain tip anchor; backup and restore test evidence.
6. Production-safe canonical inputs and retentions / masked data only.