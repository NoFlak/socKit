"""Policy-decision contract, intentionally separate from signals and execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .common import (
    SCHEMA_VERSION,
    ContractMixin,
    ContractValidationError,
    load_json_object,
    parse_utc_timestamp,
    require_enum,
    require_identifier,
    require_optional_identifier,
    require_serialized_size,
    require_string_tuple,
    require_time_window,
    strict_contract_fields,
    validate_header,
)
from .provenance import Provenance


class PolicyOutcome(str, Enum):
    ALLOW = "allow"
    ALLOW_PREVIEW = "allow-preview"
    DENY = "deny"


@dataclass(frozen=True)
class PolicyDecision(ContractMixin):
    decision_id: str
    request_id: str
    tool_id: str
    outcome: PolicyOutcome
    reasons: tuple[str, ...]
    policy_version: str
    decided_at: str
    expires_at: str
    decided_scope: tuple[str, ...]
    authorization_reference: str | None
    provenance: Provenance
    schema_version: str = SCHEMA_VERSION
    kind: str = field(default="policy_decision", init=True)

    def __post_init__(self) -> None:
        validate_header(self.schema_version, self.kind, "policy_decision")
        require_identifier(self.decision_id, "decision_id")
        require_identifier(self.request_id, "request_id")
        require_identifier(self.tool_id, "tool_id")
        object.__setattr__(self, "outcome", require_enum(PolicyOutcome, self.outcome, "outcome"))
        object.__setattr__(self, "reasons", require_string_tuple(self.reasons, "reasons"))
        require_identifier(self.policy_version, "policy_version")
        require_time_window(self.decided_at, self.expires_at, "decided_at", "expires_at")
        object.__setattr__(
            self,
            "decided_scope",
            require_string_tuple(self.decided_scope, "decided_scope", identifiers=True, maximum_items=256),
        )
        require_optional_identifier(self.authorization_reference, "authorization_reference")
        if not isinstance(self.provenance, Provenance):
            raise ContractValidationError("provenance must be a Provenance value.")
        if self.outcome is PolicyOutcome.DENY and not self.reasons:
            raise ContractValidationError("A denied policy decision must include at least one reason.")
        require_serialized_size(self.to_dict(), "policy_decision")

    def is_fresh(self, at: str) -> bool:
        moment = parse_utc_timestamp(at, "at")
        return parse_utc_timestamp(self.decided_at, "decided_at") <= moment <= parse_utc_timestamp(
            self.expires_at, "expires_at"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "kind": self.kind,
            "decision_id": self.decision_id,
            "request_id": self.request_id,
            "tool_id": self.tool_id,
            "outcome": self.outcome.value,
            "reasons": list(self.reasons),
            "policy_version": self.policy_version,
            "decided_at": self.decided_at,
            "expires_at": self.expires_at,
            "decided_scope": list(self.decided_scope),
            "authorization_reference": self.authorization_reference,
            "provenance": self.provenance.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Any) -> "PolicyDecision":
        checked = strict_contract_fields(
            data,
            kind="policy_decision",
            fields={
                "decision_id",
                "request_id",
                "tool_id",
                "outcome",
                "reasons",
                "policy_version",
                "decided_at",
                "expires_at",
                "decided_scope",
                "authorization_reference",
                "provenance",
            },
        )
        return cls(
            decision_id=checked["decision_id"],
            request_id=checked["request_id"],
            tool_id=checked["tool_id"],
            outcome=checked["outcome"],
            reasons=checked["reasons"],
            policy_version=checked["policy_version"],
            decided_at=checked["decided_at"],
            expires_at=checked["expires_at"],
            decided_scope=checked["decided_scope"],
            authorization_reference=checked["authorization_reference"],
            provenance=Provenance.from_dict(checked["provenance"]),
            schema_version=checked["schema_version"],
            kind=checked["kind"],
        )

    @classmethod
    def from_json(cls, payload: str | bytes) -> "PolicyDecision":
        return cls.from_dict(load_json_object(payload))
