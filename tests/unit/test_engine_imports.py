"""Ensure the engine stays separate from I/O, DB and presentation libraries."""
import ast
from pathlib import Path

import pytest

ENGINE_ROOT = Path(__file__).resolve().parents[2] / "src" / "lrm_engine"
FORBIDDEN = {"pandas", "sqlalchemy", "streamlit", "requests", "httpx", "socket", "psycopg", "pathlib"}


@pytest.mark.unit
def test_engine_has_no_forbidden_imports():
    for path in ENGINE_ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(item.name.split(".")[0] not in FORBIDDEN for item in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in FORBIDDEN
