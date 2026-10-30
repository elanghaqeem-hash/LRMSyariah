# WP1 source ingestion and validation methodology

**Control IDs:** R10, DQ-FILE-001, DQ-SCHEMA-001, DQ-VAL-001, DQ-AKAD-001/002, DQ-DATE-001, DQ-CURRENCY-001, DQ-DUP-001, DQ-REF-001, DQ-MATURITY-001/002, DQ-SCOPE-001.

1. Receive file **bytes** via caller and compute SHA-256 before parsing; do not save or log source contents.
2. Reject unsupported extension, excessive zipped/uncompressed size, suspicious compression, macros, formula/error cells, hidden sheets/rows/columns, and external workbook links.
3. Require two named worksheets. Parse metadata and compare `schema_version=1.0` and typed values against Pydantic source classes. No guessed mapping of legacy Bank columns.
4. Validate each source row using Pydantic; reject floats, invalid bounds, invalid akad vocabulary, unmasked account/facility identifiers. DQ errors deliberately show only field/row/source hash, never source values.
5. Validate batch consistency (one report date/currency, unique dataset and business keys, optional exact required-file scope) and GL key existence in the daily balance sheet.
6. `DQ-AKAD-002` is emitted for all current files containing akad fields because WP2 *approved* mappings are not installed. Neither this warning nor an `OTHER` akad can silently be bypassed.
7. Output immutable `LoadedSource`/`ParsedRow` values and a DQ report; a status other than `PASS` prevents submission. Workflow approval and trace archiving start in WP2/WP3.

The Excel loader uses local in-memory bytes, `openpyxl`, and `pydantic`. Engine remains a pure Python package and does not import the loader. **No regulatory factor is applied** at the ingestion stage; legal interpretation is still pending official rule-to-test verification.

## Design boundaries & remaining risk

- `NeracaHarian` GL references ensure existence, not account/segment sign or amount reconciliation (WP5).
- A timestamp from the data warehouse or intraday transaction stream may be added without altering WP1's daily reporting date.
- Two full sources may contain legitimate repeated business keys across subledgers; current contract fails duplicates until Bank establishes a signed composite-key policy. No automatic deduplication.
- Numeric Excel values with binary floating point are refused. Excel may truncate values before export; source processes must emit decimal strings and validate against original core banking figures.
- The loader does not accept legacy `.xls`, `.xlsm`, `.xlsb`, or hidden formulas. A future import adapter must be separately tested.
- DQ `WARNING` cannot be accepted by WP1 alone. Maker explanations/checker decisions must be linked to governance and audit trail in WP2/WP3.
