# Artifact Store Phase 2 Prep

Goal for next iteration: enable `utils.artifact_store.ArtifactStore` to perform real MinIO/S3 uploads when credentials are provided while maintaining the current local fallback.

## Open Questions
- Which client library is preferred? (default assumption: `boto3` so we can target AWS-compatible endpoints including MinIO).
- Should uploads be synchronous or queued? (current plan: synchronous to keep implementation simple).
- How should credentials be injected in CI/local dev? (environment variables vs. config file).

## Proposed Implementation Outline
1. Detect remote mode (`mode in {"s3", "minio"}`) and lazily initialize a boto3 client.
2. Mirror the existing local write for transparency, then attempt upload with retry/backoff.
3. Support optional TLS configuration (`SOCKIT_ARTIFACT_VERIFY_SSL`, custom CA bundle).
4. Expand logging to include bucket/key, response metadata, and error handling paths.
5. Provide unit tests using moto/local stubs to avoid real network dependencies.

## Pre-requisites
- Confirm adding `boto3` to `requirements.txt` is acceptable.
- Determine whether secrets will be available during CI runs (if not, default to dry-run log messages).
- Decide if artifact retention policy is required (e.g., prune local mirrors after upload).

This note captures the prep work so we can move straight into implementation when ready.
