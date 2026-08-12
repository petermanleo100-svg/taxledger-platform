import json
from sqlalchemy import select
from .core import canonical,digest
from .models import AuditEvent

def verify_audit_chain(conn,tenant_id=None):
 query=select(AuditEvent)
 if tenant_id is not None:query=query.where(AuditEvent.tenant_id==tenant_id)
 rows=conn.execute(query.order_by(AuditEvent.tenant_id,AuditEvent.id)).mappings();previous={};checked=0;failures=[]
 for row in rows:
  checked+=1;tenant=row["tenant_id"]
  material={"tenant":tenant,"event_type":row["event_type"],"entity_id":row["entity_id"],"payload":json.loads(row["payload_json"]),"occurred_at":row["occurred_at"],"previous_hash":row["previous_hash"]}
  actual=digest(material);expected_previous=previous.get(tenant,"GENESIS")
  if row["previous_hash"]!=expected_previous or actual!=row["event_hash"]:failures.append({"event_id":row["id"],"previous_valid":row["previous_hash"]==expected_previous,"hash_valid":actual==row["event_hash"]})
  previous[tenant]=row["event_hash"]
 return {"valid":not failures,"checked":checked,"failures":failures}
