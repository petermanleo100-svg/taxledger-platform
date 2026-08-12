from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from taxledger.api import create_app
from taxledger.core import Database
from taxledger.service import TaxLedgerService
from taxledger.security import issue_token
from taxledger.settings import Settings


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
    settings=Settings(str(tmp_path / "api.db"),"test-secret-that-is-at-least-32-bytes",environment="test")
    client = TestClient(create_app(settings=settings, initialize=True))
    def headers(user, role): return {"Authorization":f"Bearer {issue_token(settings,user,'alpha',[role])}"}
    assert client.post("/ledger/entries", json=entries(), headers=headers("alice","preparer")).status_code == 201
    rec = client.post("/vat/reconciliations", json={"period":"2026-08","invoice_tax":"156","return_tax":"156"}, headers=headers("alice","preparer"))
    assert rec.status_code == 201 and rec.json()["status"] == "MATCHED"
    paper = client.post("/workpapers", json={"period":"2026-08"}, headers=headers("alice","preparer")).json()
    approved = client.post(f"/workpapers/{paper['workpaper_id']}/review", json={"approve":True}, headers=headers("bob","reviewer"))
    assert approved.json()["status"] == "APPROVED"
    assert client.get("/health/ready").json()["status"] == "ready"


def test_api_rejects_forged_tenant_and_enforces_scopes(tmp_path):
    settings=Settings(str(tmp_path/"secure.db"),"test-secret-that-is-at-least-32-bytes",environment="test")
    client=TestClient(create_app(settings=settings,initialize=True))
    viewer={"Authorization":f"Bearer {issue_token(settings,'eve','beta',['viewer'])}","X-Tenant-ID":"alpha"}
    assert client.post("/ledger/entries",json=entries(),headers=viewer).status_code==403
    assert client.get("/lineage/ERP-1",headers=viewer).status_code==404
    assert client.post("/ledger/entries",json=entries()).status_code==401


def test_operational_headers_metrics_and_strict_payload(tmp_path):
    settings=Settings(str(tmp_path/"ops.db"),"test-secret-that-is-at-least-32-bytes",environment="test")
    client=TestClient(create_app(settings=settings,initialize=True))
    response=client.get("/health/live",headers={"X-Request-ID":"trace-123"})
    assert response.headers["x-request-id"]=="trace-123"
    assert response.headers["x-content-type-options"]=="nosniff"
    assert "taxledger_http_requests_total" in client.get("/metrics").text
    token=issue_token(settings,"alice","alpha",["preparer"])
    invalid={**entries()[0],"unexpected":"blocked"}
    assert client.post("/ledger/entries",json=[invalid],headers={"Authorization":f"Bearer {token}"}).status_code==422
