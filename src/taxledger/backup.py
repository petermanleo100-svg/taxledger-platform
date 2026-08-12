from __future__ import annotations
import base64,json,os
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import delete,insert,select
from .core import Database,canonical,digest,now
from .models import AuditEvent,FilingWorkpaper,LedgerEntry,VatReconciliation
from .integrity import verify_audit_chain

TABLES=(LedgerEntry,VatReconciliation,FilingWorkpaper,AuditEvent)
def _key(value=None):
 raw=value or os.getenv("TAXLEDGER_BACKUP_KEY_BASE64","")
 try:key=base64.b64decode(raw,validate=True)
 except Exception as exc:raise ValueError("backup key must be base64") from exc
 if len(key)!=32:raise ValueError("backup key must decode to 32 bytes")
 return key
def _json_row(row):return {k:str(v) if hasattr(v,"as_tuple") else v for k,v in dict(row).items()}
def snapshot(db:Database):
 with db.connect() as conn:
  tables={model.__tablename__:[_json_row(r) for r in conn.execute(select(model).order_by(model.id)).mappings()] for model in TABLES}
 return {"format":"taxledger-backup-v1","created_at":now(),"tables":tables}
def create_backup(db,path,key_b64=None):
 payload=snapshot(db);plain=canonical(payload).encode();nonce=os.urandom(12);encrypted=AESGCM(_key(key_b64)).encrypt(nonce,plain,b"taxledger-backup-v1")
 envelope={"format":"taxledger-aes256gcm-v1","nonce":base64.b64encode(nonce).decode(),"ciphertext":base64.b64encode(encrypted).decode(),"plaintext_sha256":digest(payload)}
 target=Path(path);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(canonical(envelope),encoding="utf-8");return {"path":str(target),"sha256":digest(envelope),"rows":sum(map(len,payload["tables"].values()))}
def restore_backup(target:Database,path,key_b64=None):
 envelope=json.loads(Path(path).read_text(encoding="utf-8"));nonce=base64.b64decode(envelope["nonce"]);cipher=base64.b64decode(envelope["ciphertext"])
 payload=json.loads(AESGCM(_key(key_b64)).decrypt(nonce,cipher,b"taxledger-backup-v1"))
 if payload.get("format")!="taxledger-backup-v1" or digest(payload)!=envelope["plaintext_sha256"]:raise ValueError("backup integrity verification failed")
 target.initialize()
 with target.connect() as conn:
  if any(conn.execute(select(model.id).limit(1)).first() for model in TABLES):raise ValueError("restore target must be empty")
  for model in TABLES:
   rows=payload["tables"][model.__tablename__]
   if rows:conn.execute(insert(model),rows)
  verification=verify_audit_chain(conn)
 if not verification["valid"]:raise ValueError("restored audit chain is invalid")
 return {"valid":True,"rows":sum(map(len,payload["tables"].values())),"plaintext_sha256":envelope["plaintext_sha256"]}
