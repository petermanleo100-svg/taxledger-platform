from types import SimpleNamespace
from taxledger.database_metrics import collect_database_health,write_database_metrics
class Result:
 def __init__(self,value):self.value=value
 def scalar_one(self):return self.value
class Connection:
 def __init__(self):self.values=iter((80,100))
 def execute(self,_query):return Result(next(self.values))
class Context:
 def __enter__(self):return Connection()
 def __exit__(self,*_args):pass
class DB:
 engine=SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
 def connect(self):return Context()
def test_database_health_and_atomic_metrics(tmp_path):
 result=collect_database_health(DB());assert result=={"connections":80,"max_connections":100,"utilization_ratio":0.8};path=tmp_path/"db.prom";write_database_metrics(path,result);assert "taxledger_db_connection_utilization_ratio 0.800000" in path.read_text()
