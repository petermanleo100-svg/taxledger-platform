import base64
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from taxledger.backup import create_backup, restore_backup
from taxledger.core import Database
from taxledger.integrity import verify_audit_chain
from taxledger.preflight import PreflightError, run_preflight
from taxledger.service import TaxLedgerService
from taxledger.settings import Settings


URL = os.getenv("TEST_POSTGRES_URL")
pytestmark = pytest.mark.skipif(not URL, reason="TEST_POSTGRES_URL is not configured")
BACKUP_KEY = base64.b64encode(bytes(range(32))).decode()
ROOT = Path(__file__).parents[1]


@pytest.fixture()
def postgres_db():
    db = Database(URL)
    db.initialize()
    with db.connect() as conn:
        for table in ("audit_events", "filing_workpapers", "vat_reconciliations", "ledger_entries"):
            conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
    yield db
    db.engine.dispose()


def ledger_item(source_id, period="2026-08", net="0.1000", tax="0.0300"):
    return {
        "source_system": "ERP",
        "source_id": source_id,
        "period": period,
        "account_code": "222101",
        "tax_code": "VAT13",
        "net_amount": net,
        "tax_amount": tax,
    }


def test_postgres_transaction_precision_and_tenant_isolation(postgres_db):
    TaxLedgerService(postgres_db, "alpha").ingest([ledger_item("PG-1")])
    assert str(TaxLedgerService(postgres_db, "alpha").reconcile("2026-08", "0.03", "0.03")["ledger_tax"]) == "0.0300"
    assert str(TaxLedgerService(postgres_db, "beta").reconcile("2026-08", "0", "0")["ledger_tax"]) == "0.0000"


def test_postgres_rls_blocks_direct_cross_tenant_sql(postgres_db):
    TaxLedgerService(postgres_db, "alpha").ingest([ledger_item("RLS-A")])
    TaxLedgerService(postgres_db, "beta").ingest([ledger_item("RLS-B")])
    admin = create_engine(URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text("DROP ROLE IF EXISTS taxledger_runtime"))
        conn.execute(text("CREATE ROLE taxledger_runtime LOGIN PASSWORD 'runtime-test-password' NOSUPERUSER NOBYPASSRLS"))
        conn.execute(text("GRANT USAGE ON SCHEMA public TO taxledger_runtime"))
        conn.execute(text("GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO taxledger_runtime"))
        conn.execute(text("GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO taxledger_runtime"))
    runtime = create_engine(URL.replace("taxledger:taxledger@", "taxledger_runtime:runtime-test-password@"))
    try:
        with runtime.begin() as conn:
            conn.execute(text("SELECT set_config('app.tenant_id','alpha',true)"))
            assert conn.execute(text("SELECT count(*) FROM ledger_entries")).scalar_one() == 1
            conn.execute(text("SELECT set_config('app.tenant_id','beta',true)"))
            assert conn.execute(text("SELECT count(*) FROM ledger_entries")).scalar_one() == 1
            assert conn.execute(text("UPDATE ledger_entries SET tax_amount=999 WHERE tenant_id='alpha'")).rowcount == 0
    finally:
        runtime.dispose()
        with admin.connect() as conn:
            conn.execute(text("DROP OWNED BY taxledger_runtime"))
            conn.execute(text("DROP ROLE taxledger_runtime"))
        admin.dispose()


def test_postgres_concurrent_audit_chain_has_no_forks(postgres_db):
    def write(index):
        TaxLedgerService(postgres_db, "concurrent").ingest([ledger_item(f"CON-{index}", "2026-09", "1", "0.13")])

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(write, range(24)))
    with postgres_db.connect("concurrent") as conn:
        result = verify_audit_chain(conn, "concurrent")
        assert result["valid"] and result["checked"] == 24


def test_postgres_encrypted_backup_restores_to_clean_schema(postgres_db, tmp_path):
    service = TaxLedgerService(postgres_db, "recovery")
    service.ingest([ledger_item("PG-BACKUP")])
    service.reconcile("2026-08", "0.03", "0.03")
    paper = service.prepare_workpaper("2026-08", "alice")
    service.review(paper["workpaper_id"], "bob", True)
    backup_path = tmp_path / "postgres-backup.enc"
    create_backup(postgres_db, backup_path, BACKUP_KEY)

    with postgres_db.engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS recovery_target CASCADE"))
        conn.execute(text("CREATE SCHEMA recovery_target"))
    target_url = make_url(URL).set(query={"options": "-csearch_path=recovery_target"})
    target = Database(target_url.render_as_string(hide_password=False))
    try:
        environment = {**os.environ, "TAXLEDGER_DATABASE_URL": target.url}
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=ROOT,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )
        restored = restore_backup(target, backup_path, BACKUP_KEY)
        assert restored["valid"]
        with target.connect("recovery") as conn:
            assert verify_audit_chain(conn, "recovery")["valid"]
        assert TaxLedgerService(target, "recovery").lineage("PG-BACKUP")["lineage"]["source_system"] == "ERP"
    finally:
        target.engine.dispose()
        with postgres_db.engine.begin() as conn:
            conn.execute(text("DROP SCHEMA recovery_target CASCADE"))


def test_production_preflight_accepts_runtime_role_and_rejects_owner(postgres_db):
    admin = create_engine(URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text("DROP ROLE IF EXISTS taxledger_preflight"))
        conn.execute(text("CREATE ROLE taxledger_preflight LOGIN PASSWORD 'preflight-password' NOSUPERUSER NOBYPASSRLS"))
        conn.execute(text("GRANT CONNECT ON DATABASE taxledger TO taxledger_preflight"))
        conn.execute(text("GRANT USAGE ON SCHEMA public TO taxledger_preflight"))
        conn.execute(text("GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO taxledger_preflight"))
        conn.execute(text("GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO taxledger_preflight"))
    runtime_url = URL.replace("taxledger:taxledger@", "taxledger_preflight:preflight-password@")
    settings = Settings(runtime_url, "", "https://id.example", "taxledger-api", "production", False, "oidc", "https://id.example/jwks", False)
    try:
        result = run_preflight(settings, BACKUP_KEY)
        assert result["valid"] and result["database"]["user"] == "taxledger_preflight"
        owner_settings = Settings(URL, "", "https://id.example", "taxledger-api", "production", False, "oidc", "https://id.example/jwks", False)
        with pytest.raises(PreflightError, match="superuser"):
            run_preflight(owner_settings, BACKUP_KEY)
    finally:
        with admin.connect() as conn:
            conn.execute(text("DROP OWNED BY taxledger_preflight"))
            conn.execute(text("DROP ROLE taxledger_preflight"))
        admin.dispose()
