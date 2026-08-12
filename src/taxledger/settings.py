from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    database_url: str
    jwt_secret: str
    jwt_issuer: str = "taxledger"
    jwt_audience: str = "taxledger-api"
    environment: str = "production"
    auto_create_schema: bool = False
    auth_mode: str = "hmac"
    oidc_jwks_url: str = ""
    allow_hmac_production: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        database_url = os.getenv("TAXLEDGER_DATABASE_URL", "")
        secret = os.getenv("TAXLEDGER_JWT_SECRET", "")
        environment = os.getenv("TAXLEDGER_ENV", "production")
        if not database_url:
            raise RuntimeError("TAXLEDGER_DATABASE_URL is required")
        auth_mode = os.getenv("TAXLEDGER_AUTH_MODE", "oidc" if environment == "production" else "hmac").lower()
        if auth_mode not in {"oidc", "hmac"}: raise RuntimeError("TAXLEDGER_AUTH_MODE must be oidc or hmac")
        allow_hmac = os.getenv("TAXLEDGER_ALLOW_HMAC_PRODUCTION", "false").lower() == "true"
        oidc_url = os.getenv("TAXLEDGER_OIDC_JWKS_URL", "")
        issuer = os.getenv("TAXLEDGER_JWT_ISSUER", "taxledger")
        audience = os.getenv("TAXLEDGER_JWT_AUDIENCE", "taxledger-api")
        if auth_mode == "hmac" and len(secret) < 32: raise RuntimeError("TAXLEDGER_JWT_SECRET must contain at least 32 characters")
        if auth_mode == "hmac" and environment == "production" and not allow_hmac: raise RuntimeError("production HMAC requires TAXLEDGER_ALLOW_HMAC_PRODUCTION=true")
        if auth_mode == "oidc" and (not issuer.startswith("https://") or not audience or not oidc_url.startswith("https://")): raise RuntimeError("OIDC production configuration requires HTTPS issuer/JWKS and audience")
        return cls(
            database_url=database_url,
            jwt_secret=secret,
            jwt_issuer=issuer,
            jwt_audience=audience,
            environment=environment,
            auto_create_schema=os.getenv("TAXLEDGER_AUTO_CREATE_SCHEMA", "false").lower() == "true",
            auth_mode=auth_mode, oidc_jwks_url=oidc_url, allow_hmac_production=allow_hmac,
        )
