import argparse,json,os
from .backup import create_backup,restore_backup
from .core import Database
from .integrity import verify_audit_chain
from .settings import Settings
from .preflight import PreflightError,run_preflight
def main():
 parser=argparse.ArgumentParser(prog="taxledger-operations");sub=parser.add_subparsers(dest="command",required=True)
 create=sub.add_parser("backup-create");create.add_argument("path")
 restore=sub.add_parser("backup-restore");restore.add_argument("path");restore.add_argument("--target-url",required=True)
 verify=sub.add_parser("audit-verify");verify.add_argument("--tenant")
 sub.add_parser("preflight")
 args=parser.parse_args()
 try:settings=Settings.from_env()
 except RuntimeError as exc:
  if args.command=="preflight":print(json.dumps({"valid":False,"error":str(exc)},sort_keys=True));raise SystemExit(2)
  raise
 db=Database(settings.database_url)
 if args.command=="preflight":
  try:result=run_preflight(settings,os.getenv("TAXLEDGER_BACKUP_KEY_BASE64",""))
  except PreflightError as exc:print(json.dumps({"valid":False,"error":str(exc)},sort_keys=True));raise SystemExit(2)
 elif args.command=="backup-create":result=create_backup(db,args.path)
 elif args.command=="backup-restore":result=restore_backup(Database(args.target_url),args.path)
 else:
  with db.connect(args.tenant) as conn:result=verify_audit_chain(conn,args.tenant)
 print(json.dumps(result,ensure_ascii=False,sort_keys=True))
 raise SystemExit(0 if result.get("valid",True) else 2)
