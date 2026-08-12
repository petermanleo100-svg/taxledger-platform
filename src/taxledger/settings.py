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

    @classmethod
    def from_env(cls) -> "Settings":
        database_url = os.getenv("TAXLEDGER_DATABASE_URL", "")
        secret = os.getenv("TAXLEDGER_JWT_SECRET", "")
        environment = os.getenv("TAXLEDGER_ENV", "production")
        if not database_url:
            raise RuntimeError("TAXLEDGER_DATABASE_URL is required")
        if len(secret) < 32:
            raise RuntimeError("TAXLEDGER_JWT_SECRET must contain at least 32 characters")
        return cls(
            database_url=database_url,
            jwt_secret=secret,
            jwt_issuer=os.getenv("TAXLEDGER_JWT_ISSUER", "taxledger"),
            jwt_audience=os.getenv("TAXLEDGER_JWT_AUDIENCE", "taxledger-api"),
            environment=environment,
            auto_create_schema=os.getenv("TAXLEDGER_AUTO_CREATE_SCHEMA", "false").lower() == "true",
        )
