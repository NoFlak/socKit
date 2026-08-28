# Runtime contracts (alpha)

The dependency-free `contracts/` package defines the untrusted data boundary
between tool discovery, execution intent, policy decisions, run observations, and
terminal results. It does not execute tools, evaluate policy, verify identity, or
grant authority.

## Input → Processing → Output

- **Input:** untrusted JSON or explicitly constructed Python values from a catalog
  publisher, caller, policy service, worker, or observer.
- **Processing:** select the expected contract type, strictly validate its version,
  kind, fields, types, identifiers, timestamps, bounds, duplicates, and lifecycle
  rules, then convert nested JSON data to immutable views.
- **Output:** a validated typed value or an explicit `ContractValidationError`.
  Serialization uses sorted keys and compact separators for deterministic JSON.

## Ownership and trust boundaries

| Contract | Producer/owner | Consumer | Security boundary |
|---|---|---|---|
| `ToolCatalog` | catalog publisher | discovery adapter, request builder | Metadata describes capability; it never authorizes execution. Restricted action modes must declare that authorization is required. |
| `ExecutionRequest` | authenticated intake adapter (future) | policy service | Identity, authorization, scope, provenance, and arguments are untrusted claims until independently verified. |
| `PolicyDecision` | policy service (future) | dispatcher | Decisions are separate from detection signals and results. A serialized allow record is not a capability or execution token. |
| `RunEvent` | isolated worker/event adapter (future) | lifecycle store, UI, audit | Events and metrics are observations only; they cannot change policy. |
| `ExecutionResult` | isolated worker/result adapter (future) | result store, UI, audit | Worker success/failure is not a policy decision. Policy denial is represented only by `PolicyDecision` plus a denied lifecycle. |
| `RunLifecycle` | lifecycle store (future) | dispatcher, UI, audit | Only allow-listed, contiguous, monotonic transitions are valid; terminal states cannot transition. |

`Provenance` records who *claims* to have produced an object and when it was
observed. It is not a trust source. Signature verification, authenticated service
identity, durable authorization, and clock assurance are outside this contract
package.

## Validation and safe usage

- Parse with the explicit expected class, for example
  `ExecutionRequest.from_json(payload)`. There is intentionally no polymorphic
  deserializer that imports or constructs a type named by untrusted input.
- Unknown/missing fields, duplicate JSON keys, malformed UTF-8/JSON, unsupported
  schema versions/kinds, unsafe identifiers, invalid enums, non-finite numbers,
  deep/large values, and inconsistent result states fail closed.
- `requested_at`/`expires_at`, `decided_at`/`expires_at`, and catalog validity are
  explicit. Call `is_fresh(at)` with a trusted, caller-selected UTC time. Parsing
  alone does not assert freshness.
- `request_id` and `idempotency_key` support replay controls.
  `validate_unique_requests()` rejects duplicates in one intake batch, but a
  durable, tenant-scoped replay store remains the intake service's responsibility.
- `validate_run_event_stream()` rejects duplicate event IDs, gaps/reordering,
  cross-run correlation, timestamp rollback, and invalid state transitions.
- Store raw rejected input only under the repository's redaction and retention
  policy; validation errors should be logged without secrets or full payloads.

## Lifecycle

```text
pending-policy ──> denied
       │
       └──> queued ──> running ──> succeeded
              │           ├──────> failed
              │           └──────> cancelled
              ├──────────> failed
              └──────────> cancelled
```

`denied`, `succeeded`, `failed`, and `cancelled` are terminal. A denial is
fail-closed and does not imply a worker ran.

## Alpha compatibility

The schema identifier is `sockit.runtime/v0alpha1`. The recovery checkpoint's
unmerged `1.0` draft is intentionally not accepted: it lacked strict
deserialization, bounded values, replay fields, and lifecycle validation. The gate
branch has no contract consumers, so this extraction changes no current execution
behavior.

Before 1.0, breaking changes are allowed only when the schema identifier changes,
tests and this document are updated, and consumers migrate explicitly. Unknown
versions must remain rejected rather than silently downgraded.
