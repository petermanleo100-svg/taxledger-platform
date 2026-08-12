import pytest

from taxledger.operation_metrics import record_operation


def test_operation_metric_is_atomic_and_preserves_last_success_on_failure(tmp_path):
    path = tmp_path / "taxledger.prom"
    record_operation(path, "backup_create", True, now=100)
    record_operation(path, "backup_create", False, now=200)
    text = path.read_text(encoding="utf-8")
    assert 'taxledger_operation_success{operation="backup_create"} 0' in text
    assert 'taxledger_operation_last_run_timestamp_seconds{operation="backup_create"} 200.000' in text
    assert 'taxledger_operation_last_success_timestamp_seconds{operation="backup_create"} 100.000' in text
    assert list(tmp_path.glob(".taxledger.prom.*")) == []


def test_operation_metric_rejects_unbounded_labels(tmp_path):
    with pytest.raises(ValueError, match="bounded"):
        record_operation(tmp_path / "metric.prom", 'bad"label', True)
