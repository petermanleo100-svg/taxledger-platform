# Production runbook

## Go-live prerequisites

- Use managed PostgreSQL with encryption, point-in-time recovery and separate application/migration identities.
- Store `TAXLEDGER_JWT_SECRET` in a secret manager; rotate it before production and after suspected exposure.
- Terminate TLS at the ingress, restrict `/metrics`, and integrate centralized logs and alerting.
- Run schema migration and restore rehearsal in staging before traffic is enabled.

## Startup and verification

1. Copy `.env.example` to an environment-specific secret source; never commit real values.
2. Provision distinct migration-owner and runtime credentials. For local Compose, use a fresh volume: runtime-role bootstrap runs only on initial database creation.
3. Run `taxledger-operations preflight` with the runtime identity; require secret-free JSON with `valid: true`.
4. Start with `docker compose up -d --build`; Compose migrates as the owner and repeats preflight before the API starts.
5. Require `/health/ready` to return 200 before routing traffic.
6. Validate an authenticated ingest, reconciliation, preparer/reviewer separation and tenant-isolation test.

## Operational objectives

- Availability target: 99.9% monthly for the API after production baselining.
- Initial recovery objectives: RPO 15 minutes, RTO 60 minutes; customer infrastructure must prove these by drill.
- Alert on readiness failure, elevated 5xx rate, p95 latency regression, database saturation and failed backups.

## Incident controls

Revoke affected tokens, preserve audit tables and database snapshots, record the incident timeline, verify the audit chain, restore into an isolated database, then obtain business owner approval before resuming filing workflows.

Application backup exports use `taxledger.backup` with a secret-manager supplied 32-byte base64 key. Restores require an empty database already migrated to the exact application Alembic revision; the restore path never creates or upgrades schema implicitly and verifies the recovered audit chain. PostgreSQL CI migrates a clean schema, restores encrypted data and reads back business lineage. This portable logical backup complements, but does not replace, managed PostgreSQL PITR; rehearse both quarterly.

Use `taxledger-operations` for controlled backup, restore and audit verification. Set `TAXLEDGER_TEXTFILE_DIR` to a Node Exporter textfile-collector directory (or equivalent). Each command atomically writes its own bounded-label `.prom` file and preserves the last-success timestamp after a failed attempt. Schedule `backup-create` and `audit-verify`; alert on non-zero exit, `operation_success == 0`, `node_textfile_scrape_error == 1`, or backup age beyond the 15-minute RPO. An unwritable or unreadable metrics directory is a deployment failure. The API caps bodies at 2 MiB and ledger batches at 1000 rows; tune ingress limits to the same or lower value.

Load `deploy/prometheus/taxledger-alerts.yml` into the approved Prometheus-compatible backend and map `owner=platform-operations` plus severity to named receivers. CI validates syntax and executes synthetic firing scenarios for readiness, 5xx rate, p95 latency, scheduled-operation failure and stale backup with `promtool`; receiver credentials and a real test notification remain environment acceptance evidence. CI runs `pip-audit`, retains an SPDX JSON image SBOM for 30 days, and blocks image vulnerabilities that are High/Critical with a known fix. Unfixed findings require explicit release risk review rather than being described as remediated.

The `release-image` workflow has two modes. Manual dispatch creates a 14-day candidate image archive, checksum and SBOM, then records GitHub provenance and SBOM attestations without publishing a registry image. A `vX.Y.Z` tag publishes only that immutable commit to `ghcr.io/<owner>/taxledger-platform`, records the registry digest, and attaches provenance plus SBOM attestations. Before creating a tag, complete the release checklist on `main`; after publication, verify with `gh attestation verify oci://ghcr.io/<owner>/taxledger-platform:vX.Y.Z -R <owner>/taxledger-platform`.

The request-serving PostgreSQL identity must be `NOSUPERUSER NOBYPASSRLS` and must not own tables. Migrations run as a separate owner. The application sets `app.tenant_id` transaction-locally and forced RLS supplies database-level defense in depth.

Before approving a release, an administrator must run `GH_TOKEN=$(gh auth token) GITHUB_REPOSITORY=petermanleo100-svg/taxledger-platform EXPECTED_REQUIRED_CHECKS=test,postgres,container,compose-smoke,analyze python scripts/verify_github_governance.py`. The verifier fails unless `main` protection, GitHub-Actions-bound checks, secret scanning/push protection and Dependabot security controls match the documented state. It intentionally runs outside Actions: the default workflow token cannot read administration settings, and storing a broad administrator PAT solely for this check would increase credential risk.

Production authentication defaults to `TAXLEDGER_AUTH_MODE=oidc`. Configure HTTPS issuer/JWKS URL and exact audience; signing keys are cached for five minutes and refreshed by `kid`. The HMAC mode is a documented pilot exception only and requires `TAXLEDGER_ALLOW_HMAC_PRODUCTION=true`; record its owner, expiry and migration date. Tax writes take a tenant-scoped PostgreSQL advisory transaction lock before extending the audit chain.

This repository is deployable for an enterprise pilot. Production tax use still requires customer security review, authoritative tax-rule validation, data mapping sign-off and environment-specific capacity testing.
