# Security policy

Do not open a public issue for a suspected vulnerability. Report it privately to the repository owner with affected version, reproduction steps, impact and any temporary mitigation. Do not include real taxpayer, invoice, credential or client data.

Supported security baseline: the latest `main` commit only. Secrets must be supplied by a secret manager, production traffic must use TLS, database identities must be least-privileged, and `/metrics` must be private. The bundled HS256 verifier is suitable for a controlled pilot; production federation should use the enterprise identity provider and its managed key-rotation policy.

Release owners must assess authentication bypass, cross-tenant access, reviewer self-approval, SQL injection, malicious payload size, sensitive logging, backup exposure and dependency advisories before production approval.
