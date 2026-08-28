## Goal and scope

- [ ] The intended outcome and affected subsystem are stated clearly.
- [ ] Unrelated behavior and generated artifacts are excluded.
- [ ] Existing CLI and legacy-tool compatibility is preserved or explicitly documented.

## Security review

- [ ] Untrusted inputs are validated and allowlisted where applicable.
- [ ] Identity, provenance, freshness, detection, and authorization are not conflated.
- [ ] No credentials, tokens, secrets, or unnecessarily sensitive output are committed or logged.
- [ ] Failure behavior is explicit, observable, and deny-by-default.
- [ ] New execution, offensive, privileged, or state-changing capability is disclosed and tested.

## Validation and release impact

- [ ] The required repository gate passes.
- [ ] Relevant positive, negative, malformed-input, and unauthorized cases are covered.
- [ ] Capability state, documentation, and alpha-version impact match actual behavior.
