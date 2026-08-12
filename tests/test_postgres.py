import os
import pytest
from sqlalchemy import create_engine,text
from concurrent.futures import ThreadPoolExecutor
from taxledger.core import Database
from taxledger.service import TaxLedgerService

URL=os.getenv("TEST_POSTGRES_URL")
pytestmark=pytest.mark.skipif(not URL,reason="TEST_POSTGRES_URL is not configured")
def test_postgres_transaction_precision_and_tenant_isolation():
 db=Database(URL);db.initialize()
 with db.connect() as conn:
  for table in ("audit_events","filing_workpapers","vat_reconciliations","ledger_entries"): conn.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
 item={"source_system":"ERP","source_id":"PG-1","period":"2026-08","account_code":"222101","tax_code":"VAT13","net_amount":"0.1000","tax_amount":"0.0300"}
 TaxLedgerService(db,"alpha").ingest([item])
 assert str(TaxLedgerService(db,"alpha").reconcile("2026-08","0.03","0.03")["ledger_tax"])=="0.0300"
 assert str(TaxLedgerService(db,"beta").reconcile("2026-08","0","0")["ledger_tax"])=="0.0000"

def test_postgres_rls_blocks_direct_cross_tenant_sql():
 admin=create_engine(URL,isolation_level="AUTOCOMMIT")
 with admin.connect() as conn:
  conn.execute(text("DROP ROLE IF EXISTS taxledger_runtime"));conn.execute(text("CREATE ROLE taxledger_runtime LOGIN PASSWORD 'runtime-test-password' NOSUPERUSER NOBYPASSRLS"));conn.execute(text("GRANT USAGE ON SCHEMA public TO taxledger_runtime"));conn.execute(text("GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO taxledger_runtime"));conn.execute(text("GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO taxledger_runtime"))
 runtime=create_engine(URL.replace("taxledger:taxledger@","taxledger_runtime:runtime-test-password@"))
 with runtime.begin() as conn:
  conn.execute(text("SELECT set_config('app.tenant_id','alpha',true)"));assert conn.execute(text("SELECT count(*) FROM ledger_entries")).scalar_one()==1
  conn.execute(text("SELECT set_config('app.tenant_id','beta',true)"));assert conn.execute(text("SELECT count(*) FROM ledger_entries")).scalar_one()==0
  assert conn.execute(text("UPDATE ledger_entries SET tax_amount=999 WHERE tenant_id='alpha'")).rowcount==0

def test_postgres_concurrent_audit_chain_has_no_forks():
 db=Database(URL)
 def write(i):
  item={"source_system":"ERP","source_id":f"CON-{i}","period":"2026-09","account_code":"222101","tax_code":"VAT13","net_amount":"1","tax_amount":"0.13"};TaxLedgerService(db,"concurrent").ingest([item])
 with ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(write,range(24)))
 with db.connect("concurrent") as conn:
  from taxledger.integrity import verify_audit_chain
  result=verify_audit_chain(conn,"concurrent");assert result["valid"] and result["checked"]==24
