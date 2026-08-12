# Enterprise pilot release checklist

- [ ] Main CI test, PostgreSQL and container jobs pass on the release commit.
- [ ] Tax owner approves rules, tolerance and ERP/invoice mappings.
- [ ] Security approves identity claims, secret storage, TLS, ingress rate limits and database roles.
- [ ] Alembic migration and rollback rehearsal pass against a production-like copy.
- [ ] Backup restore meets agreed RPO/RTO and audit-chain verification passes.
- [ ] Runtime database role is non-owner/NOBYPASSRLS and the direct SQL RLS attack test passes.
- [ ] Tenant isolation and preparer/reviewer separation are tested with customer identities.
- [ ] Monitoring routes readiness, 5xx, latency, database and backup alerts to named owners.
- [ ] Synthetic end-to-end filing workpaper is approved before real data is admitted.
- [ ] Oversize requests, empty/oversize batches and injected database failures pass negative tests.
- [ ] Scheduled `audit-verify` and backup jobs use separate least-privileged operational identities.
- [ ] OIDC issuer/audience/roles/tenant mappings and signing-key rotation are tested; no unapproved HMAC exception remains.
- [ ] PostgreSQL concurrent audit test proves the tenant chain has no fork.
- [ ] Encrypted restore runs into an empty, exact-revision PostgreSQL schema; audit chain and business lineage readback pass.
- [ ] `promtool` validates alert rules, and a test notification reaches each named owner in the deployment environment.
- [ ] The release commit has a retained SPDX image SBOM and no fixed Critical vulnerability blocked by CI.
- [ ] Candidate archive checksum and both GitHub attestations verify before a SemVer tag is approved.
- [ ] Tagged GHCR image resolves to the recorded immutable digest and provenance/SBOM attestations verify.
