import argparse,json,os
from pathlib import Path
from .backup import create_backup,restore_backup
from .core import Database
from .integrity import verify_audit_chain
from .operation_metrics import record_operation
from .settings import Settings
from .preflight import PreflightError,run_preflight
def main():
 parser=argparse.ArgumentParser(prog="taxledger-operations");sub=parser.add_subparsers(dest="command",required=True)
 create=sub.add_parser("backup-create");create.add_argument("path")
 restore=sub.add_parser("backup-restore");restore.add_argument("path");restore.add_argument("--target-url",required=True)
 verify=sub.add_parser("audit-verify");verify.add_argument("--tenant")
 sub.add_parser("preflight")
 args=parser.parse_args()
 operation=args.command.replace("-","_");metric_dir=os.getenv("TAXLEDGER_TEXTFILE_DIR","")
 metric_path=Path(metric_dir)/f"taxledger_{operation}.prom" if metric_dir else None
 try:
  try:settings=Settings.from_env()
  except RuntimeError as exc:
   if args.command!="preflight":raise
   result={"valid":False,"error":str(exc)}
  else:
   db=Database(settings.database_url)
   if args.command=="preflight":
    try:result=run_preflight(settings,os.getenv("TAXLEDGER_BACKUP_KEY_BASE64",""))
    except PreflightError as exc:result={"valid":False,"error":str(exc)}
   elif args.command=="backup-create":result=create_backup(db,args.path)
   elif args.command=="backup-restore":result=restore_backup(Database(args.target_url),args.path)
   else:
    with db.connect(args.tenant) as conn:result=verify_audit_chain(conn,args.tenant)
 except BaseException as exc:
  if metric_path:
   try:record_operation(metric_path,operation,False)
   except Exception as metric_exc:exc.add_note(f"failed to record operation metric: {metric_exc}")
  raise
 valid=result.get("valid",True)
 if metric_path:record_operation(metric_path,operation,valid)
 print(json.dumps(result,ensure_ascii=False,sort_keys=True))
 raise SystemExit(0 if valid else 2)
