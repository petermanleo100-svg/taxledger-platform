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


def issue_token(settings: Settings, subject: str, tenant_id: str, roles: Iterable[str], minutes: int = 30) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": subject, "tenant_id": tenant_id, "roles": list(roles), "iss": settings.jwt_issuer,
         "aud": settings.jwt_audience, "iat": now, "exp": now + timedelta(minutes=minutes)},
        settings.jwt_secret, algorithm="HS256",
    )


def authenticate(settings: Settings, authorization: str | None = Header(default=None)) -> Principal:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Bearer token required", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(authorization[7:], settings.jwt_secret, algorithms=["HS256"],
                             issuer=settings.jwt_issuer, audience=settings.jwt_audience,
                             options={"require": ["sub", "tenant_id", "roles", "exp", "iat"]})
        roles = tuple(str(role) for role in payload["roles"])
        scopes = frozenset().union(*(ROLE_SCOPES.get(role, set()) for role in roles))
        if not scopes:
            raise ValueError("token has no recognized role")
        return Principal(str(payload["sub"]), str(payload["tenant_id"]), roles, scopes)
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(401, "invalid access token", headers={"WWW-Authenticate": "Bearer"}) from exc


def require(principal: Principal, scope: str) -> None:
    if scope not in principal.scopes:
        raise HTTPException(403, f"missing scope: {scope}")
