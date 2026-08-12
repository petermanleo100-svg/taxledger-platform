from decimal import Decimal
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from .core import Database
from .service import TaxLedgerService
from .observability import OperationsMiddleware, metrics_response
from .security import Principal, authenticate, require
from .settings import Settings


class EntryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_system: str; source_id: str; period: str; account_code: str; tax_code: str
    net_amount: Decimal; tax_amount: Decimal; mapping: dict = Field(default_factory=dict); transformations: list[str] = Field(default_factory=list)
class ReconcileIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    period: str; invoice_tax: Decimal; return_tax: Decimal; tolerance: Decimal = Decimal("0.01")
class WorkpaperIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    period: str
class ReviewIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approve: bool


def create_app(database=None, settings: Settings | None = None, initialize: bool | None = None):
    settings = settings or (Settings.from_env() if database is None else Settings(str(database), "test-secret-that-is-at-least-32-bytes"))
    db = Database(database or settings.database_url)
    if initialize is True or (initialize is None and (database is not None or settings.auto_create_schema)): db.initialize()
    app = FastAPI(title="TaxLedger Platform", version="1.0.0", docs_url="/docs" if settings.environment != "production" else None)
    app.add_middleware(OperationsMiddleware)
    def service(principal: Principal): return TaxLedgerService(db, principal.tenant_id)
    def current(authorization: str | None = Header(default=None)): return authenticate(settings, authorization)
    @app.get("/health/ready")
    def ready():
        with db.connect() as conn: conn.exec_driver_sql("SELECT 1")
        return {"status": "ready", "dialect": db.engine.dialect.name}
    @app.get("/health/live")
    def live(): return {"status": "live", "version": "1.0.0"}
    @app.get("/metrics", include_in_schema=False)
    def metrics(): return metrics_response()
    @app.post("/ledger/entries", status_code=201)
    def ingest(items: list[EntryIn], actor: Principal = Depends(current)):
        require(actor, "ledger:write")
        try: return {"ingested": service(actor).ingest([item.model_dump() for item in items])}
        except Exception as exc: raise HTTPException(409, str(exc))
    @app.post("/vat/reconciliations", status_code=201)
    def reconcile(item: ReconcileIn, actor: Principal = Depends(current)):
        require(actor, "ledger:write")
        return service(actor).reconcile(item.period, item.invoice_tax, item.return_tax, str(item.tolerance))
    @app.post("/workpapers", status_code=201)
    def workpaper(item: WorkpaperIn, actor: Principal = Depends(current)):
        require(actor, "workpaper:prepare")
        try: return service(actor).prepare_workpaper(item.period, actor.subject)
        except ValueError as exc: raise HTTPException(409, str(exc))
    @app.post("/workpapers/{workpaper_id}/review")
    def review(workpaper_id: int, item: ReviewIn, actor: Principal = Depends(current)):
        require(actor, "workpaper:review")
        try: return service(actor).review(workpaper_id, actor.subject, item.approve)
        except ValueError as exc: raise HTTPException(409, str(exc))
    @app.get("/lineage/{source_id}")
    def lineage(source_id: str, actor: Principal = Depends(current)):
        require(actor, "ledger:read")
        try: return service(actor).lineage(source_id)
        except ValueError as exc: raise HTTPException(404, str(exc))
    return app
