# Production runbook

## Go-live prerequisites

- Use managed PostgreSQL with encryption, point-in-time recovery and separate application/migration identities.
- Store `TAXLEDGER_JWT_SECRET` in a secret manager; rotate it before production and after suspected exposure.
- Terminate TLS at the ingress, restrict `/metrics`, and integrate centralized logs and alerting.
- Run schema migration and restore rehearsal in staging before traffic is enabled.

## Startup and verification

1. Copy `.env.example` to an environment-specific secret source; never commit real values.
2. Start with `docker compose up -d --build`.
3. Require `/health/ready` to return 200 before routing traffic.
4. Validate an authenticated ingest, reconciliation, preparer/reviewer separation and tenant-isolation test.

## Operational objectives

- Availability target: 99.9% monthly for the API after production baselining.
- Initial recovery objectives: RPO 15 minutes, RTO 60 minutes; customer infrastructure must prove these by drill.
- Alert on readiness failure, elevated 5xx rate, p95 latency regression, database saturation and failed backups.

## Incident controls

Revoke affected tokens, preserve audit tables and database snapshots, record the incident timeline, verify the audit chain, restore into an isolated database, then obtain business owner approval before resuming filing workflows.

Application backup exports use `taxledger.backup` with a secret-manager supplied 32-byte base64 key. Restores deliberately refuse non-empty targets and verify the recovered audit chain. This portable logical backup complements, but does not replace, managed PostgreSQL PITR; rehearse both quarterly.

Use `taxledger-operations` for controlled backup, restore and audit verification. Schedule `audit-verify` and alert on a non-zero exit. The API caps bodies at 2 MiB and ledger batches at 1000 rows; tune ingress limits to the same or lower value. Access logs are structured JSON and include the request ID returned to callers.

The request-serving PostgreSQL identity must be `NOSUPERUSER NOBYPASSRLS` and must not own tables. Migrations run as a separate owner. The application sets `app.tenant_id` transaction-locally and forced RLS supplies database-level defense in depth.

Production authentication defaults to `TAXLEDGER_AUTH_MODE=oidc`. Configure HTTPS issuer/JWKS URL and exact audience; signing keys are cached for five minutes and refreshed by `kid`. The HMAC mode is a documented pilot exception only and requires `TAXLEDGER_ALLOW_HMAC_PRODUCTION=true`; record its owner, expiry and migration date. Tax writes take a tenant-scoped PostgreSQL advisory transaction lock before extending the audit chain.

This repository is deployable for an enterprise pilot. Production tax use still requires customer security review, authoritative tax-rule validation, data mapping sign-off and environment-specific capacity testing.
