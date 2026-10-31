# Short-term SFT / syariah repo unwind ledger — LCR engineering

**Source:** OJK POJK 20 Tahun 2025 Lampiran I bagian III.C.1–7, official PDF: https://peraturan.bpk.go.id/Download/392109/peraturan-ojk-no-20-tahun-2025.pdf. Operational Bank certification: **HOLD**.

## Mathematical approach

1. Capture original post-haircut stock (`L1`, `L2A`, `L2B`) from eligible HQLA before composition caps. Derive immutable `hqla_stock_sha256` from the source inventory. Confirm security eligibility, independent market price and custody/encumbrance status from authoritative Bank sources; **self-declared references alone are not verification**.
2. In a fully settled *open* Islamic SFT/repo/reverse-repo/collateral exchange with maturity strictly after the position date and within **30 calendar days** inclusive, model the reversal of all eligible HQLA cash/security legs. Short-term `RETURN_TO_COUNTERPARTY` means the asset is counted in today's stock and removed on unwind; `RETURN_FROM_COUNTERPARTY` means the asset is absent from today's stock (because pledged/encumbered or transferred), becomes eligible on unwind, and is added. All movement values are **post-haircut**; haircut a given asset exactly once upstream.
3. Require *both* exchange directions, settled status, effective Sharia/legal approval, verified source contract and settlement SHA, market/custody/eligibility references, single-currency agreement and globally distinct pseudonymized asset-parcel identifiers. Inconsistent book-stock fingerprints, a negative adjusted level, duplicate collateral parcel or missing exchange half **fail closed**.
4. 31+ day transactions stay in the ledger but are **excluded from adjusted-stock movement**. They still require proper trade documentation; any other in-scope short-term unsettled or unknown-position trade blocks calculation until independently resolved.
5. Apply official Annex III.C two-deduction formula with original `L1` in the 15/60 term and adjusted levels in other terms. Do not use simplified Level2-first allocation. Return original and adjusted levels and immutable source/ledger trace.
6. Archive exactly the structured ledger in WP3 `input_snapshot` and append `lrm_sft_run_ledger`, with hash-bound linkage validated before LCR `VALIDATED`/`APPROVED`. A correction requires a **new run** and original audit ledger remains unchanged.

## Scope/assumption limitations

- Pure engine derives a **candidate** adjusted HQLA stock from approved movement fields. It does not independently certify marketability, legal eligibility, right of rehypothecation, Sharia legal validity, independent valuation, source completeness, or actual Bank custody inventory; the Bank must deliver each.
- **No automatic offset** to NCO outflow/inflow from SFT transactions. Secured funding/financing cashflow evidence needs independently proven linkage to WP1/GL input. Any potential double counting, missing reclassification or absent Bank accounting policy remains a regulatory blocker. Integration's `stock_fingerprint()` controls post-haircut asset totals, not instrument-ID-by-ID stock membership; prove instrument-ID reconciliation in Bank UAT.
- Trade/leg IDs are pseudonymous; full contracts, counterparties and actual working papers must remain within the encrypted Bank vault, not GitHub.
- Bank-owned PostgreSQL least-privilege test and restricted identity-to-transaction attribution still unverified by isolated CI.
- Structural source SHA and approval reference checks are not cryptographic Bank signature verification. Final release requires signed Bank evidence and validator sign-off.

## Scenario tests

- Exact 30th-day SFT in scope, 31st-day excluded, Bank cash out/security in and reverse scenario, negative/overdrawn stock, mismatched date and currency, unsettled/matured trades, duplicate asset parcels, duplicate leg/trade ID, missing half exchange, invalid provenance, snapshot hash tampering.
- Differential test covers measure-level and rule-ID-level exact/approved-tolerance comparisons against a **synthetic** paper. Genuine Bank paper and full historical quarter are **NOT PROVIDED**; no manufactured sign-off is allowed.

## Release gate

Independent Risk, Finance/Treasury, DPS, InfoSec/IT, and model validator acceptance are all PENDING. Repository public: only code/tests/reference policies allowed; never commit confidential Bank docs or working papers.