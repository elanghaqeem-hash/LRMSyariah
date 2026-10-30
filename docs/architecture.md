# Architecture and boundaries

```
Excel files (WP1) / future validated warehouse views
       ↓
lrm_data (schema, DQ and reconciliation)
       ↓
lrm_services (rule/version orchestration, approval, audit)
       ↓
lrm_engine (pure value objects and functions)
       ↓
lrm_reporting (regulatory pack / audit pack)
       ↑
lrm_ui (thin Streamlit layer; never holds personal bank data in session)
```

The engine cannot import `pandas`, `sqlalchemy`, `streamlit`, `requests`, or network
modules. Regulation-specific factors will arrive as immutable, validated parameter
snapshots through the service layer (WP2–WP4). No calculation can proceed when
mapping or parameter verification fails. Engineering packaging on prem is WP12.

**Note:** Hash-based result reproducibility also requires stable rule ordering,
canonical record sorting, clock isolation, pinned dependency versions, and archived
inputs. WP3–WP4 must implement and validate these guarantees end-to-end.
