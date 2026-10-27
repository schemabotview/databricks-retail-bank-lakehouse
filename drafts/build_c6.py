"""Build spine/protect/* from spine/customers/07 (scratch builder, not part of the repo).

Free Edition has no account groups (no account console, no SCIM): a workspace group cannot be a
Unity Catalog principal (PRINCIPAL_DOES_NOT_EXIST, checked 2026-10-27). So 6.2 shows the grants by
layer as code, refused for that reason, and masks and row filters read a ROLE-MAPPING TABLE
(governance.roles: who reads as which role), the documented mapping-table pattern: switching the
one user's row shows two readers on one workspace, without touching the owner's identities.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_c5 import CAT, RESET, read, step  # noqa: E402

PARENT = 'customers/07-point-in-time'
P = 'protect'

catalog_py = read(f'{PARENT}/project/globalbank/catalog.py').replace(
    "LAYERS = ['landing', 'bronze', 'silver', 'gold']",
    "LAYERS = ['landing', 'bronze', 'silver', 'gold', 'governance', 'vault']")
assert 'governance' in catalog_py

UC = '''"""Unity Catalog's names, from the top: catalog, schemas, what each holds."""
from globalbank.session import get_spark

spark = get_spark()
print('metastore:', spark.sql('SELECT current_metastore()').first()[0])
catalogs = spark.sql("SHOW CATALOGS LIKE 'globalbank*'").collect()
print('catalogs: ', ', '.join(r.catalog for r in catalogs))
print('owner:    ', spark.sql("""SELECT catalog_owner
    FROM system.information_schema.catalogs
    WHERE catalog_name = 'globalbank_dev'""").first()[0])
objects = spark.sql("""
    SELECT table_schema AS schema, count(*) AS n
    FROM globalbank_dev.information_schema.tables
    WHERE table_schema NOT IN ('information_schema') GROUP BY ALL""").collect()
volumes = spark.sql("""
    SELECT volume_schema AS schema, count(*) AS n
    FROM globalbank_dev.information_schema.volumes GROUP BY ALL""").collect()
tables = {r.schema: r.n for r in objects}
vols = {r.schema: r.n for r in volumes}
print('globalbank_dev:')
for schema in ['landing', 'bronze', 'silver', 'gold', 'governance', 'vault']:
    print(f'  {schema:<11} {tables.get(schema, 0)} tables,'
          f' {vols.get(schema, 0)} volumes')
'''

GOVERN = '''"""Apply a governance file: each statement, and what the workspace said."""
import re
import sys

from globalbank.session import get_spark

spark = get_spark()
done = refused = 0
reasons = set()
for statement in open(sys.argv[1]).read().split(';'):
    sql = '\\n'.join(line for line in statement.splitlines()
                    if not line.lstrip().startswith('--')).strip()
    if not sql:
        continue
    shown = ' '.join(sql.split()).replace('globalbank_dev.', '')[:66]
    try:
        spark.sql(sql)
        done += 1
        print(f'ok   {shown}')
    except Exception as e:
        refused += 1
        reason = re.search(r'\\[([A-Z_]+)', str(e))
        reasons.add(reason.group(1) if reason else type(e).__name__)
        print(f'no   {shown}')
print(f'{done} applied, {refused} refused' +
      (f': {", ".join(sorted(reasons))}' if reasons else ''))
'''

GRANTS = """-- Who reads which layer. The principals are ACCOUNT groups, synced from
-- the bank's identity provider: engineers build, risk investigates,
-- finance and branches read only the finished products in gold.
GRANT USE CATALOG ON CATALOG globalbank_dev TO `engineers`;
GRANT USE SCHEMA, SELECT ON SCHEMA globalbank_dev.bronze TO `engineers`;
GRANT USE SCHEMA, SELECT ON SCHEMA globalbank_dev.silver TO `engineers`;
GRANT USE SCHEMA, SELECT ON SCHEMA globalbank_dev.silver TO `risk`;
GRANT USE SCHEMA, SELECT ON SCHEMA globalbank_dev.gold TO `finance`;
GRANT USE SCHEMA, SELECT ON SCHEMA globalbank_dev.gold TO `branches`;
"""

MASKS = """-- Who reads as which role: one row per user, read by every mask and filter.
CREATE TABLE IF NOT EXISTS globalbank_dev.governance.roles
  (user_name STRING, role STRING, region STRING);

-- National IDs and IBANs: only risk sees them whole.
CREATE OR REPLACE FUNCTION globalbank_dev.governance.unless_risk(v STRING)
RETURNS STRING
RETURN IF(EXISTS(SELECT 1 FROM globalbank_dev.governance.roles r
                 WHERE r.user_name = current_user() AND r.role = 'risk'),
          v, concat('*****', right(v, 3)));

ALTER TABLE globalbank_dev.silver.customers
  ALTER COLUMN national_id SET MASK globalbank_dev.governance.unless_risk;
ALTER TABLE globalbank_dev.silver.accounts
  ALTER COLUMN iban SET MASK globalbank_dev.governance.unless_risk;
"""

FILTERS = """-- A branch manager sees their region's customers; risk sees every region.
CREATE OR REPLACE FUNCTION globalbank_dev.governance.my_region(
  row_region STRING)
RETURNS BOOLEAN
RETURN EXISTS(SELECT 1 FROM globalbank_dev.governance.roles r
              WHERE r.user_name = current_user()
                AND (r.role = 'risk' OR r.region = row_region));

ALTER TABLE globalbank_dev.silver.customers
  SET ROW FILTER globalbank_dev.governance.my_region ON (region);
"""

TAGS = """-- Classify every column that identifies a person, so it can be found.
ALTER TABLE globalbank_dev.silver.customers
  ALTER COLUMN national_id SET TAGS ('pii' = 'national_id');
ALTER TABLE globalbank_dev.silver.customers
  ALTER COLUMN first_name SET TAGS ('pii' = 'name');
ALTER TABLE globalbank_dev.silver.customers
  ALTER COLUMN last_name SET TAGS ('pii' = 'name');
ALTER TABLE globalbank_dev.silver.customers
  ALTER COLUMN date_of_birth SET TAGS ('pii' = 'birth_date');
ALTER TABLE globalbank_dev.silver.customers
  ALTER COLUMN email SET TAGS ('pii' = 'contact');
ALTER TABLE globalbank_dev.silver.customers
  ALTER COLUMN address SET TAGS ('pii' = 'contact');
ALTER TABLE globalbank_dev.silver.accounts
  ALTER COLUMN iban SET TAGS ('pii' = 'account_number');
"""

ROLES = '''"""Say which role the current user reads as: their row in governance.roles."""
import sys

from globalbank.session import get_spark

ROLES = 'globalbank_dev.governance.roles'

role = sys.argv[1]
region = sys.argv[2] if len(sys.argv) > 2 else None
spark = get_spark()
spark.sql(f'DELETE FROM {ROLES} WHERE user_name = current_user()')
spark.sql(f'INSERT INTO {ROLES} VALUES (current_user(), :role, :region)',
          args={'role': role, 'region': region})
me = spark.sql('SELECT current_user()').first()[0]
print(f'{me} reads as {role}' + (f', {region}' if region else ''))
'''

PEEK = '''"""Two customers, as the current user is allowed to see them."""
from globalbank.session import get_spark

spark = get_spark()
for r in spark.sql("""
        SELECT c.customer_id, c.national_id, a.iban
        FROM globalbank_dev.silver.customers c
        JOIN globalbank_dev.silver.accounts a USING (customer_id)
        WHERE a.product = 'current'
        ORDER BY c.customer_id LIMIT 2""").collect():
    print(f'{r.customer_id}  national_id {r.national_id:<12} iban {r.iban}')
'''

REGIONS = '''"""Customers per region, as the current user is allowed to see them."""
from globalbank.session import get_spark

spark = get_spark()
rows = spark.sql("""SELECT region, count(*) AS n
                    FROM globalbank_dev.silver.customers
                    GROUP BY region ORDER BY region""").collect()
print('  '.join(f'{r.region} {r.n:,}' for r in rows) or 'no rows')
'''

PII = '''"""Every column tagged pii in the catalog: what it holds, and where."""
from globalbank.session import get_spark

spark = get_spark()
tagged = spark.sql("""
    SELECT schema_name, table_name, column_name, tag_value
    FROM globalbank_dev.information_schema.column_tags
    WHERE tag_name = 'pii' ORDER BY ALL""").collect()
print(f'{len(tagged)} columns tagged pii in globalbank_dev:')
for t in tagged:
    print(f'  {t.schema_name}.{t.table_name}.{t.column_name:<14} {t.tag_value}')
'''

LINEAGE = '''"""Which tables each table was built from, as Unity Catalog recorded it."""
from globalbank.session import get_spark

spark = get_spark()
edges = spark.sql("""
    SELECT DISTINCT
           coalesce(source_table_full_name, 'files in ' || regexp_extract(
               source_path, '/Volumes/[^/]+/([^/]+/[^/]+)', 1)) AS source,
           target_table_full_name AS target
    FROM system.access.table_lineage
    WHERE target_table_catalog = 'globalbank_dev'
      AND event_time > current_timestamp() - INTERVAL 2 HOURS
      AND target_table_full_name IN (SELECT table_catalog || '.' || table_schema
          || '.' || table_name FROM globalbank_dev.information_schema.tables)
    ORDER BY target, source""").collect()
for e in edges:
    print(f"{e.source.replace('globalbank_dev.', ''):<28} -> "
          f"{e.target.replace('globalbank_dev.', '')}")
'''

AUDIT = '''"""Who touched silver.customers in the last hour, from the audit log."""
from globalbank.session import get_spark

spark = get_spark()
rows = spark.sql("""
    SELECT user_identity.email AS who, action_name, count(*) AS n
    FROM system.access.audit
    WHERE service_name = 'unityCatalog'
      AND request_params.full_name_arg = 'globalbank_dev.silver.customers'
      AND event_time > current_timestamp() - INTERVAL 1 HOUR
    GROUP BY ALL ORDER BY n DESC""").collect()
print(f'{len(rows)} kinds of request on silver.customers in the last hour:')
for r in rows:
    print(f'  {r.who}  {r.action_name:<24} {r.n}')
'''

VAULT = '''"""The PII vault: identifying columns, keyed by customer_id, kept apart."""
from globalbank.session import get_spark

VAULT = 'globalbank_dev.vault.customer_pii'

spark = get_spark()
spark.sql(f"""CREATE OR REPLACE TABLE {VAULT} AS
    SELECT customer_id, first_name, last_name, national_id,
           date_of_birth, email, address
    FROM globalbank_dev.silver.customers""")
print(f'{VAULT}: {spark.table(VAULT).count():,} customers')
'''

ERASE = '''"""Honour an erasure request: delete the customer from the vault."""
import csv
import glob

from globalbank.session import get_spark

VAULT = 'globalbank_dev.vault.customer_pii'

path = glob.glob('landing/privacy/erasure-requests-*.csv')[0]
request = next(csv.DictReader(open(path)))
customer = request['customer_id']
print(f"request {request['request_id']}: erase {customer}")
spark = get_spark()
spark.sql(f"DELETE FROM {VAULT} WHERE customer_id = '{customer}'")
last = spark.sql(f'DESCRIBE HISTORY {VAULT} LIMIT 1').first()
m = last.operationMetrics
print(f"version {last.version}: deleted {m['numDeletedRows']} row,"
      f" deletion vectors added {m.get('numDeletionVectorsAdded', 0)}")
for v in (last.version - 1, last.version):
    n = spark.sql(f"""SELECT count(*) FROM {VAULT} VERSION AS OF {v}
                      WHERE customer_id = '{customer}'""").first()[0]
    print(f'  version {v} holds them: {n} row')
facts = spark.sql(f"""SELECT count(*) FROM globalbank_dev.silver.accounts
                      WHERE customer_id = '{customer}'""").first()[0]
print(f'silver.accounts still holds {facts} account rows for {customer}')
'''

PURGE = '''"""Make an erasure physical: rewrite the files, then remove the old ones."""
from globalbank.session import get_spark

VAULT = 'globalbank_dev.vault.customer_pii'

spark = get_spark()
spark.sql(f'REORG TABLE {VAULT} APPLY (PURGE)')
m = spark.sql(f'DESCRIBE HISTORY {VAULT} LIMIT 1').first().operationMetrics
print(f"REORG ... PURGE: {m['numAddedFiles']} file written,"
      f" {m['numRemovedFiles']} removed from the table")
vacuum = spark.sql(f'VACUUM {VAULT}').collect()
print(f'VACUUM: {len(vacuum)} files deleted now; the removed file is'
      ' deleted once it is older than the 7-day retention')
'''

INGESTED = [RESET, CAT, 'bash land.sh 2026-09-01 core_cdc 2026-10-31 > /dev/null',
            'python -m globalbank.land core_cdc > /dev/null',
            "python -m globalbank.cdc customers '2026-' > /dev/null",
            "python -m globalbank.cdc accounts '2026-' > /dev/null"]
GOV = 'python -m globalbank.govern governance/'
MASKED = INGESTED + [GOV + 'masks.sql > /dev/null']
FILTERED = MASKED + [GOV + 'filters.sql > /dev/null']

step(P, '01-unity-catalog', PARENT, ['globalbank/catalog.py', 'globalbank/uc.py'],
     {'globalbank/catalog.py': catalog_py, 'globalbank/uc.py': UC},
     ['python -m globalbank.uc'], INGESTED)
step(P, '02-grants', f'{P}/01-unity-catalog', ['globalbank/govern.py', 'governance/grants.sql'],
     {'globalbank/govern.py': GOVERN, 'governance/grants.sql': GRANTS},
     [GOV + 'grants.sql'], INGESTED)
step(P, '03-masks', f'{P}/02-grants', ['governance/masks.sql', 'globalbank/roles.py', 'globalbank/peek.py'],
     {'governance/masks.sql': MASKS, 'globalbank/roles.py': ROLES, 'globalbank/peek.py': PEEK},
     [GOV + 'masks.sql', 'python -m globalbank.peek', 'python -m globalbank.roles risk', 'python -m globalbank.peek'],
     INGESTED)
step(P, '04-row-filters', f'{P}/03-masks', ['governance/filters.sql', 'globalbank/regions.py'],
     {'governance/filters.sql': FILTERS, 'globalbank/regions.py': REGIONS},
     [GOV + 'filters.sql', 'python -m globalbank.roles branch North', 'python -m globalbank.regions',
      'python -m globalbank.roles risk', 'python -m globalbank.regions'], MASKED)
step(P, '05-tags', f'{P}/04-row-filters', ['governance/tags.sql', 'globalbank/pii.py'],
     {'governance/tags.sql': TAGS, 'globalbank/pii.py': PII},
     [GOV + 'tags.sql | tail -1', 'python -m globalbank.pii'], FILTERED)
step(P, '06-lineage', f'{P}/05-tags', ['globalbank/lineage.py'], {'globalbank/lineage.py': LINEAGE},
     ['python -m globalbank.lineage'],
     FILTERED + ['bash land.sh 2026-10-01 > /dev/null', 'python -m globalbank.land > /dev/null',
                 'python -m globalbank.ledger post 2026-10-01 > /dev/null', 'python -m globalbank.scd2 C000001 > /dev/null',
                 'sleep 240'])
step(P, '07-audit', f'{P}/06-lineage', ['globalbank/audit.py'], {'globalbank/audit.py': AUDIT},
     ['python -m globalbank.audit'], FILTERED + ['python -m globalbank.regions > /dev/null', 'sleep 240'],
     extra={'volatile': ['digits']})
step(P, '08-erasure', f'{P}/07-audit', ['globalbank/vault.py', 'globalbank/erase.py', 'globalbank/purge.py'],
     {'globalbank/vault.py': VAULT, 'globalbank/erase.py': ERASE, 'globalbank/purge.py': PURGE},
     ['python -m globalbank.vault', 'python -m globalbank.erase', 'python -m globalbank.purge'],
     FILTERED + ['python -m globalbank.roles risk > /dev/null',
                 'python -m globalbank_sim --out landing --only privacy > /dev/null'])
print('built')
