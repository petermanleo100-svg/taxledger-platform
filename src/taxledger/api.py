from decimal import Decimal
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from .core import Database
from .service import TaxLedgerService


class EntryIn(BaseModel):
    source_system: str; source_id: str; period: str; account_code: str; tax_code: str
    net_amount: Decimal; tax_amount: Decimal; mapping: dict = {}; transformations: list[str] = []
class ReconcileIn(BaseModel): period: str; invoice_tax: Decimal; return_tax: Decimal; tolerance: Decimal = Decimal("0.01")
class WorkpaperIn(BaseModel): period: str; prepared_by: str
class ReviewIn(BaseModel): reviewer: str; approve: bool


def create_app(database="work/taxledger.db"):
    db = Database(database); db.initialize(); app = FastAPI(title="TaxLedger Platform", version="0.1.0")
    def service(tenant: str): return TaxLedgerService(db, tenant)
    @app.get("/health/ready")
    def ready():
        with db.connect() as conn: conn.exec_driver_sql("SELECT 1")
        return {"status": "ready", "dialect": db.engine.dialect.name}
    @app.post("/ledger/entries", status_code=201)
    def ingest(items: list[EntryIn], x_tenant_id: str = Header(alias="X-Tenant-ID")):
        try: return {"ingested": service(x_tenant_id).ingest([item.model_dump() for item in items])}
        except Exception as exc: raise HTTPException(409, str(exc))
    @app.post("/vat/reconciliations", status_code=201)
    def reconcile(item: ReconcileIn, x_tenant_id: str = Header(alias="X-Tenant-ID")):
        return service(x_tenant_id).reconcile(item.period, item.invoice_tax, item.return_tax, str(item.tolerance))
    @app.post("/workpapers", status_code=201)
    def workpaper(item: WorkpaperIn, x_tenant_id: str = Header(alias="X-Tenant-ID")):
        try: return service(x_tenant_id).prepare_workpaper(item.period, item.prepared_by)
        except ValueError as exc: raise HTTPException(409, str(exc))
    @app.post("/workpapers/{workpaper_id}/review")
    def review(workpaper_id: int, item: ReviewIn, x_tenant_id: str = Header(alias="X-Tenant-ID")):
        try: return service(x_tenant_id).review(workpaper_id, item.reviewer, item.approve)
        except ValueError as exc: raise HTTPException(409, str(exc))
    @app.get("/lineage/{source_id}")
    def lineage(source_id: str, x_tenant_id: str = Header(alias="X-Tenant-ID")):
        try: return service(x_tenant_id).lineage(source_id)
        except ValueError as exc: raise HTTPException(404, str(exc))
    return app
