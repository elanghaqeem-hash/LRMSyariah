# LCR differential testing against Bank working paper

## Input contract

Bank must provide a controlled **machine-readable summary** (adapted from its own authorised daily LCR working paper) as a JSON object:

- `reporting_date` (ISO-8601 day), `currency` (ISO code, approved FX basis),
- `measures`: `hqla`, `outflow`, `inflow_raw`, `inflow_used`, `net_cash_outflow`, `lcr` as ratio (e.g. 1.25, not 125), `level1`, `level2a`, `level2b`, `adjusted_level1`, `adjusted_level2a`, `adjusted_level2b` (all values **strings** in decimal notation),
- `rule_amounts`: each source-engine regulatory `rule_id` with gross/weighted amount matching the `trace` convention and signed Bank classification.

The secure adapter must **validate the exact SHA-256 of raw JSON bytes against a separately approved vault digest**, position date, currency and full category coverage. An approval reference is metadata and does **not** constitute independent signature authentication. The Bank must attest its genuine hash, user role, and sign-off in its protected data room.

## Reconciliation methods

1. Read Bank-approved snapshot and calculate engine result using exact engine semver + Git SHA, frozen WP2 parameter and akad revisions, and WP3 immutable source/SFT batches.
2. Compare twelve aggregate measures plus every rule ID without dropping zero/different classifications; reject missing/extra categories. Compare ratio with ratio tolerance and monetary amounts with money tolerance, both independently approved and never guessed.
3. Each delta becomes a variance finding with field name, sign, exact Decimal amount, reason/owner and root-cause workflow. A tolerance PASS is not automatic permission to publish.
4. Persist only non-sensitive hashes and summary counts in public engineering evidence; detailed paper, account/customer data and raw variance explanations remain in encrypted Bank Vault.
5. Re-run every position date for one **real full quarter** after Bank extract availability. Use `docs/validation/parallel_run_register_template.csv` to record immutable per-day evidence, exception and checker.
6. Independent validator, SKMR, Finance, DPS, TI must separately sign. Any unexplained material variance, missing FX basis, double-counted SFT, or missing maturity schedule = HOLD.

## CLI (only in a secured Bank UAT workspace)

```bash
python scripts/run_lcr_differential.py \
  --bank-paper /secure/vault/working_paper_summary.json \
  --engine-result /secure/vault/engine_result.json \
  --paper-sha256 <vault_approved_sha256> \
  --bank-approval-ref <bank_signed_record_reference> \
  --bank-approval-sha256 <bank_signature_document_sha256> \
  --date YYYY-MM-DD --currency IDR \
  --amount-tolerance <approved_decimal> --ratio-tolerance <approved_decimal> \
  --tolerance-approval-ref <approved_tolerance_policy>
```

The CLI prints **only PASS/FAILED, counts, and SHA digests**. Use `--synthetic` for simulation; an engineering PASS never substitutes for signed Bank working papers. The current repository contains no actual Bank paper or a validated quarter of daily data. **Production remains NO-GO.**