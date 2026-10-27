"""Build spine/serve/* from spine/pipeline/09 (scratch builder, not part of the repo).

Gold is built by SQL files run on the SQL warehouse from the laptop (globalbank/warehouse.py, the
SDK's statement execution API): plain Delta tables, so their versions answer the regulator's "as
reported on" question. The pipeline (Course 7) keeps bronze and silver; this course adds the clearing
file, the core system's postings and silver accounts to it. Statements list what CLEARED (the
scheme's settlement, in EUR), as a real statement does; the card files are only landed for the last
days of October, where 8.4 needs them.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_c5 import CAT, RESET, read, step  # noqa: E402

PARENT = 'pipeline/09-full-refresh'
P = 'serve'

catalog_py = read(f'{PARENT}/project/globalbank/catalog.py').replace(
    "'landing.core_cdc',\n", "'landing.core_cdc',\n           'landing.postings', ")
assert 'landing.postings' in catalog_py

WAREHOUSE = '''"""Run a .sql file on the workspace's SQL warehouse, from the laptop."""
import sys
import time
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import (StatementParameterListItem,
                                       StatementState)


def warehouse(w):
    return next(w.warehouses.list())  # Free Edition has one


def run(w, sql, **params):
    r = w.statement_execution.execute_statement(
        warehouse_id=warehouse(w).id, statement=sql, wait_timeout='30s',
        parameters=[StatementParameterListItem(name=k, value=str(v))
                    for k, v in params.items()])
    while r.status.state in (StatementState.PENDING, StatementState.RUNNING):
        time.sleep(2)
        r = w.statement_execution.get_statement(r.statement_id)
    if r.status.state != StatementState.SUCCEEDED:
        raise SystemExit(f'{r.status.state.value}: {r.status.error.message}')
    columns = [c.name for c in r.manifest.schema.columns]
    return columns, (r.result.data_array or []) if r.result else []


def show(columns, rows):
    """Print a result as aligned columns: numbers right, text left."""
    cols = list(zip(*rows)) if rows else [()] * len(columns)
    widths = [max([len(c)] + [len(str(v)) for v in col])
              for c, col in zip(columns, cols)]
    number = lambda v: str(v)[:1].isdigit() or str(v)[:1] == '-'
    for line in [columns] + rows:
        print('  '.join(str(v).rjust(n) if number(v) else str(v).ljust(n)
                        for v, n in zip(line, widths)).rstrip())


if __name__ == '__main__':
    w = WorkspaceClient()
    if sys.argv[1] == '--about':
        wh = warehouse(w)
        print(f'{wh.name}: {wh.cluster_size},'
              f' serverless {wh.enable_serverless_compute}')
        raise SystemExit
    path = Path(sys.argv[1])
    params = dict(arg.split('=', 1) for arg in sys.argv[2:])
    for sql in [s for s in path.read_text().split(';') if s.strip()]:
        show(*run(w, sql, **params))
'''

CARD_SPEND = """-- Gold, as the business reads it: approved card spend per day, in EUR.
SELECT day, auths, spend
FROM globalbank_dev.gold.card_spend_daily
ORDER BY day
"""

BRONZE_ADD = """

@dp.table(name='globalbank_dev.bronze.settlements', table_properties=KEEP)
def settlements():
    return landed('settlements', 'csv',
                  'amount DECIMAL(18,2), amount_eur DECIMAL(18,2),'
                  ' cleared_date DATE')


@dp.table(name='globalbank_dev.bronze.postings', table_properties=KEEP)
def postings():
    return landed('postings', 'csv', 'amount DECIMAL(18,2), posted_date DATE')
"""

SILVER_ADD = """

ACCOUNT = ('account_id STRING, customer_id STRING, product STRING,'
           ' iban STRING, opened DATE, status STRING,'
           ' overdraft_limit DECIMAL(18,2), opening_balance DECIMAL(18,2)')


@dp.temporary_view()
def account_changes():
    return spark.sql(f\"\"\"
        SELECT op, seq, coalesce(a.account_id, k) AS account_id,
               a.* EXCEPT (account_id)
        FROM (SELECT op, seq, key:account_id AS k,
                     from_json(after, '{ACCOUNT}') AS a
              FROM STREAM(globalbank_dev.bronze.core_cdc)
              WHERE `table` = 'accounts')\"\"\")


dp.create_streaming_table('globalbank_dev.silver.accounts')
dp.create_auto_cdc_flow(
    target='globalbank_dev.silver.accounts', source='account_changes',
    keys=['account_id'], sequence_by='seq', apply_as_deletes="op = 'D'",
    except_column_list=['op'], stored_as_scd_type=1)


@dp.materialized_view(name='globalbank_dev.silver.settlements')
def settlements():
    return spark.sql(\"\"\"
        SELECT auth_id, card_id, kind, amount, currency, amount_eur,
               cleared_date
        FROM globalbank_dev.bronze.settlements
        QUALIFY row_number() OVER (PARTITION BY auth_id
                                   ORDER BY landed_at) = 1\"\"\")


@dp.materialized_view(name='globalbank_dev.silver.postings')
def postings():
    return spark.sql(\"\"\"
        SELECT posting_id, account_id, kind, amount, posted_date
        FROM globalbank_dev.bronze.postings
        QUALIFY row_number() OVER (PARTITION BY posting_id
                                   ORDER BY landed_at) = 1\"\"\")
"""

BALANCES = """-- Gold: every account's balance at the end of every day, in EUR.
-- Opening balance + the core system's postings - what cards cleared.
CREATE OR REPLACE TABLE globalbank_dev.gold.daily_balances AS
WITH days AS (
  SELECT explode(sequence(DATE'2026-09-01', DATE'2026-10-31')) AS day),
moves AS (
  SELECT account_id, posted_date AS day, amount
  FROM globalbank_dev.silver.postings
  UNION ALL
  SELECT a.account_id, s.cleared_date, -s.amount_eur
  FROM globalbank_dev.silver.settlements s
  JOIN globalbank_dev.silver.accounts a
    ON s.card_id = 'K' || substr(a.account_id, 2, 6)
   AND a.product = 'current'),
daily AS (SELECT account_id, day, sum(amount) AS moved
          FROM moves GROUP BY ALL)
SELECT a.account_id, d.day,
       a.opening_balance + sum(coalesce(m.moved, 0)) OVER (
         PARTITION BY a.account_id ORDER BY d.day) AS balance
FROM globalbank_dev.silver.accounts a
JOIN days d ON d.day >= a.opened
LEFT JOIN daily m ON m.account_id = a.account_id AND m.day = d.day
"""

BALANCE_OF = """-- One account's October, a week to a row: the balance each evening.
SELECT min(day) AS week_from,
       array_join(transform(array_sort(collect_list(struct(day, balance))),
                            x -> format_number(x.balance, 0)), '  ') AS balances
FROM globalbank_dev.gold.daily_balances
WHERE account_id = :account AND day >= DATE'2026-10-01'
GROUP BY weekofyear(day)
ORDER BY week_from
"""

STATEMENTS = """-- Gold: every account's October statement.
CREATE OR REPLACE TABLE globalbank_dev.gold.monthly_statements AS
WITH card AS (
  SELECT a.account_id, sum(s.amount_eur) AS cards, count(*) AS card_lines
  FROM globalbank_dev.silver.settlements s
  JOIN globalbank_dev.silver.accounts a
    ON s.card_id = 'K' || substr(a.account_id, 2, 6)
   AND a.product = 'current'
  WHERE s.cleared_date BETWEEN DATE'2026-10-01' AND DATE'2026-10-31'
    AND s.kind = 'SETTLEMENT'
  GROUP BY ALL),
core AS (
  SELECT account_id,
         sum(amount) FILTER (WHERE kind = 'SALARY') AS salary,
         sum(amount) FILTER (WHERE kind = 'RENT') AS rent,
         sum(amount) FILTER (WHERE kind = 'TRANSFER') AS transfers
  FROM globalbank_dev.silver.postings
  WHERE posted_date BETWEEN DATE'2026-10-01' AND DATE'2026-10-31'
  GROUP BY ALL)
SELECT '2026-10' AS month, b.account_id,
       o.balance AS opening, coalesce(card.cards, 0) AS cards,
       coalesce(card.card_lines, 0) AS card_lines,
       coalesce(core.salary, 0) AS salary, coalesce(core.rent, 0) AS rent,
       coalesce(core.transfers, 0) AS transfers, b.balance AS closing
FROM globalbank_dev.gold.daily_balances b
JOIN globalbank_dev.gold.daily_balances o
  ON o.account_id = b.account_id AND o.day = DATE'2026-09-30'
LEFT JOIN card ON card.account_id = b.account_id
LEFT JOIN core ON core.account_id = b.account_id
WHERE b.day = DATE'2026-10-31'
"""

STATEMENT_OF = """-- One account's October statement, a line per entry.
SELECT stack(7, 'opening balance', opening, 'card payments', -cards,
             'salary', salary, 'rent', rent, 'transfers', transfers,
             'closing balance', closing,
             'check', opening - cards + salary + rent + transfers - closing)
       AS (line, eur)
FROM globalbank_dev.gold.monthly_statements
WHERE account_id = :account
"""

SNAPSHOT = """-- Gold: what the bank reports on its card book, for the last days of October.
CREATE OR REPLACE TABLE globalbank_dev.gold.regulatory_snapshot AS
SELECT to_date(t.auth_ts) AS day, count(*) AS approved,
       count(s.auth_id) AS cleared, sum(s.amount_eur) AS cleared_eur
FROM globalbank_dev.silver.card_transactions t
LEFT JOIN globalbank_dev.silver.settlements s USING (auth_id)
WHERE t.status = 'APPROVED'
GROUP BY ALL
"""

ASOF = '''"""The regulator's question: the report as it stood then, and as it is now."""
from globalbank.warehouse import run, show
from databricks.sdk import WorkspaceClient

SNAPSHOT = 'globalbank_dev.gold.regulatory_snapshot'

w = WorkspaceClient()
_, history = run(w, f'DESCRIBE HISTORY {SNAPSHOT}')
first, last = history[-1], history[0]  # newest first
for label, version in (('as reported', first), ('as restated', last)):
    print(f'{label}: version {version[0]}, written {version[1][:16]}')
    show(*run(w, f"""SELECT day, approved, cleared, cleared_eur
                     FROM {SNAPSHOT} TIMESTAMP AS OF '{version[1]}'
                     ORDER BY day"""))
'''

DASHBOARD = '''"""Publish the statements dashboard, then run each of its datasets once."""
import json
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.dashboards import Dashboard

from globalbank.warehouse import run, show, warehouse

NAME = 'globalbank statements'

w = WorkspaceClient()
spec = Path('dashboards/statements.lvdash.json').read_text()
folder = f'/Workspace/Users/{w.current_user.me().user_name}/globalbank'
w.workspace.mkdirs(folder)
found = [d for d in w.lakeview.list() if d.display_name == NAME]
board = Dashboard(display_name=NAME, serialized_dashboard=spec,
                  warehouse_id=warehouse(w).id, parent_path=folder)
if found:
    w.lakeview.update(found[0].dashboard_id, dashboard=board)
else:
    found = [w.lakeview.create(board)]
w.lakeview.publish(found[0].dashboard_id, warehouse_id=warehouse(w).id)
print(f'{NAME}: published, {len(json.loads(spec)["datasets"])} datasets')
for dataset in json.loads(spec)['datasets']:
    print(f"-- {dataset['displayName']}")
    show(*run(w, ''.join(dataset['queryLines'])))
'''


def lvdash():
    by_region = ['SELECT c.region, round(sum(s.amount_eur)) AS card_eur\n',
                 'FROM globalbank_dev.silver.settlements s\n',
                 'JOIN globalbank_dev.silver.accounts a\n',
                 "  ON s.card_id = 'K' || substr(a.account_id, 2, 6) AND a.product = 'current'\n",
                 'JOIN globalbank_dev.silver.customers c USING (customer_id)\n',
                 "WHERE s.kind = 'SETTLEMENT' AND s.cleared_date >= DATE'2026-10-01'\n",
                 'GROUP BY ALL ORDER BY region']
    by_segment = ['SELECT c.segment, count(*) AS accounts,\n',
                  '       round(avg(m.closing)) AS avg_closing_eur\n',
                  'FROM globalbank_dev.gold.monthly_statements m\n',
                  'JOIN globalbank_dev.silver.accounts a USING (account_id)\n',
                  'JOIN globalbank_dev.silver.customers c USING (customer_id)\n',
                  "WHERE a.product = 'current'\n",
                  'GROUP BY ALL ORDER BY avg_closing_eur']

    def bar(name, dataset, x, y, pos):
        return {'widget': {'name': name, 'queries': [{'name': 'main_query', 'query': {
            'datasetName': dataset, 'disaggregated': True,
            'fields': [{'name': x, 'expression': f'`{x}`'}, {'name': y, 'expression': f'`{y}`'}]}}],
            'spec': {'version': 3, 'widgetType': 'bar', 'encodings': {
                'x': {'fieldName': x, 'scale': {'type': 'categorical'}, 'displayName': x},
                'y': {'fieldName': y, 'scale': {'type': 'quantitative'}, 'displayName': y}}}},
            'position': pos}
    return json.dumps({
        'datasets': [
            {'name': 'by_region', 'displayName': 'October card spend by region', 'queryLines': by_region},
            {'name': 'by_segment', 'displayName': 'Closing balance by segment', 'queryLines': by_segment},
        ],
        'pages': [{'name': 'october', 'displayName': 'October', 'layout': [
            bar('spend', 'by_region', 'region', 'card_eur', {'x': 0, 'y': 0, 'width': 3, 'height': 6}),
            bar('balance', 'by_segment', 'segment', 'avg_closing_eur', {'x': 3, 'y': 0, 'width': 3, 'height': 6}),
        ]}],
    }, indent=1) + '\n'


OVERDRAWN = """-- Accounts below their overdraft limit at the end of a day: an alert's query.
SELECT b.day, count(*) AS accounts, round(min(b.balance)) AS lowest_eur
FROM globalbank_dev.gold.daily_balances b
JOIN globalbank_dev.silver.accounts a USING (account_id)
WHERE b.balance < -a.overdraft_limit AND b.day >= DATE'2026-10-25'
GROUP BY ALL ORDER BY b.day
"""

ALERT = '''"""Create the overdraft alert: the warehouse runs its query on a schedule."""
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.service import sql

from globalbank.warehouse import warehouse

NAME = 'globalbank overdrafts'

w = WorkspaceClient()
query = Path('sql/alerts/overdrawn.sql').read_text()
alert = sql.AlertV2(
    display_name=NAME, query_text=query, warehouse_id=warehouse(w).id,
    evaluation=sql.AlertV2Evaluation(
        source=sql.AlertV2OperandColumn(name='accounts',
                                        aggregation=sql.Aggregation.SUM),
        comparison_operator=sql.ComparisonOperator.GREATER_THAN,
        threshold=sql.AlertV2Operand(
            value=sql.AlertV2OperandValue(double_value=0)),
        empty_result_state=sql.AlertEvaluationState.OK),
    schedule=sql.CronSchedule(quartz_cron_schedule='0 0 7 * * ?',
                              timezone_id='Europe/Amsterdam'))
for old in w.alerts_v2.list_alerts():
    if old.display_name == NAME:
        w.alerts_v2.trash_alert(old.id)
created = w.alerts_v2.create_alert(alert)
e = created.evaluation
print(f'{NAME}: created, {created.lifecycle_state.value.lower()}')
print(f'  when SUM(accounts) {e.comparison_operator.value} 0,'
      f' every day at 07:00 Europe/Amsterdam')
'''

SLOW = '''"""This session's statements on the warehouse: what each one read."""
from databricks.sdk import WorkspaceClient

from globalbank.warehouse import run, show

w = WorkspaceClient()
show(*run(w, """
    SELECT left(regexp_replace(statement_text, '\\\\s+', ' '), 34) AS statement,
           read_files AS files, pruned_files AS pruned,
           round(read_bytes / 1e6, 1) AS read_mb
    FROM system.query.history
    WHERE start_time > current_timestamp() - INTERVAL 30 MINUTES
      AND executed_by = current_user() AND read_files > 0
      AND statement_text NOT LIKE '%system.query.history%'
    ORDER BY start_time DESC LIMIT 6"""))
'''

POINT = """-- Card spend on one day: the filter the regulator's report runs most.
SELECT count(*) AS settlements, sum(amount_eur) AS eur
FROM globalbank_dev.silver.settlements
WHERE cleared_date = DATE'2026-10-30'
"""

WH = 'python -m globalbank.warehouse'
q = lambda c: c + ' > /dev/null'
BASE = [RESET, CAT, 'bash land.sh 2026-10-29 card_auths 2026-10-31 > /dev/null',
        'bash land.sh 2026-09-01 core_cdc 2026-10-31 > /dev/null']
MONEY = ['bash land.sh 2026-09-02 settlements 2026-10-31 > /dev/null',
         'bash land.sh 2026-09-01 postings 2026-10-31 > /dev/null']
PIPE = [q('python -m globalbank.deploy'), q('python -m globalbank.run')]
BUILT = BASE + MONEY + PIPE + [q(f'{WH} sql/gold/daily_balances.sql')]
STATED = BUILT + [q(f'{WH} sql/gold/monthly_statements.sql')]

step(P, '01-warehouse', PARENT, ['globalbank/warehouse.py', 'sql/gold/card_spend.sql'],
     {'globalbank/warehouse.py': WAREHOUSE, 'sql/gold/card_spend.sql': CARD_SPEND},
     [f'{WH} --about', f'{WH} sql/gold/card_spend.sql'], BASE + PIPE)
step(P, '02-daily-balances', f'{P}/01-warehouse',
     ['globalbank/catalog.py', 'pipelines/bronze.py', 'pipelines/silver.py',
      'sql/gold/daily_balances.sql', 'sql/gold/balance_of.sql'],
     {'globalbank/catalog.py': catalog_py,
      'pipelines/bronze.py': read(f'{PARENT}/project/pipelines/bronze.py') + BRONZE_ADD,
      'pipelines/silver.py': read(f'{PARENT}/project/pipelines/silver.py') + SILVER_ADD,
      'sql/gold/daily_balances.sql': BALANCES, 'sql/gold/balance_of.sql': BALANCE_OF},
     [f'{WH} sql/gold/daily_balances.sql', f'{WH} sql/gold/balance_of.sql account=A0000011'],
     BASE + MONEY + PIPE)
step(P, '03-statements', f'{P}/02-daily-balances', ['sql/gold/monthly_statements.sql', 'sql/gold/statement_of.sql'],
     {'sql/gold/monthly_statements.sql': STATEMENTS, 'sql/gold/statement_of.sql': STATEMENT_OF},
     [f'{WH} sql/gold/monthly_statements.sql', f'{WH} sql/gold/statement_of.sql account=A0000011'], BUILT)
step(P, '04-as-of', f'{P}/03-statements', ['sql/gold/regulatory_snapshot.sql', 'globalbank/asof.py'],
     {'sql/gold/regulatory_snapshot.sql': SNAPSHOT, 'globalbank/asof.py': ASOF},
     ['bash land.sh 2026-11-01 settlements 2026-11-03 | wc -l', 'python -m globalbank.run | sed -n 1p',
      q(f'{WH} sql/gold/regulatory_snapshot.sql'), 'python -m globalbank.asof'],
     BUILT + [q(f'{WH} sql/gold/regulatory_snapshot.sql'), 'sleep 5'],
     extra={'mask': [r'written \d{4}-\d{2}-\d{2} \d{2}:\d{2}']})
step(P, '05-dashboard', f'{P}/04-as-of', ['dashboards/statements.lvdash.json', 'globalbank/dashboard.py'],
     {'dashboards/statements.lvdash.json': lvdash(), 'globalbank/dashboard.py': DASHBOARD},
     ['python -m globalbank.dashboard'], STATED)
step(P, '06-alerts', f'{P}/05-dashboard', ['sql/alerts/overdrawn.sql', 'globalbank/alert.py'],
     {'sql/alerts/overdrawn.sql': OVERDRAWN, 'globalbank/alert.py': ALERT},
     [f'{WH} sql/alerts/overdrawn.sql', 'python -m globalbank.alert'], BUILT)
step(P, '07-slow-query', f'{P}/06-alerts', ['sql/gold/point.sql', 'globalbank/slow.py'],
     {'sql/gold/point.sql': POINT, 'globalbank/slow.py': SLOW},
     [f'{WH} sql/gold/point.sql', 'python -m globalbank.slow'], STATED + ['sleep 60'],
     extra={'volatile': ['digits']})
print('built')
