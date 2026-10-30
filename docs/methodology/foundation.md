# WP0 Calculation Methodology Foundations

- **Number format:** monetary quantities and regulatory factors are `Decimal`.
  API input numbers must be decimal strings or integers, never binary floats.
- **Precision:** arithmetic should use local decimal context with precision 38,
  ROUND_HALF_EVEN; invalid operations, overflow and division by zero raise.
  This is an **engineering setting**, not a regulatory rounding policy.
- **Rounding:** none in the engine during intermediate aggregation. Output
  rounding is explicit and configured per output/report definition in a later WP.
- **Canonical representations:** all Decimal forms normalize to plain string;
  UTC datetimes to ISO 8601 `Z`, dates to ISO 8601, maps by lexical keys; floats,
  naive datetimes and unsupported objects rejected.
- **Maturity buckets:** must be passed by caller as a validated definition;
  no regulatory tenor classification hard-coded in WP0.
- **Legal trace:** every regulatory rule/factor has rule_id, legal_basis, test
  and approval state (WP2–WP4).
- **Regulatory methodology:** LCR, NSFR, ILAAP, survival, DCR formulas
  **NOT IMPLEMENTED** in WP0; no claims of regulatory compliance.
