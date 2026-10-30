# WP0 Local Test Evidence — 2026-10-30

- Environment: Python **3.13.5** in isolated execution environment (target CI: Python **3.12**).
- `PYTHONPATH=src pytest tests/unit --cov=lrm_engine --cov-branch --cov-report=term-missing --cov-fail-under=90 -q` → **40 passed; 100% coverage** for WP0 engine primitives only.
- `python scripts/check_regulatory_seeds.py` → **PASS**, five placeholder seeds; none active, all values null.
- Python AST syntax inspection → **25 Python files parsed**.
- NOT locally run: CI workflow on Python 3.12, Ruff, mypy, Bandit, pip-audit and CycloneDX (tools unavailable locally); these are configured as CI gates. No claim that CI is green until GitHub Actions executes.
- No regulation-specific calculation rules tested: LCR/NSFR/ILAAP/DCR implementation belongs to WP4/WP8/WP9/WP10/WP11.
- Test fixtures contain synthetic, non-customer values only.
