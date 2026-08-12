import json
import sys
from types import SimpleNamespace

import pytest

import taxledger.operations as operations


def test_backup_cli_writes_success_metric(tmp_path, monkeypatch, capsys):
    metrics = tmp_path / "metrics"
    monkeypatch.setenv("TAXLEDGER_TEXTFILE_DIR", str(metrics))
    monkeypatch.setattr(operations.Settings, "from_env", lambda: SimpleNamespace(database_url="sqlite://"))
    monkeypatch.setattr(operations, "Database", lambda _url: object())
    monkeypatch.setattr(operations, "create_backup", lambda _db, path: {"path": path, "rows": 3})
    monkeypatch.setattr(sys, "argv", ["taxledger-operations", "backup-create", str(tmp_path / "backup")])
    with pytest.raises(SystemExit, match="0"):
        operations.main()
    assert json.loads(capsys.readouterr().out)["rows"] == 3
    assert 'taxledger_operation_success{operation="backup_create"} 1' in (metrics / "taxledger_backup_create.prom").read_text()


def test_backup_cli_writes_failure_metric_on_exception(tmp_path, monkeypatch):
    metrics = tmp_path / "metrics"
    monkeypatch.setenv("TAXLEDGER_TEXTFILE_DIR", str(metrics))
    monkeypatch.setattr(operations.Settings, "from_env", lambda: SimpleNamespace(database_url="sqlite://"))
    monkeypatch.setattr(operations, "Database", lambda _url: object())
    monkeypatch.setattr(operations, "create_backup", lambda *_: (_ for _ in ()).throw(OSError("disk full")))
    monkeypatch.setattr(sys, "argv", ["taxledger-operations", "backup-create", str(tmp_path / "backup")])
    with pytest.raises(OSError, match="disk full"):
        operations.main()
    assert 'taxledger_operation_success{operation="backup_create"} 0' in (metrics / "taxledger_backup_create.prom").read_text()
