from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from taxledger.api import create_app
from taxledger.core import Database
from taxledger.service import TaxLedgerService


def entries(): return [
    {"source_system":"ERP","source_id":"ERP-1","period":"2026-08","account_code":"222101","tax_code":"VAT13",
     "net_amount":"1000.0000","tax_amount":"130.0000","mapping":{"source":"SAP.BSEG"},"transformations":["tax_code_map_v3"]},
    {"source_system":"INVOICE","source_id":"INV-1","period":"2026-08","account_code":"222101","tax_code":"VAT13",
     "net_amount":"200.0000","tax_amount":"26.0000","mapping":{"source":"invoice_pool"},"transformations":[]},
]


def test_end_to_end_reconciliation_workpaper_and_four_eyes(tmp_path):
    service = TaxLedgerService(Database(tmp_path / "ledger.db"), "alpha"); service.db.initialize()
    assert service.ingest(entries()) == 2
    reconciliation = service.reconcile("2026-08", "156", "155")
    assert reconciliation["ledger_tax"] == Decimal("156.0000")
    assert reconciliation["status"] == "EXCEPTION"
    paper = service.prepare_workpaper("2026-08", "alice")
    with pytest.raises(ValueError, match="independent"):
        service.review(paper["workpaper_id"], "alice", True)
    assert service.review(paper["workpaper_id"], "bob", True)["status"] == "APPROVED"
    assert service.lineage("ERP-1")["lineage"]["mapping"]["source"] == "SAP.BSEG"


def test_tenant_isolation_and_decimal_precision(tmp_path):
    db = Database(tmp_path / "tenant.db"); db.initialize()
    TaxLedgerService(db, "alpha").ingest(entries())
    assert TaxLedgerService(db, "beta").reconcile("2026-08", 0, 0)["ledger_tax"] == Decimal("0.0000")


def test_api_real_workflow(tmp_path):
    client = TestClient(create_app(str(tmp_path / "api.db"))); headers={"X-Tenant-ID":"alpha"}
    assert client.post("/ledger/entries", json=entries(), headers=headers).status_code == 201
    rec = client.post("/vat/reconciliations", json={"period":"2026-08","invoice_tax":"156","return_tax":"156"}, headers=headers)
    assert rec.status_code == 201 and rec.json()["status"] == "MATCHED"
    paper = client.post("/workpapers", json={"period":"2026-08","prepared_by":"alice"}, headers=headers).json()
    approved = client.post(f"/workpapers/{paper['workpaper_id']}/review", json={"reviewer":"bob","approve":True}, headers=headers)
    assert approved.json()["status"] == "APPROVED"
    assert client.get("/health/ready").json()["status"] == "ready"
