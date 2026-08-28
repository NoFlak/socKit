"""Observable execution-result contract, separate from policy decisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from .common import (
    SCHEMA_VERSION,
    ContractMixin,
    ContractValidationError,
    load_json_object,
    require_boolean,
    require_enum,
    require_identifier,
    require_integer,
    require_serialized_size,
    require_string_tuple,
    require_text,
    require_time_window,
    strict_contract_fields,
    validate_header,
)
from .provenance import Provenance


class ExecutionOutcome(str, Enum):
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class ExecutionError:
    code: str
    message: str
    retryable: bool

    def __post_init__(self) -> None:
        require_identifier(self.code, "error.code")
        require_text(self.message, "error.message", maximum=1_024)
        require_boolean(self.retryable, "error.retryable")

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "retryable": self.retryable}

    @classmethod
    def from_dict(cls, data: Any) -> "ExecutionError":
        fields = {"code", "message", "retryable"}
        if not isinstance(data, Mapping):
            raise ContractValidationError("error must be a mapping or null.")
        if any(not isinstance(key, str) for key in data):
            raise ContractValidationError("error field names must be strings.")
        missing = sorted(fields - set(data))
        unknown = sorted(set(data) - fields)
        if missing:
            raise ContractValidationError(f"error is missing required fields: {missing}.")
        if unknown:
            raise ContractValidationError(f"error contains unknown fields: {unknown}.")
        return cls(code=data["code"], message=data["message"], retryable=data["retryable"])


@dataclass(frozen=True)
class ExecutionResult(ContractMixin):
    result_id: str
    run_id: str
    request_id: str
    tool_id: str
    outcome: ExecutionOutcome
    started_at: str
    completed_at: str
    summary: str
    exit_code: int | None
    error: ExecutionError | None
    artifact_references: tuple[str, ...]
    provenance: Provenance
    schema_version: str = SCHEMA_VERSION
    kind: str = field(default="execution_result", init=True)

    def __post_init__(self) -> None:
        validate_header(self.schema_version, self.kind, "execution_result")
        for name in ("result_id", "run_id", "request_id", "tool_id"):
            require_identifier(getattr(self, name), name)
        object.__setattr__(self, "outcome", require_enum(ExecutionOutcome, self.outcome, "outcome"))
        require_time_window(self.started_at, self.completed_at, "started_at", "completed_at")
        require_text(self.summary, "summary", maximum=1_024)
        if self.exit_code is not None:
            require_integer(
                self.exit_code,
                "exit_code",
                minimum=-2_147_483_648,
                maximum=4_294_967_295,
            )
        if self.error is not None and not isinstance(self.error, ExecutionError):
            raise ContractValidationError("error must be an ExecutionError value or null.")
        object.__setattr__(
            self,
            "artifact_references",
            require_string_tuple(
                self.artifact_references, "artifact_references", maximum_items=256
            ),
        )
        if not isinstance(self.provenance, Provenance):
            raise ContractValidationError("provenance must be a Provenance value.")
        if self.outcome is ExecutionOutcome.FAILED and self.error is None:
            raise ContractValidationError("A failed execution result must include an error.")
        if self.outcome is ExecutionOutcome.SUCCEEDED:
            if self.error is not None:
                raise ContractValidationError("A succeeded execution result must not include an error.")
            if self.exit_code not in (None, 0):
                raise ContractValidationError(
                    "A succeeded execution result must have a zero or null exit_code."
                )
        require_serialized_size(self.to_dict(), "execution_result")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "kind": self.kind,
            "result_id": self.result_id,
            "run_id": self.run_id,
            "request_id": self.request_id,
            "tool_id": self.tool_id,
            "outcome": self.outcome.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "summary": self.summary,
            "exit_code": self.exit_code,
            "error": None if self.error is None else self.error.to_dict(),
            "artifact_references": list(self.artifact_references),
            "provenance": self.provenance.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "ExecutionResult":
        checked = strict_contract_fields(
            data,
            kind="execution_result",
            fields={
                "result_id",
                "run_id",
                "request_id",
                "tool_id",
                "outcome",
                "started_at",
                "completed_at",
                "summary",
                "exit_code",
                "error",
                "artifact_references",
                "provenance",
            },
        )
        error = None if checked["error"] is None else ExecutionError.from_dict(checked["error"])
        return cls(
            result_id=checked["result_id"],
            run_id=checked["run_id"],
            request_id=checked["request_id"],
            tool_id=checked["tool_id"],
            outcome=checked["outcome"],
            started_at=checked["started_at"],
            completed_at=checked["completed_at"],
            summary=checked["summary"],
            exit_code=checked["exit_code"],
            error=error,
            artifact_references=checked["artifact_references"],
            provenance=Provenance.from_dict(checked["provenance"]),
            schema_version=checked["schema_version"],
            kind=checked["kind"],
        )

    @classmethod
    def from_json(cls, payload: str | bytes) -> "ExecutionResult":
        return cls.from_dict(load_json_object(payload))
