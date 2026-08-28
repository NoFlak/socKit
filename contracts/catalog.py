"""Tool-discovery catalog contract; catalog claims do not grant authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from .common import (
    SCHEMA_VERSION,
    ContractMixin,
    ContractValidationError,
    as_jsonable,
    load_json_object,
    parse_utc_timestamp,
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


class ActionMode(str, Enum):
    INFORMATIONAL = "informational"
    READ_ONLY = "read-only"
    SENSITIVE_READ_ONLY = "sensitive-read-only"
    ACTIVE_READ_ONLY = "active-read-only"
    PREVIEW = "preview"
    STATE_CHANGING = "state-changing"


class CapabilityState(str, Enum):
    OPERATIONAL = "operational"
    PREVIEW_ONLY = "preview-only"
    SYNTHETIC = "synthetic"
    PLACEHOLDER = "placeholder"
    UNAVAILABLE = "unavailable"
    DEPRECATED = "deprecated"


_RESTRICTED_MODES = {
    ActionMode.SENSITIVE_READ_ONLY,
    ActionMode.ACTIVE_READ_ONLY,
    ActionMode.STATE_CHANGING,
}


@dataclass(frozen=True)
class ToolDefinition:
    tool_id: str
    tool_version: int
    label: str
    description: str
    action_mode: ActionMode
    capability_state: CapabilityState
    scope_types: tuple[str, ...]
    platforms: tuple[str, ...]
    privilege_required: str
    authorization_required: bool
    preview_supported: bool
    timeout_seconds: int
    cancel_supported: bool

    def __post_init__(self) -> None:
        require_identifier(self.tool_id, "tool_id")
        require_integer(self.tool_version, "tool_version", minimum=1, maximum=1_000_000)
        require_text(self.label, "label", maximum=128)
        require_text(self.description, "description", maximum=1_024)
        object.__setattr__(self, "action_mode", require_enum(ActionMode, self.action_mode, "action_mode"))
        object.__setattr__(
            self,
            "capability_state",
            require_enum(CapabilityState, self.capability_state, "capability_state"),
        )
        object.__setattr__(
            self, "scope_types", require_string_tuple(self.scope_types, "scope_types", identifiers=True)
        )
        object.__setattr__(
            self, "platforms", require_string_tuple(self.platforms, "platforms", identifiers=True)
        )
        require_identifier(self.privilege_required, "privilege_required")
        require_boolean(self.authorization_required, "authorization_required")
        require_boolean(self.preview_supported, "preview_supported")
        require_integer(self.timeout_seconds, "timeout_seconds", minimum=1, maximum=86_400)
        require_boolean(self.cancel_supported, "cancel_supported")
        if self.action_mode in _RESTRICTED_MODES and not self.authorization_required:
            raise ContractValidationError(
                "Sensitive, active, and state-changing catalog entries must declare authorization_required."
            )
        if self.capability_state is CapabilityState.PREVIEW_ONLY and not self.preview_supported:
            raise ContractValidationError("A preview-only tool must declare preview_supported.")

    def to_dict(self) -> dict[str, Any]:
        return as_jsonable(
            {
                "tool_id": self.tool_id,
                "tool_version": self.tool_version,
                "label": self.label,
                "description": self.description,
                "action_mode": self.action_mode,
                "capability_state": self.capability_state,
                "scope_types": self.scope_types,
                "platforms": self.platforms,
                "privilege_required": self.privilege_required,
                "authorization_required": self.authorization_required,
                "preview_supported": self.preview_supported,
                "timeout_seconds": self.timeout_seconds,
                "cancel_supported": self.cancel_supported,
            }
        )

    @classmethod
    def from_dict(cls, data: Any) -> "ToolDefinition":
        fields = {
            "tool_id",
            "tool_version",
            "label",
            "description",
            "action_mode",
            "capability_state",
            "scope_types",
            "platforms",
            "privilege_required",
            "authorization_required",
            "preview_supported",
            "timeout_seconds",
            "cancel_supported",
        }
        if not isinstance(data, Mapping):
            raise ContractValidationError("tool definition must be a mapping.")
        if any(not isinstance(key, str) for key in data):
            raise ContractValidationError("tool definition field names must be strings.")
        missing = sorted(fields - set(data))
        unknown = sorted(set(data) - fields)
        if missing:
            raise ContractValidationError(f"tool definition is missing required fields: {missing}.")
        if unknown:
            raise ContractValidationError(f"tool definition contains unknown fields: {unknown}.")
        return cls(**{name: data[name] for name in fields})


@dataclass(frozen=True)
class ToolCatalog(ContractMixin):
    catalog_id: str
    revision: int
    published_at: str
    valid_until: str
    provenance: Provenance
    tools: tuple[ToolDefinition, ...]
    schema_version: str = SCHEMA_VERSION
    kind: str = field(default="tool_catalog", init=True)

    def __post_init__(self) -> None:
        validate_header(self.schema_version, self.kind, "tool_catalog")
        require_identifier(self.catalog_id, "catalog_id")
        require_integer(self.revision, "revision", minimum=1, maximum=1_000_000)
        require_time_window(self.published_at, self.valid_until, "published_at", "valid_until")
        if not isinstance(self.provenance, Provenance):
            raise ContractValidationError("provenance must be a Provenance value.")
        if not isinstance(self.tools, tuple) or not self.tools or len(self.tools) > 1_024:
            raise ContractValidationError("tools must be a non-empty tuple with at most 1024 entries.")
        if any(not isinstance(tool, ToolDefinition) for tool in self.tools):
            raise ContractValidationError("tools must contain only ToolDefinition values.")
        tool_ids = [tool.tool_id for tool in self.tools]
        if len(tool_ids) != len(set(tool_ids)):
            raise ContractValidationError("tools must not contain duplicate tool_id values.")
        require_serialized_size(self.to_dict(), "tool_catalog")

    def is_fresh(self, at: str) -> bool:
        moment = parse_utc_timestamp(at, "at")
        return parse_utc_timestamp(self.published_at, "published_at") <= moment <= parse_utc_timestamp(
            self.valid_until, "valid_until"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "kind": self.kind,
            "catalog_id": self.catalog_id,
            "revision": self.revision,
            "published_at": self.published_at,
            "valid_until": self.valid_until,
            "provenance": self.provenance.to_dict(),
            "tools": [tool.to_dict() for tool in self.tools],
        }

    @classmethod
    def from_dict(cls, data: Any) -> "ToolCatalog":
        checked = strict_contract_fields(
            data,
            kind="tool_catalog",
            fields={"catalog_id", "revision", "published_at", "valid_until", "provenance", "tools"},
        )
        if not isinstance(checked["tools"], (list, tuple)):
            raise ContractValidationError("tools must be an array.")
        return cls(
            catalog_id=checked["catalog_id"],
            revision=checked["revision"],
            published_at=checked["published_at"],
            valid_until=checked["valid_until"],
            provenance=Provenance.from_dict(checked["provenance"]),
            tools=tuple(ToolDefinition.from_dict(item) for item in checked["tools"]),
            schema_version=checked["schema_version"],
            kind=checked["kind"],
        )

    @classmethod
    def from_json(cls, payload: str | bytes) -> "ToolCatalog":
        return cls.from_dict(load_json_object(payload))
