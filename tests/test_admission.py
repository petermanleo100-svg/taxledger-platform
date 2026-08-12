import json
from datetime import datetime, timezone
from taxledger.admission import REQUIRED_CONTROLS, verify_admission

SHA = "a" * 40
def evidence():
    checked = datetime.now(timezone.utc).isoformat()
    return {"schema_version":2,"project":"taxledger-platform","release_sha":SHA,"environment":"customer-staging","deployed_by":"release-engineer@example.com","controls":{name:{"status":"passed","verifier":"control-owner@example.com","verified_at_utc":checked,"evidence_uri":f"https://evidence.example.com/{name}","evidence_sha256":"b"*64} for name in REQUIRED_CONTROLS}}
def test_admission_accepts_fresh_release_bound_complete_evidence(tmp_path):
    path=tmp_path/"evidence.json";path.write_text(json.dumps(evidence()),encoding="utf-8")
    assert verify_admission(path,SHA)["valid"] is True
def test_admission_fails_closed_on_pending_missing_and_wrong_release(tmp_path):
    data=evidence();data["release_sha"]="b"*40;data["controls"]["alert_delivery"]["status"]="pending";del data["controls"]["oidc_key_rotation"]
    path=tmp_path/"evidence.json";path.write_text(json.dumps(data),encoding="utf-8");result=verify_admission(path,SHA)
    assert result["valid"] is False and any("does not match" in error for error in result["errors"]) and any("not passed" in error for error in result["errors"]) and any("missing required" in error for error in result["errors"])
def test_admission_rejects_naive_non_utc_time(tmp_path):
    data=evidence();data["controls"]["alert_delivery"]["verified_at_utc"]="2026-08-13T10:00:00";path=tmp_path/"evidence.json";path.write_text(json.dumps(data),encoding="utf-8")
    assert "control alert_delivery verified_at_utc is invalid" in verify_admission(path,SHA)["errors"]
def test_admission_rejects_self_approval_missing_digest_and_age_bypass(tmp_path):
    data=evidence();data["controls"]["alert_delivery"]["verifier"]="RELEASE-ENGINEER@example.com";data["controls"]["alert_delivery"]["evidence_sha256"]="bad";path=tmp_path/"evidence.json";path.write_text(json.dumps(data),encoding="utf-8");errors=verify_admission(path,SHA)["errors"]
    assert any("independent" in error for error in errors) and any("evidence_sha256" in error for error in errors)
    assert verify_admission(path,SHA,169)["errors"]==["max_age_hours must be between 1 and 168"]
