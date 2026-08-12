from __future__ import annotations
import os,tempfile
from pathlib import Path
from sqlalchemy import text
def collect_database_health(db)->dict:
 if db.engine.dialect.name!="postgresql":raise RuntimeError("database-status-export requires PostgreSQL")
 with db.connect() as conn:
  current=conn.execute(text("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND backend_type='client backend'")).scalar_one()
  maximum=conn.execute(text("SELECT setting::bigint FROM pg_settings WHERE name='max_connections'")).scalar_one()
 if maximum<=0:raise RuntimeError("PostgreSQL max_connections must be positive")
 return {"connections":current,"max_connections":maximum,"utilization_ratio":current/maximum}
def write_database_metrics(path,result):
 target=Path(path);target.parent.mkdir(parents=True,exist_ok=True);lines=["# HELP taxledger_db_connections Current client backend connections for the TaxLedger database.","# TYPE taxledger_db_connections gauge",f"taxledger_db_connections {result['connections']}","# HELP taxledger_db_max_connections Configured PostgreSQL maximum connections.","# TYPE taxledger_db_max_connections gauge",f"taxledger_db_max_connections {result['max_connections']}","# HELP taxledger_db_connection_utilization_ratio Current connections divided by max_connections.","# TYPE taxledger_db_connection_utilization_ratio gauge",f"taxledger_db_connection_utilization_ratio {result['utilization_ratio']:.6f}"]
 handle,temporary=tempfile.mkstemp(prefix=f".{target.name}.",dir=target.parent,text=True)
 try:
  with os.fdopen(handle,"w",encoding="utf-8",newline="\n") as stream:stream.write("\n".join(lines)+"\n");stream.flush();os.fsync(stream.fileno())
  os.replace(temporary,target)
 finally:
  if os.path.exists(temporary):os.unlink(temporary)
