"""Shared validation and serialization primitives for runtime contracts.

The helpers in this module deliberately avoid dynamic type resolution.  A caller
must select the expected contract class before parsing untrusted input.
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, TypeAlias


SCHEMA_VERSION = "sockit.runtime/v0alpha1"
MAX_SERIALIZED_BYTES = 65_536
MAX_JSON_DEPTH = 8
MAX_JSON_ITEMS = 128
MAX_JSON_STRING = 4_096
MAX_JSON_NODES = 2_048

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@-]{0,127}$")
_UTC_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"
)
_CONTROL_CHARACTER = re.compile(r"[\x00-\x1f\x7f]")

JsonScalar: TypeAlias = None | bool | int | float | str
JsonValue: TypeAlias = JsonScalar | Mapping[str, "JsonValue"] | tuple["JsonValue", ...]


class ContractValidationError(ValueError):
    """Raised when data fails a runtime-contract boundary check."""


class RunState(str, Enum):
    PENDING_POLICY = "pending-policy"
    DENIED = "denied"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


def require_identifier(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ContractValidationError(
            f"{field_name} must be a stable identifier of 1-128 safe characters."
        )
    return value


def require_optional_identifier(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    return require_identifier(value, field_name)


def require_text(value: Any, field_name: str, *, maximum: int = 512) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > maximum
        or _CONTROL_CHARACTER.search(value)
    ):
        raise ContractValidationError(
            f"{field_name} must be 1-{maximum} characters of trimmed text without control characters."
        )
    return value


def require_optional_text(value: Any, field_name: str, *, maximum: int = 512) -> str | None:
    if value is None:
        return None
    return require_text(value, field_name, maximum=maximum)


def parse_utc_timestamp(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str) or not _UTC_TIMESTAMP.fullmatch(value):
        raise ContractValidationError(
            f"{field_name} must be a canonical RFC 3339 UTC timestamp ending in Z."
        )
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContractValidationError(f"{field_name} is not a real calendar timestamp.") from exc


def require_time_window(start: Any, end: Any, start_name: str, end_name: str) -> None:
    if parse_utc_timestamp(end, end_name) < parse_utc_timestamp(start, start_name):
        raise ContractValidationError(f"{end_name} must not be earlier than {start_name}.")


def require_integer(
    value: Any,
    field_name: str,
    *,
    minimum: int = 0,
    maximum: int = 2_147_483_647,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ContractValidationError(
            f"{field_name} must be an integer between {minimum} and {maximum}."
        )
    return value


def require_boolean(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ContractValidationError(f"{field_name} must be boolean.")
    return value


def require_string_tuple(
    value: Any,
    field_name: str,
    *,
    identifiers: bool = False,
    maximum_items: int = 64,
) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or len(value) > maximum_items:
        raise ContractValidationError(
            f"{field_name} must be an array with at most {maximum_items} entries."
        )
    checked: list[str] = []
    for index, item in enumerate(value):
        if identifiers:
            checked.append(require_identifier(item, f"{field_name}[{index}]"))
        else:
            checked.append(require_text(item, f"{field_name}[{index}]", maximum=512))
    if len(checked) != len(set(checked)):
        raise ContractValidationError(f"{field_name} must not contain duplicates.")
    return tuple(checked)


def require_enum(enum_type: type[Enum], value: Any, field_name: str) -> Any:
    if isinstance(value, enum_type):
        return value
    if not isinstance(value, str):
        raise ContractValidationError(f"{field_name} must be a string enum value.")
    try:
        return enum_type(value)
    except ValueError as exc:
        supported = ", ".join(member.value for member in enum_type)
        raise ContractValidationError(
            f"{field_name} has unsupported value {value!r}; supported values: {supported}."
        ) from exc


def _freeze_json(value: Any, field_name: str, depth: int, budget: list[int]) -> JsonValue:
    budget[0] -= 1
    if budget[0] < 0:
        raise ContractValidationError(f"{field_name} exceeds the maximum JSON node count.")
    if depth > MAX_JSON_DEPTH:
        raise ContractValidationError(f"{field_name} exceeds the maximum JSON depth.")
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        if abs(value) > 9_007_199_254_740_991:
            raise ContractValidationError(f"{field_name} integer exceeds the portable JSON range.")
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ContractValidationError(f"{field_name} must not contain NaN or infinity.")
        return value
    if isinstance(value, str):
        if len(value) > MAX_JSON_STRING or _CONTROL_CHARACTER.search(value):
            raise ContractValidationError(f"{field_name} contains unsafe or oversized text.")
        return value
    if isinstance(value, Mapping):
        if len(value) > MAX_JSON_ITEMS:
            raise ContractValidationError(f"{field_name} contains too many object members.")
        frozen: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key or len(key) > 128 or _CONTROL_CHARACTER.search(key):
                raise ContractValidationError(f"{field_name} contains an invalid object key.")
            frozen[key] = _freeze_json(item, f"{field_name}.{key}", depth + 1, budget)
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        if len(value) > MAX_JSON_ITEMS:
            raise ContractValidationError(f"{field_name} contains too many array entries.")
        return tuple(
            _freeze_json(item, f"{field_name}[{index}]", depth + 1, budget)
            for index, item in enumerate(value)
        )
    raise ContractValidationError(f"{field_name} must contain only JSON data types.")


def require_json_mapping(value: Any, field_name: str) -> Mapping[str, JsonValue]:
    if not isinstance(value, Mapping):
        raise ContractValidationError(f"{field_name} must be a JSON object.")
    frozen = _freeze_json(value, field_name, 0, [MAX_JSON_NODES])
    if not isinstance(frozen, Mapping):  # Defensive typing guard.
        raise ContractValidationError(f"{field_name} must be a JSON object.")
    return frozen


def as_jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {key: as_jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [as_jsonable(item) for item in value]
    return value


def deterministic_json(data: Mapping[str, Any]) -> str:
    return json.dumps(
        as_jsonable(data),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def require_serialized_size(data: Mapping[str, Any], field_name: str) -> None:
    size = len(deterministic_json(data).encode("utf-8"))
    if size > MAX_SERIALIZED_BYTES:
        raise ContractValidationError(
            f"{field_name} exceeds the {MAX_SERIALIZED_BYTES}-byte serialized size limit."
        )


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractValidationError(f"Serialized input contains duplicate field {key!r}.")
        result[key] = value
    return result


def load_json_object(payload: str | bytes) -> Mapping[str, Any]:
    if not isinstance(payload, (str, bytes)):
        raise ContractValidationError("Serialized input must be text or UTF-8 bytes.")
    if isinstance(payload, bytes):
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ContractValidationError("Serialized bytes must be valid UTF-8.") from exc
    else:
        text = payload
    if len(text.encode("utf-8")) > MAX_SERIALIZED_BYTES:
        raise ContractValidationError(
            f"Serialized input exceeds the {MAX_SERIALIZED_BYTES}-byte limit."
        )
    try:
        value = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda constant: (_ for _ in ()).throw(
                ContractValidationError(f"Unsupported JSON constant: {constant}.")
            ),
        )
    except ContractValidationError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise ContractValidationError("Serialized input is not valid JSON.") from exc
    if not isinstance(value, Mapping):
        raise ContractValidationError("Serialized contract root must be a JSON object.")
    return value


def strict_contract_fields(
    data: Any,
    *,
    kind: str,
    fields: set[str],
) -> Mapping[str, Any]:
    if not isinstance(data, Mapping):
        raise ContractValidationError(f"{kind} must be a mapping.")
    if any(not isinstance(key, str) for key in data):
        raise ContractValidationError(f"{kind} field names must be strings.")
    expected = fields | {"schema_version", "kind"}
    actual = set(data)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing:
        raise ContractValidationError(f"{kind} is missing required fields: {missing}.")
    if unknown:
        raise ContractValidationError(f"{kind} contains unknown fields: {unknown}.")
    if data["schema_version"] != SCHEMA_VERSION:
        raise ContractValidationError(
            f"Unsupported schema_version {data['schema_version']!r}; expected {SCHEMA_VERSION!r}."
        )
    if data["kind"] != kind:
        raise ContractValidationError(
            f"Unsupported contract kind {data['kind']!r}; expected {kind!r}."
        )
    return data


def validate_header(schema_version: Any, actual_kind: Any, expected_kind: str) -> None:
    if schema_version != SCHEMA_VERSION:
        raise ContractValidationError(
            f"Unsupported schema_version {schema_version!r}; expected {SCHEMA_VERSION!r}."
        )
    if actual_kind != expected_kind:
        raise ContractValidationError(
            f"Unsupported contract kind {actual_kind!r}; expected {expected_kind!r}."
        )


class ContractMixin:
    """Serialization surface implemented by each explicit contract type."""

    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError

    def to_json(self) -> str:
        return deterministic_json(self.to_dict())
