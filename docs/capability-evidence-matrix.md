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
| Backup and recovery | AES-256-GCM envelope, empty-target restore, audit-chain verification | wrong-key, non-empty target and business restore tests |
| Runtime abuse controls | 2 MiB body/1000-row batch limits and bounded fields | oversize/empty/invalid payload tests |
| Safe failure boundary | centralized SQLAlchemy 503 without internal detail | injected database failure leak test |
| Operability | structured request log, admin integrity API and operations CLI | authorization/integrity/API tests |
