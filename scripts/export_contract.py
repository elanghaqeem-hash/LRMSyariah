"""Export machine-readable JSON Schema from Pydantic source of truth (WP1)."""
from __future__ import annotations

import json
from pathlib import Path

from lrm_data.schema import DATASET_MODELS, SourceMetadata


def main() -> None:
    path = Path("docs/data-contract/json-schema")
    path.mkdir(parents=True, exist_ok=True)
    for dataset, model in DATASET_MODELS.items():
        schema = model.model_json_schema()
        schema["$comment"] = ("Provisional LRM Bank Syariah Phase-1 data contract. "
                                "Bank source mapping / regulatory rules not yet approved.")
        (path / f"{dataset.value}.schema.json").write_text(
            json.dumps(schema, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    (path / "SourceMetadata.schema.json").write_text(
        json.dumps(SourceMetadata.model_json_schema(), indent=2, ensure_ascii=False,
                   sort_keys=True) + "\n", encoding="utf-8",
    )
    print(f"Exported {len(DATASET_MODELS) + 1} schema documents")


if __name__ == "__main__":
    main()
