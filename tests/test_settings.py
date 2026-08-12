import pytest
from taxledger.settings import Settings
def test_production_requires_oidc_or_explicit_hmac_exception(monkeypatch):
 monkeypatch.setenv("TAXLEDGER_DATABASE_URL","sqlite:///x.db");monkeypatch.setenv("TAXLEDGER_ENV","production");monkeypatch.setenv("TAXLEDGER_AUTH_MODE","hmac");monkeypatch.setenv("TAXLEDGER_JWT_SECRET","x"*32)
 with pytest.raises(RuntimeError,match="ALLOW_HMAC"):Settings.from_env()
 monkeypatch.setenv("TAXLEDGER_ALLOW_HMAC_PRODUCTION","true");assert Settings.from_env().auth_mode=="hmac"
def test_oidc_requires_https(monkeypatch):
 monkeypatch.setenv("TAXLEDGER_DATABASE_URL","sqlite:///x.db");monkeypatch.setenv("TAXLEDGER_ENV","production");monkeypatch.setenv("TAXLEDGER_AUTH_MODE","oidc");monkeypatch.setenv("TAXLEDGER_JWT_ISSUER","http://id");monkeypatch.setenv("TAXLEDGER_OIDC_JWKS_URL","http://id/jwks")
 with pytest.raises(RuntimeError,match="HTTPS"):Settings.from_env()
