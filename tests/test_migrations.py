import os,subprocess,sys
from pathlib import Path
from sqlalchemy import create_engine,inspect
ROOT=Path(__file__).parents[1]
def run(db,cmd):
 env={**os.environ,"TAXLEDGER_DATABASE_URL":f"sqlite:///{db.as_posix()}"};subprocess.run([sys.executable,"-m","alembic",*cmd],cwd=ROOT,env=env,check=True,capture_output=True,text=True)
def test_migration_upgrade_downgrade_roundtrip(tmp_path):
 db=tmp_path/"migration.db";run(db,["upgrade","head"]);assert "ledger_entries" in inspect(create_engine(f"sqlite:///{db.as_posix()}")).get_table_names();run(db,["downgrade","base"]);assert "ledger_entries" not in inspect(create_engine(f"sqlite:///{db.as_posix()}")).get_table_names();run(db,["upgrade","head"])
