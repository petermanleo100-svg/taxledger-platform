# Threat model

| Asset | Threat | Implemented control | Deployment responsibility |
|---|---|---|---|
| Tenant tax data | forged tenant header / IDOR | tenant comes from signed JWT; every query includes tenant scope | IdP claim governance and negative authorization test |
| Filing approval | preparer self-approval | independent reviewer check and role scopes | access review and leaver process |
| Amount integrity | binary rounding or altered source | Decimal/Numeric plus source/content hashes | authoritative mapping and reconciliation sign-off |
| Audit evidence | record mutation | per-tenant chained hashes | immutable backup/PITR and restricted DB admin |
| API identity | forged token, stale key or auth downgrade | OIDC/JWKS algorithm allowlist, issuer/audience/expiry/role/tenant checks; explicit HMAC exception | IdP group governance and emergency rotation drill |
| API resources | malformed/oversize payload, clickjacking | forbidden extra fields, body/batch limits, security headers | TLS, WAF/rate limit and centralized alerting |
| Audit chain | concurrent writers create forks | tenant advisory transaction lock and chain verifier | alert on verifier failure and restrict direct writers |
| Availability | database outage or corrupt release | readiness gate, migration tests, restart policy | HA database, capacity test and restore drill |

Residual risk: application-level tenant predicates are verified in tests, but production database row-level security is an additional recommended defense. Legal filing correctness is outside the software-only assurance boundary.
