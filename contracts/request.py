"""Execution-request contract; requests carry intent, never implicit authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .common import (
    SCHEMA_VERSION,
    ContractMixin,
    ContractValidationError,
    as_jsonable,
    load_json_object,
    parse_utc_timestamp,
    require_identifier,
    require_json_mapping,
    require_optional_identifier,
    require_serialized_size,
    require_string_tuple,
    require_time_window,
    strict_contract_fields,
    validate_header,
)
from .provenance import Provenance


@dataclass(frozen=True)
class ExecutionRequest(ContractMixin):
    request_id: str
    idempotency_key: str
    tool_id: str
    requested_at: str
    expires_at: str
    provenance: Provenance
    arguments: Any
    scope: tuple[str, ...]
    operator_id: str | None
    tenant_id: str | None
    authorization_reference: str | None
    schema_version: str = SCHEMA_VERSION
    kind: str = field(default="execution_request", init=True)

    def __post_init__(self) -> None:
        validate_header(self.schema_version, self.kind, "execution_request")
        require_identifier(self.request_id, "request_id")
        require_identifier(self.idempotency_key, "idempotency_key")
        require_identifier(self.tool_id, "tool_id")
        require_time_window(self.requested_at, self.expires_at, "requested_at", "expires_at")
        if not isinstance(self.provenance, Provenance):
            raise ContractValidationError("provenance must be a Provenance value.")
        object.__setattr__(self, "arguments", require_json_mapping(self.arguments, "arguments"))
        object.__setattr__(
            self, "scope", require_string_tuple(self.scope, "scope", identifiers=True, maximum_items=256)
        )
        require_optional_identifier(self.operator_id, "operator_id")
        require_optional_identifier(self.tenant_id, "tenant_id")
        require_optional_identifier(self.authorization_reference, "authorization_reference")
        require_serialized_size(self.to_dict(), "execution_request")

    def is_fresh(self, at: str) -> bool:
        moment = parse_utc_timestamp(at, "at")
        return parse_utc_timestamp(self.requested_at, "requested_at") <= moment <= parse_utc_timestamp(
            self.expires_at, "expires_at"
        )

    @property
    def replay_key(self) -> tuple[str | None, str, str]:
        """Stable key for an owning service's durable replay store."""

        return (self.tenant_id, self.tool_id, self.idempotency_key)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "kind": self.kind,
            "request_id": self.request_id,
            "idempotency_key": self.idempotency_key,
            "tool_id": self.tool_id,
            "requested_at": self.requested_at,
            "expires_at": self.expires_at,
            "provenance": self.provenance.to_dict(),
            "arguments": as_jsonable(self.arguments),
            "scope": list(self.scope),
            "operator_id": self.operator_id,
            "tenant_id": self.tenant_id,
            "authorization_reference": self.authorization_reference,
        }

    @classmethod
    def from_dict(cls, data: Any) -> "ExecutionRequest":
        checked = strict_contract_fields(
            data,
            kind="execution_request",
            fields={
                "request_id",
                "idempotency_key",
                "tool_id",
                "requested_at",
                "expires_at",
                "provenance",
                "arguments",
                "scope",
                "operator_id",
                "tenant_id",
                "authorization_reference",
            },
        )
        return cls(
            request_id=checked["request_id"],
            idempotency_key=checked["idempotency_key"],
            tool_id=checked["tool_id"],
            requested_at=checked["requested_at"],
            expires_at=checked["expires_at"],
            provenance=Provenance.from_dict(checked["provenance"]),
            arguments=checked["arguments"],
            scope=checked["scope"],
            operator_id=checked["operator_id"],
            tenant_id=checked["tenant_id"],
            authorization_reference=checked["authorization_reference"],
            schema_version=checked["schema_version"],
            kind=checked["kind"],
        )

    @classmethod
    def from_json(cls, payload: str | bytes) -> "ExecutionRequest":
        return cls.from_dict(load_json_object(payload))


def validate_unique_requests(requests: tuple[ExecutionRequest, ...]) -> None:
    """Reject duplicates in one intake batch; durable replay defense remains external."""

    if not isinstance(requests, tuple) or len(requests) > 10_000 or any(
        not isinstance(request, ExecutionRequest) for request in requests
    ):
        raise ContractValidationError(
            "requests must be a tuple of at most 10000 ExecutionRequest values."
        )
    request_ids = [request.request_id for request in requests]
    replay_keys = [request.replay_key for request in requests]
    if len(request_ids) != len(set(request_ids)):
        raise ContractValidationError("requests contain a duplicate request_id.")
    if len(replay_keys) != len(set(replay_keys)):
        raise ContractValidationError("requests contain a duplicate replay key.")
