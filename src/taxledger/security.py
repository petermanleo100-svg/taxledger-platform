from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

import jwt
from fastapi import Header, HTTPException

from .settings import Settings


ROLE_SCOPES = {
    "viewer": {"ledger:read", "workpaper:read"},
    "preparer": {"ledger:read", "ledger:write", "workpaper:read", "workpaper:prepare"},
    "reviewer": {"ledger:read", "workpaper:read", "workpaper:review"},
    "admin": {"ledger:read", "ledger:write", "workpaper:read", "workpaper:prepare", "workpaper:review", "integrity:verify"},
}


@dataclass(frozen=True)
class Principal:
    subject: str
    tenant_id: str
    roles: tuple[str, ...]
    scopes: frozenset[str]

class OIDCVerifier:
    def __init__(self,settings:Settings,jwks_client=None):
        self.settings=settings;self.client=jwks_client or jwt.PyJWKClient(settings.oidc_jwks_url,cache_keys=True,lifespan=300,timeout=5)
    def decode(self,token):
        key=self.client.get_signing_key_from_jwt(token)
        return jwt.decode(token,key.key,algorithms=["RS256","ES256"],issuer=self.settings.jwt_issuer,audience=self.settings.jwt_audience,options={"require":["sub","tenant_id","roles","iss","aud","iat","exp"]})

def build_verifier(settings,jwks_client=None):return OIDCVerifier(settings,jwks_client) if settings.auth_mode=="oidc" else None

def _principal(payload):
    roles=tuple(str(role) for role in payload["roles"]);scopes=frozenset().union(*(ROLE_SCOPES.get(role,set()) for role in roles));tenant=str(payload["tenant_id"]);subject=str(payload["sub"])
    if not scopes or not tenant or len(tenant)>64 or not tenant.replace("-","").replace("_","").isalnum() or not subject or len(subject)>200:raise ValueError("invalid identity claims")
    return Principal(subject,tenant,roles,scopes)


def issue_token(settings: Settings, subject: str, tenant_id: str, roles: Iterable[str], minutes: int = 30) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": subject, "tenant_id": tenant_id, "roles": list(roles), "iss": settings.jwt_issuer,
         "aud": settings.jwt_audience, "iat": now, "exp": now + timedelta(minutes=minutes)},
        settings.jwt_secret, algorithm="HS256",
    )


def authenticate(settings: Settings, authorization: str | None = Header(default=None),verifier=None) -> Principal:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Bearer token required", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload=(verifier or build_verifier(settings)).decode(authorization[7:]) if settings.auth_mode=="oidc" else jwt.decode(authorization[7:], settings.jwt_secret, algorithms=["HS256"],issuer=settings.jwt_issuer,audience=settings.jwt_audience,options={"require": ["sub", "tenant_id", "roles", "exp", "iat"]})
        return _principal(payload)
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(401, "invalid access token", headers={"WWW-Authenticate": "Bearer"}) from exc


def require(principal: Principal, scope: str) -> None:
    if scope not in principal.scopes:
        raise HTTPException(403, f"missing scope: {scope}")
