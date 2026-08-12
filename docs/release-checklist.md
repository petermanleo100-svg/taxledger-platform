# Enterprise pilot release checklist

- [ ] Main CI test, PostgreSQL and container jobs pass on the release commit.
- [ ] Tax owner approves rules, tolerance and ERP/invoice mappings.
- [ ] Security approves identity claims, secret storage, TLS, ingress rate limits and database roles.
- [ ] Alembic migration and rollback rehearsal pass against a production-like copy.
- [ ] Backup restore meets agreed RPO/RTO and audit-chain verification passes.
- [ ] Tenant isolation and preparer/reviewer separation are tested with customer identities.
- [ ] Monitoring routes readiness, 5xx, latency, database and backup alerts to named owners.
- [ ] Synthetic end-to-end filing workpaper is approved before real data is admitted.
