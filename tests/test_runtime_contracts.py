import itertools
import json

import pytest

from contracts import (
    ActionMode,
    CapabilityState,
    ContractValidationError,
    ExecutionError,
    ExecutionOutcome,
    ExecutionRequest,
    ExecutionResult,
    PolicyDecision,
    PolicyOutcome,
    Provenance,
    RunEvent,
    RunLifecycle,
    RunState,
    ToolCatalog,
    ToolDefinition,
    validate_run_event_stream,
    validate_unique_requests,
)


T0 = "2026-08-27T20:00:00Z"
T1 = "2026-08-27T20:01:00Z"
T2 = "2026-08-27T20:02:00Z"
T3 = "2026-08-27T20:03:00Z"


def provenance() -> Provenance:
    return Provenance(
        source_id="test.adapter",
        source_instance_id="adapter-1",
        observed_at=T0,
        correlation_id="trace-1",
    )


def tool(**overrides) -> ToolDefinition:
    values = {
        "tool_id": "network.tcp_scan",
        "tool_version": 1,
        "label": "TCP port scan",
        "description": "Observe approved TCP ports on an explicitly scoped asset.",
        "action_mode": ActionMode.ACTIVE_READ_ONLY,
        "capability_state": CapabilityState.OPERATIONAL,
        "scope_types": ("asset",),
        "platforms": ("windows", "linux"),
        "privilege_required": "user",
        "authorization_required": True,
        "preview_supported": True,
        "timeout_seconds": 60,
        "cancel_supported": True,
    }
    values.update(overrides)
    return ToolDefinition(**values)


def catalog(**overrides) -> ToolCatalog:
    values = {
        "catalog_id": "catalog-1",
        "revision": 1,
        "published_at": T0,
        "valid_until": T3,
        "provenance": provenance(),
        "tools": (tool(),),
    }
    values.update(overrides)
    return ToolCatalog(**values)


def request(**overrides) -> ExecutionRequest:
    values = {
        "request_id": "request-1",
        "idempotency_key": "intake-1",
        "tool_id": "network.tcp_scan",
        "requested_at": T0,
        "expires_at": T2,
        "provenance": provenance(),
        "arguments": {"ports": [22, 443], "dry_run": True},
        "scope": ("asset-1",),
        "operator_id": None,
        "tenant_id": "tenant-1",
        "authorization_reference": None,
    }
    values.update(overrides)
    return ExecutionRequest(**values)


def denied_decision(**overrides) -> PolicyDecision:
    values = {
        "decision_id": "decision-1",
        "request_id": "request-1",
        "tool_id": "network.tcp_scan",
        "outcome": PolicyOutcome.DENY,
        "reasons": ("verified authorization is unavailable",),
        "policy_version": "deny-unverified-v1",
        "decided_at": T1,
        "expires_at": T2,
        "decided_scope": ("asset-1",),
        "authorization_reference": None,
        "provenance": provenance(),
    }
    values.update(overrides)
    return PolicyDecision(**values)


def event(sequence: int, state: RunState, occurred_at: str, **overrides) -> RunEvent:
    values = {
        "event_id": f"event-{sequence}",
        "run_id": "run-1",
        "request_id": "request-1",
        "tool_id": "network.tcp_scan",
        "sequence": sequence,
        "state": state,
        "occurred_at": occurred_at,
        "summary": f"Run entered {state.value}.",
        "metrics": {},
        "provenance": provenance(),
    }
    values.update(overrides)
    return RunEvent(**values)


def failed_result(**overrides) -> ExecutionResult:
    values = {
        "result_id": "result-1",
        "run_id": "run-1",
        "request_id": "request-1",
        "tool_id": "network.tcp_scan",
        "outcome": ExecutionOutcome.FAILED,
        "started_at": T1,
        "completed_at": T2,
        "summary": "The worker failed without completing the authorized observation.",
        "exit_code": 2,
        "error": ExecutionError(
            code="worker-error",
            message="The isolated worker returned an error.",
            retryable=False,
        ),
        "artifact_references": ("artifact://run-1/stderr",),
        "provenance": provenance(),
    }
    values.update(overrides)
    return ExecutionResult(**values)


@pytest.mark.parametrize(
    "value, parser",
    [
        (catalog(), ToolCatalog.from_json),
        (request(), ExecutionRequest.from_json),
        (denied_decision(), PolicyDecision.from_json),
        (event(0, RunState.PENDING_POLICY, T0), RunEvent.from_json),
        (failed_result(), ExecutionResult.from_json),
        (
            RunLifecycle(
                run_id="run-1",
                request_id="request-1",
                tool_id="network.tcp_scan",
                state=RunState.PENDING_POLICY,
                sequence=0,
                updated_at=T0,
            ),
            RunLifecycle.from_json,
        ),
    ],
)
def test_valid_contracts_round_trip_deterministically(value, parser):
    encoded = value.to_json()

    assert parser(encoded) == value
    assert parser(encoded).to_json() == encoded
    assert encoded == json.dumps(value.to_dict(), sort_keys=True, separators=(",", ":"))


def test_missing_required_and_unknown_fields_fail_closed():
    data = request().to_dict()
    del data["tool_id"]
    with pytest.raises(ContractValidationError, match="missing required"):
        ExecutionRequest.from_dict(data)

    data = request().to_dict()
    data["trusted"] = True
    with pytest.raises(ContractValidationError, match="unknown fields"):
        ExecutionRequest.from_dict(data)

    data = request().to_dict()
    data[1] = "non-string field name"
    with pytest.raises(ContractValidationError, match="field names must be strings"):
        ExecutionRequest.from_dict(data)


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("schema_version", "sockit.runtime/v9", "Unsupported schema_version"),
        ("kind", "python.class.path", "Unsupported contract kind"),
    ],
)
def test_unknown_schema_version_and_kind_are_rejected(field, value, message):
    data = request().to_dict()
    data[field] = value

    with pytest.raises(ContractValidationError, match=message):
        ExecutionRequest.from_dict(data)


def test_invalid_types_enums_identifiers_and_catalog_security_invariants_are_rejected():
    with pytest.raises(ContractValidationError, match="authorization_required must be boolean"):
        tool(authorization_required="yes")
    with pytest.raises(ContractValidationError, match="unsupported value"):
        tool(action_mode="execute-anything")
    with pytest.raises(ContractValidationError, match="stable identifier"):
        request(request_id="../../unsafe")
    with pytest.raises(ContractValidationError, match="must declare authorization_required"):
        tool(authorization_required=False)


def test_catalog_rejects_duplicate_tool_identifiers_and_invalid_freshness_window():
    with pytest.raises(ContractValidationError, match="duplicate tool_id"):
        catalog(tools=(tool(), tool(label="Duplicate label")))
    with pytest.raises(ContractValidationError, match="valid_until must not be earlier"):
        catalog(published_at=T2, valid_until=T1)


def test_freshness_is_explicit_and_uses_a_caller_supplied_time():
    assert request().is_fresh(T1) is True
    assert request().is_fresh(T3) is False
    assert catalog().is_fresh(T2) is True
    assert denied_decision().is_fresh(T3) is False


def test_request_arguments_are_bounded_json_and_copied_from_mutable_input():
    supplied = {"nested": {"ports": [22]}}
    frozen_request = request(arguments=supplied)
    supplied["nested"]["ports"].append(443)

    assert frozen_request.to_dict()["arguments"] == {"nested": {"ports": [22]}}
    with pytest.raises(ContractValidationError, match="JSON data types"):
        request(arguments={"callable": object()})
    too_deep = {"leaf": 1}
    for index in range(10):
        too_deep = {f"level-{index}": too_deep}
    with pytest.raises(ContractValidationError, match="maximum JSON depth"):
        request(arguments=too_deep)
    too_many_nodes = {f"key-{index}": list(range(16)) for index in range(128)}
    with pytest.raises(ContractValidationError, match="maximum JSON node count"):
        request(arguments=too_many_nodes)
    oversized = {f"key-{index}": "x" * 4_096 for index in range(16)}
    with pytest.raises(ContractValidationError, match="serialized size limit"):
        request(arguments=oversized)


def test_batch_validation_rejects_duplicate_request_and_replay_identifiers():
    with pytest.raises(ContractValidationError, match="duplicate request_id"):
        validate_unique_requests((request(), request(idempotency_key="intake-2")))
    with pytest.raises(ContractValidationError, match="duplicate replay key"):
        validate_unique_requests((request(), request(request_id="request-2")))


def test_policy_denial_is_explicit_and_cannot_be_empty():
    decision = denied_decision()

    assert decision.outcome is PolicyOutcome.DENY
    assert decision.authorization_reference is None
    assert decision.reasons == ("verified authorization is unavailable",)
    with pytest.raises(ContractValidationError, match="must include at least one reason"):
        denied_decision(reasons=())


def test_execution_failure_is_explicit_and_not_a_policy_denial():
    result = failed_result()

    assert result.outcome is ExecutionOutcome.FAILED
    assert result.error.code == "worker-error"
    with pytest.raises(ContractValidationError, match="must include an error"):
        failed_result(error=None)
    with pytest.raises(ContractValidationError, match="zero or null exit_code"):
        failed_result(outcome=ExecutionOutcome.SUCCEEDED, error=None, exit_code=1)
    with pytest.raises(ContractValidationError, match="unsupported value"):
        failed_result(outcome="denied")


@pytest.mark.parametrize(
    "payload,message",
    [
        ("not-json", "not valid JSON"),
        ("[]", "root must be a JSON object"),
        ('{"kind":"execution_request","kind":"run_event"}', "duplicate field"),
        ('{"value":NaN}', "Unsupported JSON constant"),
        (b"\xff", "valid UTF-8"),
    ],
)
def test_untrusted_malformed_serialized_input_is_rejected(payload, message):
    with pytest.raises(ContractValidationError, match=message):
        ExecutionRequest.from_json(payload)


def test_oversized_serialized_input_is_rejected_before_deserialization():
    with pytest.raises(ContractValidationError, match="byte limit"):
        ExecutionRequest.from_json("{" + ("x" * 70_000) + "}")


def test_valid_run_event_stream_builds_terminal_lifecycle():
    events = (
        event(0, RunState.PENDING_POLICY, T0),
        event(1, RunState.QUEUED, T1),
        event(2, RunState.RUNNING, T2),
        event(3, RunState.SUCCEEDED, T3),
    )

    lifecycle = validate_run_event_stream(events)

    assert lifecycle.state is RunState.SUCCEEDED
    assert lifecycle.sequence == 3
    assert lifecycle.terminal is True


def test_run_stream_rejects_duplicates_bad_sequences_and_cross_run_data():
    duplicate = event(1, RunState.QUEUED, T1, event_id="event-0")
    with pytest.raises(ContractValidationError, match="duplicate event_id"):
        validate_run_event_stream((event(0, RunState.PENDING_POLICY, T0), duplicate))
    with pytest.raises(ContractValidationError, match="increase by exactly one"):
        validate_run_event_stream(
            (event(0, RunState.PENDING_POLICY, T0), event(2, RunState.QUEUED, T1))
        )
    with pytest.raises(ContractValidationError, match="consistent run"):
        validate_run_event_stream(
            (
                event(0, RunState.PENDING_POLICY, T0),
                event(1, RunState.QUEUED, T1, request_id="request-other"),
            )
        )


def test_run_stream_bounds_iterables_before_materializing_them():
    with pytest.raises(ContractValidationError, match="1-10000"):
        validate_run_event_stream(itertools.repeat(event(0, RunState.PENDING_POLICY, T0)))


def test_invalid_and_terminal_lifecycle_transitions_are_rejected():
    lifecycle = RunLifecycle(
        run_id="run-1",
        request_id="request-1",
        tool_id="network.tcp_scan",
        state=RunState.PENDING_POLICY,
        sequence=0,
        updated_at=T0,
    )
    with pytest.raises(ContractValidationError, match="pending-policy -> running"):
        lifecycle.transition(RunState.RUNNING, sequence=1, updated_at=T1)

    denied = lifecycle.transition(RunState.DENIED, sequence=1, updated_at=T1)
    with pytest.raises(ContractValidationError, match="denied -> queued"):
        denied.transition(RunState.QUEUED, sequence=2, updated_at=T2)


def test_lifecycle_rejects_non_monotonic_time():
    lifecycle = RunLifecycle(
        run_id="run-1",
        request_id="request-1",
        tool_id="network.tcp_scan",
        state=RunState.PENDING_POLICY,
        sequence=0,
        updated_at=T1,
    )
    with pytest.raises(ContractValidationError, match="must be monotonic"):
        lifecycle.transition(RunState.QUEUED, sequence=1, updated_at=T0)
