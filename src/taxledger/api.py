from decimal import Decimal
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from fastapi.responses import JSONResponse
from .core import Database
from .service import TaxLedgerService
from .observability import OperationsMiddleware, metrics_response
from .security import Principal, authenticate, require
from .settings import Settings
from .integrity import verify_audit_chain


class EntryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_system: str = Field(min_length=1,max_length=30); source_id: str = Field(min_length=1,max_length=100); period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"); account_code: str = Field(min_length=1,max_length=30); tax_code: str = Field(min_length=1,max_length=30)
    net_amount: Decimal = Field(ge=Decimal("-9999999999999999"),le=Decimal("9999999999999999")); tax_amount: Decimal = Field(ge=Decimal("-9999999999999999"),le=Decimal("9999999999999999")); mapping: dict = Field(default_factory=dict); transformations: list[str] = Field(default_factory=list,max_length=20)
class ReconcileIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"); invoice_tax: Decimal; return_tax: Decimal; tolerance: Decimal = Field(default=Decimal("0.01"),ge=0,le=Decimal("1000000"))
class WorkpaperIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
class ReviewIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approve: bool


def create_app(database=None, settings: Settings | None = None, initialize: bool | None = None):
    settings = settings or (Settings.from_env() if database is None else Settings(str(database), "test-secret-that-is-at-least-32-bytes"))
    db = Database(database or settings.database_url)
    if initialize is True or (initialize is None and (database is not None or settings.auto_create_schema)): db.initialize()
    app = FastAPI(title="TaxLedger Platform", version="1.0.0", docs_url="/docs" if settings.environment != "production" else None)
    app.add_middleware(OperationsMiddleware)
    @app.exception_handler(SQLAlchemyError)
    async def database_error(_request, _exc):
        return JSONResponse(status_code=503,content={"detail":"database operation failed"})
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
    @app.get("/operations/integrity")
    def integrity(actor: Principal = Depends(current)):
        require(actor,"integrity:verify")
        with db.connect(actor.tenant_id) as conn:return verify_audit_chain(conn,actor.tenant_id)
    @app.post("/ledger/entries", status_code=201)
    def ingest(items: list[EntryIn], actor: Principal = Depends(current)):
        require(actor, "ledger:write")
        if not 1 <= len(items) <= 1000: raise HTTPException(413,"batch must contain 1 to 1000 entries")
        try: return {"ingested": service(actor).ingest([item.model_dump() for item in items])}
        except IntegrityError as exc: raise HTTPException(409,"duplicate ledger entry") from exc
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
