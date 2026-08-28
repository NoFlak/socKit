"""Run lifecycle snapshot and deterministic transition validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import islice
from typing import Any, Iterable

from .common import (
    SCHEMA_VERSION,
    ContractMixin,
    ContractValidationError,
    RunState,
    load_json_object,
    parse_utc_timestamp,
    require_enum,
    require_identifier,
    require_integer,
    require_serialized_size,
    strict_contract_fields,
    validate_header,
)
from .events import RunEvent


TERMINAL_STATES = frozenset(
    {RunState.DENIED, RunState.SUCCEEDED, RunState.FAILED, RunState.CANCELLED}
)

ALLOWED_TRANSITIONS: dict[RunState, frozenset[RunState]] = {
    RunState.PENDING_POLICY: frozenset({RunState.DENIED, RunState.QUEUED}),
    RunState.DENIED: frozenset(),
    RunState.QUEUED: frozenset({RunState.RUNNING, RunState.FAILED, RunState.CANCELLED}),
    RunState.RUNNING: frozenset(
        {RunState.SUCCEEDED, RunState.FAILED, RunState.CANCELLED}
    ),
    RunState.SUCCEEDED: frozenset(),
    RunState.FAILED: frozenset(),
    RunState.CANCELLED: frozenset(),
}


@dataclass(frozen=True)
class RunLifecycle(ContractMixin):
    run_id: str
    request_id: str
    tool_id: str
    state: RunState
    sequence: int
    updated_at: str
    schema_version: str = SCHEMA_VERSION
    kind: str = field(default="run_lifecycle", init=True)

    def __post_init__(self) -> None:
        validate_header(self.schema_version, self.kind, "run_lifecycle")
        for name in ("run_id", "request_id", "tool_id"):
            require_identifier(getattr(self, name), name)
        object.__setattr__(self, "state", require_enum(RunState, self.state, "state"))
        require_integer(self.sequence, "sequence")
        parse_utc_timestamp(self.updated_at, "updated_at")
        if self.sequence == 0 and self.state is not RunState.PENDING_POLICY:
            raise ContractValidationError("Lifecycle sequence 0 must be pending-policy.")
        if self.sequence > 0 and self.state is RunState.PENDING_POLICY:
            raise ContractValidationError("pending-policy is valid only at lifecycle sequence 0.")
        require_serialized_size(self.to_dict(), "run_lifecycle")

    @property
    def terminal(self) -> bool:
        return self.state in TERMINAL_STATES

    def transition(self, state: RunState | str, *, sequence: int, updated_at: str) -> "RunLifecycle":
        next_state = require_enum(RunState, state, "state")
        if next_state not in ALLOWED_TRANSITIONS[self.state]:
            raise ContractValidationError(
                f"Invalid run transition: {self.state.value} -> {next_state.value}."
            )
        if sequence != self.sequence + 1:
            raise ContractValidationError("Lifecycle sequence must increase by exactly one.")
        if parse_utc_timestamp(updated_at, "updated_at") < parse_utc_timestamp(
            self.updated_at, "current.updated_at"
        ):
            raise ContractValidationError("Lifecycle updated_at must be monotonic.")
        return RunLifecycle(
            run_id=self.run_id,
            request_id=self.request_id,
            tool_id=self.tool_id,
            state=next_state,
            sequence=sequence,
            updated_at=updated_at,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "kind": self.kind,
            "run_id": self.run_id,
            "request_id": self.request_id,
            "tool_id": self.tool_id,
            "state": self.state.value,
            "sequence": self.sequence,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Any) -> "RunLifecycle":
        checked = strict_contract_fields(
            data,
            kind="run_lifecycle",
            fields={"run_id", "request_id", "tool_id", "state", "sequence", "updated_at"},
        )
        return cls(
            run_id=checked["run_id"],
            request_id=checked["request_id"],
            tool_id=checked["tool_id"],
            state=checked["state"],
            sequence=checked["sequence"],
            updated_at=checked["updated_at"],
            schema_version=checked["schema_version"],
            kind=checked["kind"],
        )

    @classmethod
    def from_json(cls, payload: str | bytes) -> "RunLifecycle":
        return cls.from_dict(load_json_object(payload))


def validate_run_event_stream(events: Iterable[RunEvent]) -> RunLifecycle:
    """Validate a complete, ordered event stream and return its final snapshot."""

    if isinstance(events, (str, bytes)):
        raise ContractValidationError("events must be an iterable of RunEvent values.")
    try:
        event_list = list(islice(iter(events), 10_001))
    except TypeError as exc:
        raise ContractValidationError("events must be an iterable of RunEvent values.") from exc
    if not event_list or len(event_list) > 10_000:
        raise ContractValidationError("events must contain 1-10000 RunEvent values.")
    if any(not isinstance(event, RunEvent) for event in event_list):
        raise ContractValidationError("events must contain only RunEvent values.")
    event_ids = [event.event_id for event in event_list]
    if len(event_ids) != len(set(event_ids)):
        raise ContractValidationError("events contain a duplicate event_id.")

    first = event_list[0]
    if first.sequence != 0 or first.state is not RunState.PENDING_POLICY:
        raise ContractValidationError(
            "A complete event stream must begin at sequence 0 in pending-policy."
        )
    lifecycle = RunLifecycle(
        run_id=first.run_id,
        request_id=first.request_id,
        tool_id=first.tool_id,
        state=first.state,
        sequence=first.sequence,
        updated_at=first.occurred_at,
    )
    for event in event_list[1:]:
        if (event.run_id, event.request_id, event.tool_id) != (
            lifecycle.run_id,
            lifecycle.request_id,
            lifecycle.tool_id,
        ):
            raise ContractValidationError("events must use consistent run, request, and tool IDs.")
        lifecycle = lifecycle.transition(
            event.state, sequence=event.sequence, updated_at=event.occurred_at
        )
    return lifecycle
