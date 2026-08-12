from __future__ import annotations

import hashlib, json
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine, insert, select
from sqlalchemy.pool import NullPool
from .models import AuditEvent, Base


def now(): return datetime.now(timezone.utc).isoformat(timespec="milliseconds")
def canonical(value): return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
def digest(value): return hashlib.sha256(canonical(value).encode()).hexdigest()


class Database:
    def __init__(self, value):
        raw = str(value); self.url = raw if "://" in raw else f"sqlite:///{Path(raw).resolve().as_posix()}"
        options = {"pool_pre_ping": True}
        if self.url.startswith("sqlite"): options.update(poolclass=NullPool, connect_args={"check_same_thread": False})
        self.engine = create_engine(self.url, **options)
    def initialize(self): Base.metadata.create_all(self.engine)
    @contextmanager
    def connect(self):
        with self.engine.begin() as conn: yield conn


def audit(conn, tenant, event_type, entity_id, payload):
    previous = conn.execute(select(AuditEvent.event_hash).where(AuditEvent.tenant_id == tenant).order_by(AuditEvent.id.desc()).limit(1)).scalar_one_or_none() or "GENESIS"
    occurred = now(); material = {"tenant": tenant, "event_type": event_type, "entity_id": entity_id, "payload": payload, "occurred_at": occurred, "previous_hash": previous}
    event_hash = digest(material)
    conn.execute(insert(AuditEvent).values(tenant_id=tenant, event_type=event_type, entity_id=entity_id,
        payload_json=canonical(payload), occurred_at=occurred, previous_hash=previous, event_hash=event_hash))
