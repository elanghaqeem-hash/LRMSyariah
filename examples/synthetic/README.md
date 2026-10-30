# SYNTHETIC TEST DATA — NOT BANK DATA

All 13 XLSX workbooks are generated deterministically in content from
`scripts/generate_synthetic_inputs.py`. The zip container byte hashes may change
across runs because Excel archive metadata can change. File-level SHA-256 is
computed at ingestion and stored in the DQ evidence file.

**DO NOT** treat synthetic ratio values (including 0 GWM/PLM) as verified
legal/regulatory assumptions. Do not insert customer/Bank PII here.
