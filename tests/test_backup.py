import base64,os
import pytest
from taxledger.backup import create_backup,restore_backup
from taxledger.core import Database
from taxledger.service import TaxLedgerService
from test_taxledger import entries

KEY=base64.b64encode(bytes(range(32))).decode()
def test_encrypted_backup_clean_restore_and_business_verification(tmp_path):
 source=Database(tmp_path/"source.db");source.initialize();service=TaxLedgerService(source,"alpha");service.ingest(entries());service.reconcile("2026-08","156","156");paper=service.prepare_workpaper("2026-08","alice");service.review(paper["workpaper_id"],"bob",True)
 backup=tmp_path/"backup.enc";result=create_backup(source,backup,KEY);assert result["rows"]>=5 and b"ERP-1" not in backup.read_bytes()
 target=Database(tmp_path/"restore.db");restored=restore_backup(target,backup,KEY);assert restored["valid"]
 assert TaxLedgerService(target,"alpha").lineage("ERP-1")["lineage"]["source_system"]=="ERP"
 with pytest.raises(ValueError,match="empty"):restore_backup(target,backup,KEY)
def test_wrong_backup_key_is_rejected(tmp_path):
 source=Database(tmp_path/"empty.db");source.initialize();path=tmp_path/"backup.enc";create_backup(source,path,KEY)
 with pytest.raises(Exception):restore_backup(Database(tmp_path/"target.db"),path,base64.b64encode(os.urandom(32)).decode())
