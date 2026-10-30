# Data contract 1.0 — Bank Umum Syariah (WP1)

**Status:** proposed Bank data interface, not a signed Bank source specification. **No claim of regulatory correctness** for provisional category fields, Bank-specific LPS rules, GWM/PLM ratios, or akad definitions.

## Workbook layout (exact)

All Fase 1 files must be `.xlsx`; two worksheets named `__meta__` and `data` (visible, no hidden rows/columns). No formulas, macros, external links, or workbook connections; values only. Metadata has exactly two headers on row 1: `key`, `value`. One key and one value per subsequent row:

| Key | Meaning | Required? | Example (synthetic) |
|---|---|---|---|
| `schema_version` | Exact interface version | Yes | `1.0` |
| `dataset_type` | One of 13 canonical names | Yes | `GiroTabungan` |
| `reporting_date` | One cutoff (date only) | Yes | `2026-10-30` |
| `reporting_currency` | ISO 4217 uppercase | Yes | `IDR` |
| `source_system` | Named Bank source/extractor | Yes | `SYNTHETIC_GENERATOR` |
| `extracted_at` | ISO datetime with timezone | Yes | `2026-10-30T01:00:00+07:00` |
| `source_reference` | Export/batch reference for evidence | Yes | `SYNTHETIC-WP1-NOT-BANK-DATA` |

Every data row includes mandatory `currency` (ISO 4217 uppercase). It must match `reporting_currency`; automated FX conversion is intentionally unavailable pending Bank approval. The `data` worksheet row 1 contains **exact** canonical field names. Column order may vary. Unknown/missing columns and invalid rows fail. The Pydantic models in `src/lrm_data/schema.py` are the machine-authoritative field definitions; JSON Schema exports under `json-schema/` are generated copies. Dates are ISO `YYYY-MM-DD` or Excel date cells; **money and factors must be text decimal strings** to avoid floating-point contamination (e.g., `"123456.70"`, `"0.042"`). Empty optional cells are allowed; required fields may not be empty. Percentages such as rate/nisbah use decimal fractions (0.60 = 60%), not displayed percentage points.

Customer account and financing identifiers must be tokenized at source: `MASK-` / `TOKEN-` followed by at least six ASCII alphanumeric/`_`/`-` characters. No names, national identifiers, raw account numbers, or bank secrets in examples or repository. Actual Bank tokenization method is a mobilization decision.

## File catalogue and mandatory fields

*All listed columns are mandatory unless marked optional; **every dataset additionally requires `currency`**. The `akad` attribute is required for engine-eligible instrument, asset, liability, financing and off-balance rows, but not GL reference/capital/rate master entries. This exception is intentional: those reference records are not themselves fed to ratio classification.*

| Dataset (`dataset_type`) | Fields |
|---|---|
| `NeracaHarian` | `gl_code`, `pos_neraca`, `saldo` (signed) |
| `PenempatanBI` | `placement_id`, `jenis`, `gl_code`, `akad`, `saldo`, `jatuh_tempo` (optional) |
| `SuratBerhargaSyariah` | `instrument_id`, `gl_code`, `isin`, `jenis`, `issuer_code`, `akad`, `rating` (optional), `agency` (optional), `jatuh_tempo`, `nilai_pasar`, `encumbered_flag` |
| `PenempatanBankLain` | `placement_id`, `gl_code`, `counterparty_code`, `akad`, `jatuh_tempo`, `saldo` |
| `GiroTabungan` | `account_id`, `gl_code`, `product_code`, `akad`, `segmen`, `lps_eligible`, `operational_flag`, `relationship_months`, `saldo` |
| `Deposito` | `account_id`, `gl_code`, `product_code`, `akad`, `jatuh_tempo`, `aro_flag`, `early_withdrawal_penalty` (optional), `segmen`, `saldo` |
| `KewajibanAntarBank` | `funding_id`, `gl_code`, `counterparty_code`, `akad`, `jatuh_tempo`, `saldo` |
| `Pembiayaan` | `facility_id`, `gl_code`, `product_code`, `akad`, `kolektibilitas` (integer 1–5), `jatuh_tempo`, `jadwal_angsuran`, `outstanding`, `encumbered_flag` |
| `Kontinjensi` | `commitment_id`, `gl_code` (optional), `jenis`, `counterparty_type`, `akad`, `nilai` |
| `DistribusiBagiHasil` | `distribution_id`, `product_code`, `akad`, `tenor_months`, `nisbah_nasabah`, `distributable_revenue`, `equivalent_rate` |
| `BenchmarkImbalHasil` | `benchmark_type`, `rate`, `sumber`, `tanggal_efektif` |
| `Permodalan` | `component_id`, `gl_code`, `komponen_modal`, `nominal` |
| `KewajibanGWMPLM` | `reference_id`, `rasio_gwm`, `rasio_plm`, `tanggal_efektif`, `sumber`, `legal_basis`, `verification_status` **must be `DRAFT_UNVERIFIED`** |

`jadwal_angsuran` is a JSON array in one Excel **text** cell: `[{"tanggal":"2026-11-02","nilai":"50000"}]`. Schedule amounts are exact decimals and positive; events in the past create DQ warnings. Field list is **not** an assertion that these suffice for every OJK reporting line. Additional Bank-approved category attributes, particularly for HQLA eligibility, depositor stability, operational deposit, LPS and NSFR bucketing, may be required in WP2–WP4; do not invent defaults.

## Status & gating

- `FAILED`: row or file rejected; blocked from calculation/approval.
- `WARNING`: no structural failure, but maker must explain and checker must resolve/approve as applicable. WP1 always warns for akad mapping pending WP2; **calculation and submission are blocked** until the mapping service is approved.
- `PASS`: all configured rules pass and no warning. In WP1, it is possible only for restricted reference-data scope; not a signoff for regulator.
- `DQ-SCOPE-001`: if Bank has not specified mandatory files per run, scope is `WARNING`.
- Exchange rates are not assumed. Non-matching `reporting_currency` yields `FAILED`. Bank must supply FX conversion sources and effective-dated policy before multi-currency batches can pass.
- The `NeracaHarian` GL check is **existence only**, not a signed financial amount reconciliation. 3-layer reconciliation is **WP5**.

## Known boundaries

1. Source date grain is `reporting_date`, with `extracted_at` timestamp for provenance. Transaction-time/intraday detail requires later approved contract extensions (Fase 2), not invented in Fase 1.
2. The initial `akad` vocabulary lists project-known names, not the approved product-code mapping. `other_pending_bank_approval` is rejected by DQ. Product/akad mapping and syariah legal basis need WP2 approval.
3. Synthetic GWM/PLM values `0` are deliberately NOT real reference rates and cannot be activated. All legal references are `[VERIFY]` pending Bank/OJK/BI verification.
4. Encoding for Bank-specific counterparty IDs, segment codebook, IFBS categories, rating agencies, fee/penalty treatment, consolidation group member scope, cut-off time and input volume are **TBC-BANK**.
5. Supports only standard `.xlsx` files with formulas disabled. The loader is bounded to 20 MiB compressed, 160 MiB uncompressed and 100,000 data rows per file; these engineering limits must be load-tested and Bank-approved before UAT.

## Generate/run

```bash
python -m pip install -e '.[dev]'
python scripts/export_contract.py
python scripts/generate_synthetic_inputs.py
python scripts/validate_synthetic.py
pytest tests/unit/test_wp1* tests/integration -q
```

All `examples/synthetic/*.xlsx` are made from synthetic literals in `scripts/generate_synthetic_inputs.py` only.

## WP2 extension (30 October 2026)

The governed `mapping` is based on `(DatasetType, source key, akad)` with
classification categories and rule ID supplied by Bank. Nine source dataset
types with an akad use the fields defined in
`lrm_services/akad_gateway.py::SOURCE_KEY_FIELDS`; sources without akad (GL,
capital, benchmark and GWM reference) are exempt from the product mapping
control but remain subject to their other data-quality rules.

Complete active mapping AND an approved, explicit mandatory regulatory parameter
list are needed to clear the WP2 DQ gate; no real Bank mapping is embedded.
The Bank must validate which non-product classifier key is legally correct.
