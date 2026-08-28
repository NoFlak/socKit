"""Untrusted provenance assertions shared by runtime contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .common import (
    ContractValidationError,
    parse_utc_timestamp,
    require_identifier,
    require_optional_identifier,
)


@dataclass(frozen=True)
class Provenance:
    source_id: str
    source_instance_id: str
    observed_at: str
    correlation_id: str | None

    def __post_init__(self) -> None:
        require_identifier(self.source_id, "source_id")
        require_identifier(self.source_instance_id, "source_instance_id")
        parse_utc_timestamp(self.observed_at, "observed_at")
        require_optional_identifier(self.correlation_id, "correlation_id")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_instance_id": self.source_instance_id,
            "observed_at": self.observed_at,
            "correlation_id": self.correlation_id,
        }

    @classmethod
    def from_dict(cls, data: Any) -> "Provenance":
        fields = {"source_id", "source_instance_id", "observed_at", "correlation_id"}
        if not isinstance(data, Mapping):
            raise ContractValidationError("provenance must be a mapping.")
        if any(not isinstance(key, str) for key in data):
            raise ContractValidationError("provenance field names must be strings.")
        missing = sorted(fields - set(data))
        unknown = sorted(set(data) - fields)
        if missing:
            raise ContractValidationError(f"provenance is missing required fields: {missing}.")
        if unknown:
            raise ContractValidationError(f"provenance contains unknown fields: {unknown}.")
        return cls(**{name: data[name] for name in fields})
