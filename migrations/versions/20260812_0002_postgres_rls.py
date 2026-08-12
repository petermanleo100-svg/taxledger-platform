"""PostgreSQL tenant row-level security"""
from alembic import op
revision="20260812_0002";down_revision="20260812_0001";branch_labels=None;depends_on=None
TABLES=("ledger_entries","vat_reconciliations","filing_workpapers","audit_events")
def upgrade():
 if op.get_bind().dialect.name!="postgresql":return
 for table in TABLES:
  op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
  op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
  op.execute(f"CREATE POLICY {table}_tenant_policy ON {table} USING (tenant_id = current_setting('app.tenant_id', true)) WITH CHECK (tenant_id = current_setting('app.tenant_id', true))")
def downgrade():
 if op.get_bind().dialect.name!="postgresql":return
 for table in TABLES:
  op.execute(f"DROP POLICY IF EXISTS {table}_tenant_policy ON {table}");op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
