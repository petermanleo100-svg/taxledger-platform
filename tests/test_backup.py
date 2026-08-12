import base64
import os
import subprocess
import sys
from pathlib import Path

import pytest

from taxledger.backup import create_backup, restore_backup
from taxledger.core import Database
from taxledger.service import TaxLedgerService
from test_taxledger import entries


KEY = base64.b64encode(bytes(range(32))).decode()
ROOT = Path(__file__).parents[1]


def migrate(path):
    environment = {**os.environ, "TAXLEDGER_DATABASE_URL": f"sqlite:///{path.as_posix()}"}
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


def test_encrypted_backup_clean_restore_and_business_verification(tmp_path):
    source = Database(tmp_path / "source.db")
    source.initialize()
    service = TaxLedgerService(source, "alpha")
    service.ingest(entries())
    service.reconcile("2026-08", "156", "156")
    paper = service.prepare_workpaper("2026-08", "alice")
    service.review(paper["workpaper_id"], "bob", True)
    backup = tmp_path / "backup.enc"
    result = create_backup(source, backup, KEY)
    assert result["rows"] >= 5 and b"ERP-1" not in backup.read_bytes()

    target_path = tmp_path / "restore.db"
    migrate(target_path)
    target = Database(target_path)
    restored = restore_backup(target, backup, KEY)
    assert restored["valid"]
    assert TaxLedgerService(target, "alpha").lineage("ERP-1")["lineage"]["source_system"] == "ERP"
    with pytest.raises(ValueError, match="empty"):
        restore_backup(target, backup, KEY)


def test_wrong_backup_key_is_rejected(tmp_path):
    source = Database(tmp_path / "empty.db")
    source.initialize()
    path = tmp_path / "backup.enc"
    create_backup(source, path, KEY)
    with pytest.raises(Exception):
        restore_backup(Database(tmp_path / "target.db"), path, base64.b64encode(os.urandom(32)).decode())


def test_restore_rejects_unmigrated_target(tmp_path):
    source = Database(tmp_path / "source.db")
    source.initialize()
    path = tmp_path / "backup.enc"
    create_backup(source, path, KEY)
    with pytest.raises(ValueError, match="migrated"):
        restore_backup(Database(tmp_path / "target.db"), path, KEY)
