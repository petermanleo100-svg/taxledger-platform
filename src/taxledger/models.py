from __future__ import annotations

from decimal import Decimal
from sqlalchemy import Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

MONEY = Numeric(20, 4)


class Base(DeclarativeBase): pass


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_system: Mapped[str] = mapped_column(String(30), nullable=False)
    source_id: Mapped[str] = mapped_column(String(100), nullable=False)
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    account_code: Mapped[str] = mapped_column(String(30), nullable=False)
    tax_code: Mapped[str] = mapped_column(String(30), nullable=False)
    net_amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    lineage_json: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    __table_args__ = (UniqueConstraint("tenant_id", "source_system", "source_id", "content_hash"),)


class VatReconciliation(Base):
    __tablename__ = "vat_reconciliations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    ledger_tax: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    invoice_tax: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    return_tax: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    ledger_invoice_variance: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    ledger_return_variance: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[str] = mapped_column(String(40), nullable=False)


class FilingWorkpaper(Base):
    __tablename__ = "filing_workpapers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    period: Mapped[str] = mapped_column(String(7), nullable=False)
    prepared_by: Mapped[str] = mapped_column(String(100), nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    __table_args__ = (UniqueConstraint("tenant_id", "period"),)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[str] = mapped_column(String(40), nullable=False)
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
