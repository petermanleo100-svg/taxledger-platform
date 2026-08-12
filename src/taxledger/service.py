from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import func, insert, select, update
from .core import Database, audit, canonical, digest, now
from .models import FilingWorkpaper, LedgerEntry, VatReconciliation

Q = Decimal("0.0001")
def money(value): return Decimal(str(value)).quantize(Q, rounding=ROUND_HALF_UP)


class TaxLedgerService:
    def __init__(self, db: Database, tenant_id: str): self.db, self.tenant_id = db, tenant_id

    def ingest(self, entries: list[dict]) -> int:
        rows = []
        for item in entries:
            lineage = {"source_system": item["source_system"], "source_id": item["source_id"],
                       "mapping": item.get("mapping", {}), "transformations": item.get("transformations", [])}
            material = {**item, "net_amount": str(money(item["net_amount"])), "tax_amount": str(money(item["tax_amount"])), "lineage": lineage}
            rows.append({"tenant_id": self.tenant_id, "source_system": item["source_system"], "source_id": item["source_id"],
                "period": item["period"], "account_code": item["account_code"], "tax_code": item["tax_code"],
                "net_amount": money(item["net_amount"]), "tax_amount": money(item["tax_amount"]),
                "lineage_json": canonical(lineage), "content_hash": digest(material)})
        with self.db.connect() as conn:
            if rows: conn.execute(insert(LedgerEntry), rows)
            audit(conn, self.tenant_id, "LEDGER_INGESTED", rows[0]["period"] if rows else "empty", {"rows": len(rows)})
        return len(rows)

    def reconcile(self, period: str, invoice_tax, return_tax, tolerance="0.01") -> dict:
        with self.db.connect() as conn:
            ledger = conn.execute(select(func.coalesce(func.sum(LedgerEntry.tax_amount), 0)).where(
                LedgerEntry.tenant_id == self.tenant_id, LedgerEntry.period == period)).scalar_one()
            invoice, returned = money(invoice_tax), money(return_tax); ledger = money(ledger)
            invoice_variance, return_variance = money(ledger - invoice), money(ledger - returned)
            status = "MATCHED" if abs(invoice_variance) <= Decimal(tolerance) and abs(return_variance) <= Decimal(tolerance) else "EXCEPTION"
            result = conn.execute(insert(VatReconciliation).values(tenant_id=self.tenant_id, period=period,
                ledger_tax=ledger, invoice_tax=invoice, return_tax=returned, ledger_invoice_variance=invoice_variance,
                ledger_return_variance=return_variance, status=status, created_at=now()).returning(VatReconciliation.id)).scalar_one()
            audit(conn, self.tenant_id, "VAT_RECONCILED", str(result), {"period": period, "status": status,
                  "ledger_invoice_variance": str(invoice_variance), "ledger_return_variance": str(return_variance)})
        return {"reconciliation_id": result, "period": period, "ledger_tax": ledger, "invoice_tax": invoice,
                "return_tax": returned, "ledger_invoice_variance": invoice_variance,
                "ledger_return_variance": return_variance, "status": status}

    def prepare_workpaper(self, period: str, prepared_by: str) -> dict:
        with self.db.connect() as conn:
            reconciliation = conn.execute(select(VatReconciliation).where(VatReconciliation.tenant_id == self.tenant_id,
                VatReconciliation.period == period).order_by(VatReconciliation.id.desc()).limit(1)).mappings().one_or_none()
            if reconciliation is None: raise ValueError("VAT reconciliation is required")
            entries = [dict(row) for row in conn.execute(select(LedgerEntry).where(
                LedgerEntry.tenant_id == self.tenant_id, LedgerEntry.period == period)).mappings()]
            payload = {"period": period, "reconciliation": dict(reconciliation), "entry_count": len(entries),
                       "source_hashes": sorted(row["content_hash"] for row in entries)}
            workpaper_id = conn.execute(insert(FilingWorkpaper).values(tenant_id=self.tenant_id, period=period,
                prepared_by=prepared_by, status="PENDING_REVIEW", version=1, payload_json=canonical(payload),
                payload_hash=digest(payload)).returning(FilingWorkpaper.id)).scalar_one()
            audit(conn, self.tenant_id, "WORKPAPER_PREPARED", str(workpaper_id), {"period": period, "prepared_by": prepared_by})
        return {"workpaper_id": workpaper_id, "status": "PENDING_REVIEW", "payload_hash": digest(payload)}

    def review(self, workpaper_id: int, reviewer: str, approve: bool) -> dict:
        with self.db.connect() as conn:
            row = conn.execute(select(FilingWorkpaper).where(FilingWorkpaper.id == workpaper_id,
                FilingWorkpaper.tenant_id == self.tenant_id)).mappings().one_or_none()
            if row is None or row["status"] != "PENDING_REVIEW": raise ValueError("workpaper is not pending")
            if row["prepared_by"] == reviewer: raise ValueError("independent reviewer required")
            status = "APPROVED" if approve else "REJECTED"
            result = conn.execute(update(FilingWorkpaper).where(FilingWorkpaper.id == workpaper_id,
                FilingWorkpaper.version == row["version"]).values(status=status, reviewed_by=reviewer,
                version=row["version"] + 1))
            if result.rowcount != 1: raise ValueError("concurrent review conflict")
            audit(conn, self.tenant_id, "WORKPAPER_REVIEWED", str(workpaper_id), {"status": status, "reviewer": reviewer})
        return {"workpaper_id": workpaper_id, "status": status, "reviewed_by": reviewer}

    def lineage(self, source_id: str) -> dict:
        with self.db.connect() as conn:
            row = conn.execute(select(LedgerEntry).where(LedgerEntry.tenant_id == self.tenant_id,
                LedgerEntry.source_id == source_id).order_by(LedgerEntry.id.desc()).limit(1)).mappings().one_or_none()
        if row is None: raise ValueError("unknown source_id")
        return {"source_id": source_id, "content_hash": row["content_hash"], "lineage": json.loads(row["lineage_json"])}
