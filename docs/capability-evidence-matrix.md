# Capability–evidence matrix

| Capability | Implementation | Evidence |
|---|---|---|
| Exact tax ledger | Decimal/Numeric ledger entries | precision and tenant test |
| Field lineage | source, mapping, transformation and content hash | end-to-end lineage assertion |
| VAT reconciliation | ledger/invoice/return comparison with tolerance | matched and exception workflows |
| Filing governance | versioned workpaper and independent review | four-eyes test |
| Deployability | FastAPI, non-root image and CI | API test and container job |
| Auth and tenant binding | Signed JWT roles and token tenant context | scope and forged-tenant API tests |
| Operations | request ID, metrics, probes and security headers | operations test |
| Schema lifecycle | Alembic baseline | upgrade/downgrade round-trip test |
| Enterprise pilot | PostgreSQL Compose hardening and runbook | PostgreSQL and container CI jobs |
| Database tenant defense | PostgreSQL FORCE RLS and transaction tenant context | direct SQL cross-tenant attack test |
| Backup and recovery | AES-256-GCM envelope, exact Alembic-revision/empty-target gates and audit-chain verification | wrong-key/unmigrated-target negatives plus PostgreSQL clean-schema restore and business readback |
| Runtime abuse controls | 2 MiB body/1000-row batch limits and bounded fields | oversize/empty/invalid payload tests |
| Safe failure boundary | centralized SQLAlchemy 503 without internal detail | injected database failure leak test |
| Operability | structured request log, admin integrity API and operations CLI | authorization/integrity/API tests |
| Enterprise identity | OIDC/JWKS RS256/ES256, issuer/audience/expiry/role/tenant validation and 5-minute key cache | signed-token negative matrix |
| Auth downgrade control | production defaults OIDC; HMAC requires explicit exception | configuration fail-closed tests |
| Concurrent audit integrity | per-tenant PostgreSQL advisory transaction lock | 8-worker/24-event no-fork integration test |
| Actionable observability | versioned Prometheus 5xx, p95 latency and readiness alerts | `promtool check rules` runs in CI; routing remains deployment-specific |
| Container supply-chain evidence | SPDX JSON SBOM for the built image and fixed-critical vulnerability gate | commit-pinned SBOM/scan actions and retained CI artifact |
| Verifiable image release path | manual candidate archive with checksum/SBOM/attestations; SemVer tags publish digest-addressed GHCR images with provenance and SBOM attestations | candidate workflow run and `gh attestation verify`; formal image publication remains tag-controlled |
