"""Engine build provenance; rule: ENG-TRACE-002."""
from __future__ import annotations

import re
from dataclasses import dataclass

_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class EngineBuild:
    """Immutable engine version; caller injects verified git SHA at packaging."""

    semver: str
    git_sha: str

    def __post_init__(self) -> None:
        if not _SEMVER.fullmatch(self.semver):
            raise ValueError("engine semver is invalid")
        if not _GIT_SHA.fullmatch(self.git_sha):
            raise ValueError("full lowercase 40-character git SHA required")

    @property
    def identity(self) -> str:
        separator = "." if "+" in self.semver else "+"
        return f"{self.semver}{separator}git.{self.git_sha}"
