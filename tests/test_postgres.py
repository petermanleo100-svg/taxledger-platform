import os
import pytest
from sqlalchemy import text
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
