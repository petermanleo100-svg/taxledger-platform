from __future__ import annotations

import base64
from dataclasses import dataclass

from sqlalchemy import inspect, text

from .core import Database
from .settings import Settings


EXPECTED_REVISION = "20260812_0002"
TENANT_TABLES = (
    "ledger_entries",
    "vat_reconciliations",
    "filing_workpapers",
    "audit_events",
)


class PreflightError(RuntimeError):
    pass


@dataclass(frozen=True)
class PreflightResult:
    database_user: str
    schema_revision: str
    tenant_tables: int
    auth_mode: str

    def as_dict(self) -> dict:
        return {
            "valid": True,
            "database": {
                "dialect": "postgresql",
                "user": self.database_user,
                "superuser": False,
                "bypass_rls": False,
                "owns_tenant_tables": False,
                "forced_rls_tables": self.tenant_tables,
            },
            "schema_revision": self.schema_revision,
            "auth_mode": self.auth_mode,
            "backup_key": "configured-32-bytes",
        }


def _validate_backup_key(encoded: str) -> None:
    try:
        key = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise PreflightError("backup key must be valid base64") from exc
    if len(key) != 32:
        raise PreflightError("backup key must decode to exactly 32 bytes")


def run_preflight(settings: Settings, backup_key_base64: str) -> dict:
    if settings.environment != "production":
        raise PreflightError("preflight requires production environment")
    if not settings.database_url.startswith("postgresql+psycopg://"):
        raise PreflightError("production database must use postgresql+psycopg")
    if settings.auto_create_schema:
        raise PreflightError("production schema auto-creation must be disabled")
    _validate_backup_key(backup_key_base64)

    database = Database(settings.database_url)
    try:
        with database.connect() as connection:
            role = connection.execute(text(
                "SELECT current_user AS name, rolsuper, rolbypassrls "
                "FROM pg_roles WHERE rolname = current_user"
            )).mappings().one()
            if role["rolsuper"]:
                raise PreflightError("request database role must not be superuser")
            if role["rolbypassrls"]:
                raise PreflightError("request database role must be NOBYPASSRLS")

            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one_or_none()
            if revision != EXPECTED_REVISION:
                raise PreflightError(f"database schema must be at revision {EXPECTED_REVISION}")

            rows = connection.execute(text(
                "SELECT c.relname, pg_get_userbyid(c.relowner) AS owner, "
                "c.relrowsecurity, c.relforcerowsecurity "
                "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = current_schema() AND c.relkind = 'r'"
            )).mappings()
            tables = {row["relname"]: row for row in rows}
            missing = sorted(set(TENANT_TABLES) - set(tables))
            if missing:
                raise PreflightError(f"missing tenant tables: {', '.join(missing)}")
            owned = sorted(name for name in TENANT_TABLES if tables[name]["owner"] == role["name"])
            if owned:
                raise PreflightError("request database role must not own tenant tables")
            unprotected = sorted(
                name for name in TENANT_TABLES
                if not tables[name]["relrowsecurity"] or not tables[name]["relforcerowsecurity"]
            )
            if unprotected:
                raise PreflightError(f"tenant tables must enforce RLS: {', '.join(unprotected)}")
    finally:
        database.engine.dispose()

    return PreflightResult(
        database_user=role["name"],
        schema_revision=revision,
        tenant_tables=len(TENANT_TABLES),
        auth_mode=settings.auth_mode,
    ).as_dict()

