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

This repository is deployable for an enterprise pilot. Production tax use still requires customer security review, authoritative tax-rule validation, data mapping sign-off and environment-specific capacity testing.
