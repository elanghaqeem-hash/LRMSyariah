import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from check_regulatory_seeds import validate_seed  # noqa: E402


@pytest.mark.security
def test_unverified_seed_default_is_blocked_for_prod():
    seed = json.loads((ROOT / "config" / "parameters.seed.json").read_text())
    assert validate_seed(seed) == []
    assert all(x["status"] == "DRAFT_UNVERIFIED" for x in seed["regulatory_parameters"])
    assert all(x["value"] is None for x in seed["regulatory_parameters"])


@pytest.mark.security
def test_activated_or_value_seed_fails_closed():
    example = {"regulatory_parameters": [{
        "param_id": "FACTOR", "legal_basis": "rule", "status": "ACTIVE",
        "effective_from": "2026-01-01", "value": "0.50",
    }]}
    issues = validate_seed(example)
    assert len(issues) == 3


@pytest.mark.security
def test_missing_or_duplicate_seed_is_rejected():
    assert validate_seed({})
    assert validate_seed({"regulatory_parameters": []})
    assert validate_seed({"regulatory_parameters": [None]})
    dupes = {"regulatory_parameters": [
        {"param_id": "x", "legal_basis": "rule", "status": "DRAFT_UNVERIFIED", "value": None, "effective_from": None},
        {"param_id": "x", "legal_basis": "", "status": "DRAFT_UNVERIFIED", "value": None, "effective_from": None},
    ]}
    assert len(validate_seed(dupes)) == 2
