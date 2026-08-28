"""Observable run-event contract; telemetry is evidence, not authorization."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .common import (
    SCHEMA_VERSION,
    ContractMixin,
    ContractValidationError,
    RunState,
    as_jsonable,
    load_json_object,
    parse_utc_timestamp,
    require_enum,
    require_identifier,
    require_integer,
    require_json_mapping,
    require_serialized_size,
    require_text,
    strict_contract_fields,
    validate_header,
)
from .provenance import Provenance


@dataclass(frozen=True)
class RunEvent(ContractMixin):
    event_id: str
    run_id: str
    request_id: str
    tool_id: str
    sequence: int
    state: RunState
    occurred_at: str
    summary: str
    metrics: Any
    provenance: Provenance
    schema_version: str = SCHEMA_VERSION
    kind: str = field(default="run_event", init=True)

    def __post_init__(self) -> None:
        validate_header(self.schema_version, self.kind, "run_event")
        for name in ("event_id", "run_id", "request_id", "tool_id"):
            require_identifier(getattr(self, name), name)
        require_integer(self.sequence, "sequence")
        object.__setattr__(self, "state", require_enum(RunState, self.state, "state"))
        parse_utc_timestamp(self.occurred_at, "occurred_at")
        require_text(self.summary, "summary", maximum=1_024)
        object.__setattr__(self, "metrics", require_json_mapping(self.metrics, "metrics"))
        if len(self.metrics) > 32:
            raise ContractValidationError("metrics must contain at most 32 entries.")
        if not isinstance(self.provenance, Provenance):
            raise ContractValidationError("provenance must be a Provenance value.")
        require_serialized_size(self.to_dict(), "run_event")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "kind": self.kind,
            "event_id": self.event_id,
            "run_id": self.run_id,
            "request_id": self.request_id,
            "tool_id": self.tool_id,
            "sequence": self.sequence,
            "state": self.state.value,
            "occurred_at": self.occurred_at,
            "summary": self.summary,
            "metrics": as_jsonable(self.metrics),
            "provenance": self.provenance.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "RunEvent":
        checked = strict_contract_fields(
            data,
            kind="run_event",
            fields={
                "event_id",
                "run_id",
                "request_id",
                "tool_id",
                "sequence",
                "state",
                "occurred_at",
                "summary",
                "metrics",
                "provenance",
            },
        )
        return cls(
            event_id=checked["event_id"],
            run_id=checked["run_id"],
            request_id=checked["request_id"],
            tool_id=checked["tool_id"],
            sequence=checked["sequence"],
            state=checked["state"],
            occurred_at=checked["occurred_at"],
            summary=checked["summary"],
            metrics=checked["metrics"],
            provenance=Provenance.from_dict(checked["provenance"]),
            schema_version=checked["schema_version"],
            kind=checked["kind"],
        )

    @classmethod
    def from_json(cls, payload: str | bytes) -> "RunEvent":
        return cls.from_dict(load_json_object(payload))
