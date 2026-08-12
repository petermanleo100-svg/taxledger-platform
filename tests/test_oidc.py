from datetime import datetime,timedelta,timezone
import jwt,pytest
from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key
from taxledger.security import OIDCVerifier,authenticate
from taxledger.settings import Settings
class Client:
 def __init__(self,key):self.key=key;self.calls=0
 def get_signing_key_from_jwt(self,_token):self.calls+=1;return type("Key",(),{"key":self.key})()
def token(key,**overrides):
 now=datetime.now(timezone.utc);claims={"sub":"alice","tenant_id":"alpha","roles":["preparer"],"iat":now,"exp":now+timedelta(minutes=5),"iss":"https://id.example.com","aud":"taxledger-api"};claims.update(overrides);return jwt.encode(claims,key,algorithm="RS256",headers={"kid":"k1"})
def test_oidc_signature_claims_roles_and_tenant():
 key=generate_private_key(public_exponent=65537,key_size=2048);settings=Settings("sqlite://","",jwt_issuer="https://id.example.com",auth_mode="oidc",oidc_jwks_url="https://id.example.com/jwks");verifier=OIDCVerifier(settings,Client(key.public_key()))
 assert authenticate(settings,"Bearer "+token(key),verifier).tenant_id=="alpha"
 for bad in ({"aud":"wrong"},{"roles":["superuser"]},{"tenant_id":"../escape"}):
  with pytest.raises(Exception):authenticate(settings,"Bearer "+token(key,**bad),verifier)
