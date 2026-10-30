# WP1 local test evidence — 30 Oct 2026

- Environment: Python 3.13.5, Linux, Pydantic 2.13.5, openpyxl 3.1.5, pytest 9.0.2, pytest-cov 7.0.0.
- Command: `pytest -q --cov=lrm_engine --cov=lrm_data --cov-branch --cov-report=term-missing`.
- Result: **97 passed**, including **40 WP0** foundation tests and **57 new WP1** tests.
- Combined branch-aware coverage: **92.80%** across the currently implemented `lrm_engine` and `lrm_data` packages; `lrm_engine` foundation lines remain fully covered. Do **not** interpret this as LCR/NSFR regulatory rule coverage.
- `python scripts/check_regulatory_seeds.py` → **PASS**, five seeds remain unverified/non-active.
- `python scripts/validate_synthetic.py` → `WARNING`; 13 synthetic files, 0 FAIL, 9 warnings (akad mapping pending), `calculation_allowed=false`, `submission_allowed=false`.
- Negative tests cover invalid extension, broken ZIP, formulas, hidden rows, duplicate header, float-money input, PII-like raw ID rejection, unsupported akad, missing metadata, external links, missing dataset, mismatched date/currency, duplicate business key, missing GL, maturity in past, future-effective reference and cross-dataset product/akad conflicts.

**Not executed in this sandbox:** GitHub CI Python 3.12, mypy/ruff, Bandit, dependency audit, CycloneDX, Docker security tests and enterprise UAT. Package install succeeded locally only with `--no-build-isolation` because network resolution for build dependency downloads was unavailable; this does not validate the full CI toolchain. Formal Bank input volumes, latency and signed data contract are not available.
