"""Build spine/schedule/* from spine/detect/08 (scratch builder, not part of the repo).

The nightly job is written as a bundle resource (resources/nightly.yml), so Course 11's bundle takes
the same file unchanged; until then globalbank/job.py deploys it with the SDK, filling in the three
references a bundle would resolve (the pipeline's id, the warehouse, the workspace folder) and the
current user. Tasks: the pipeline (bronze, silver) → gold SQL on the warehouse → the fraud rule →
a check in Python on serverless job compute. Free Edition allows 5 concurrent tasks: the widest
point here is 2.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_c5 import CAT, RESET, read, step  # noqa: E402

PARENT = 'detect/08-tradeoff'
P = 'schedule'

REQUIREMENTS = read(f'{PARENT}/project/requirements.txt') + 'pyyaml==6.0.3\n'

TASKS = """      tasks:
        - task_key: pipeline
          pipeline_task:
            pipeline_id: ${resources.pipelines.globalbank_pipeline.id}
        - task_key: accounts
          depends_on: [{task_key: pipeline}]
          sql_task:
            warehouse_id: ${var.warehouse_id}
            file:
              path: "${workspace.file_path}/sql/gold/accounts.sql"
        - task_key: balances
          depends_on: [{task_key: pipeline}]
          sql_task:
            warehouse_id: ${var.warehouse_id}
            file:
              path: "${workspace.file_path}/sql/gold/daily_balances.sql"
        - task_key: statements
          depends_on: [{task_key: balances}]
          sql_task:
            warehouse_id: ${var.warehouse_id}
            file:
              path: "${workspace.file_path}/sql/gold/monthly_statements.sql"
        - task_key: flags
          depends_on: [{task_key: pipeline}]
          sql_task:
            warehouse_id: ${var.warehouse_id}
            file:
              path: "${workspace.file_path}/sql/fraud/flags.sql"
        - task_key: check
          depends_on:
            - {task_key: accounts}
            - {task_key: statements}
            - {task_key: flags}
          environment_key: default
          spark_python_task:
            python_file: ${workspace.file_path}/jobs/check.py
            parameters: ["{{job.parameters.run_date}}"]
"""

MONTH_END_TASK = """        - task_key: month_end
          depends_on: [{task_key: check}]
          sql_task:
            warehouse_id: ${var.warehouse_id}
            file:
              path: "${workspace.file_path}/sql/gold/month_end.sql"
"""

MONTH_END_PARAMS = """            parameters: {month: "{{tasks.check.values.month}}"}
"""


def nightly(trigger=False, month_end=False, params=False, owner=False):
    head = """# The nightly run, as a bundle resource: bronze and silver (the pipeline),
# then gold on the SQL warehouse, then checks. Deployed by globalbank/job.py
# until Course 11's bundle deploys it.
resources:
  jobs:
    globalbank_nightly:
      name: globalbank_nightly
      parameters:
        - {name: run_date, default: "2026-10-31"}
      environments:
        - environment_key: default
          spec: {environment_version: "4"}
"""
    if trigger:
        head += """      trigger:  # a new clearing file starts the run
        file_arrival: {url: /Volumes/globalbank_dev/landing/settlements/}
"""
    if owner:
        head += """      run_as: {user_name: "${workspace.current_user.userName}"}
      email_notifications:
        on_failure: ["${workspace.current_user.userName}"]
"""
    body = TASKS + (MONTH_END_TASK + (MONTH_END_PARAMS if params else '') if month_end else '')
    return head + body


FLAGS = """-- Gold: card-testing flags, by the velocity rule (Course 9).
CREATE OR REPLACE TABLE globalbank_dev.gold.fraud_flags AS
SELECT auth_id, card_id, auth_ts, auths_10m
FROM (SELECT auth_id, card_id, auth_ts,
             count(*) OVER (PARTITION BY card_id ORDER BY auth_ts
                            RANGE BETWEEN INTERVAL 10 MINUTES PRECEDING
                                      AND CURRENT ROW) AS auths_10m
      FROM globalbank_dev.silver.card_transactions)
WHERE auths_10m > 5
"""

CHECK = '''"""The nightly run's last check: did the day's clearing file arrive?"""
import sys

from databricks.sdk.runtime import dbutils
from pyspark.sql import SparkSession

day = sys.argv[1]
spark = SparkSession.builder.getOrCreate()
cleared = spark.sql(f"""SELECT count(*) FROM globalbank_dev.silver.settlements
                        WHERE cleared_date = '{day}'""").first()[0]
statements = spark.table('globalbank_dev.gold.monthly_statements').count()
print(f'{day}: {cleared} settlements cleared, {statements} statements')
if not cleared:
    raise SystemExit(f'no clearing file for {day}: the gold tables are stale')
dbutils.jobs.taskValues.set(key='cleared', value=cleared)
dbutils.jobs.taskValues.set(key='month', value=day[:7])
'''

JOB = '''"""The nightly job: deploy | run [k=v] | wait | repair | output | who."""
import sys
import time
from pathlib import Path

import yaml
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import JobSettings
from databricks.sdk.service.workspace import ImportFormat

from globalbank.deploy import NAME as PIPELINE
from globalbank.warehouse import warehouse

NAME = 'globalbank_nightly'
FILES = ['sql/gold/accounts.sql', 'sql/gold/daily_balances.sql', 'sql/gold/monthly_statements.sql',
         'sql/gold/month_end.sql', 'sql/fraud/flags.sql', 'jobs/check.py']


def settings(w):
    """resources/nightly.yml, with what a bundle would fill in filled in."""
    me = w.current_user.me().user_name
    folder = f'/Workspace/Users/{me}/globalbank'
    pipeline = next(w.pipelines.list_pipelines(
        filter=f"name LIKE '{PIPELINE}'"))
    text = Path('resources/nightly.yml').read_text()
    filled = {'resources.pipelines.globalbank_pipeline.id':
              pipeline.pipeline_id,
              'var.warehouse_id': warehouse(w).id,
              'workspace.file_path': folder,
              'workspace.current_user.userName': me}
    for ref, value in filled.items():
        text = text.replace('${' + ref + '}', value)
    for f in (f for f in FILES if Path(f).exists()):
        w.workspace.mkdirs(f'{folder}/{Path(f).parent}')
        w.workspace.upload(f'{folder}/{f}', open(f, 'rb'),
                           format=ImportFormat.AUTO, overwrite=True)
    job = yaml.safe_load(text)['resources']['jobs'][NAME]
    return JobSettings.from_dict(job)


def job_id(w):
    return next(w.jobs.list(name=NAME)).job_id


def report(w, run):
    run = w.jobs.get_run(run.run_id)
    print(f'run {run.state.result_state.value}'
          f' ({run.trigger.value.lower()}): {len(run.tasks)} tasks')
    for t in sorted(run.tasks, key=lambda t: t.start_time or 0):
        state = t.state.result_state.value if t.state.result_state else '-'
        print(f'  {t.task_key:<11}{state:<16}'
              + (t.state.state_message or '')[:48].split('\\n')[0])


if __name__ == '__main__':
    w = WorkspaceClient()
    verb = sys.argv[1]
    if verb == 'deploy':
        job = settings(w)
        found = list(w.jobs.list(name=NAME))
        if found:
            w.jobs.reset(found[0].job_id, new_settings=job)
        else:
            w.jobs.create(**job.as_shallow_dict())
        print(f'{NAME}: {"updated" if found else "created"}')
        for t in job.tasks:
            after = ', '.join(d.task_key for d in t.depends_on or [])
            print(f'  {t.task_key:<11}{"after " + after if after else "first"}')
    elif verb == 'run':
        params = dict(a.split('=', 1) for a in sys.argv[2:])
        run = w.jobs.run_now(job_id(w), job_parameters=params or None).response
        while not w.jobs.get_run(run.run_id).state.result_state:
            time.sleep(15)
        report(w, run)
'''

JOB_WAIT = """    elif verb == 'wait':  # for the run a new file started
        for _ in range(60):
            runs = [r for r in w.jobs.list_runs(job_id=job_id(w))
                    if r.trigger and r.trigger.value == 'FILE_ARRIVAL']
            if runs and runs[0].state.result_state:
                break
            time.sleep(15)
        report(w, runs[0])
"""

JOB_REPAIR = """    elif verb == 'repair':  # re-run what failed, and what depends on it
        failed = lambda r: r.state.result_state and \\
            r.state.result_state.value == 'FAILED'
        run = next(r for r in w.jobs.list_runs(job_id=job_id(w), limit=5)
                   if failed(r))
        w.jobs.repair_run(run.run_id, rerun_all_failed_tasks=True,
                          rerun_dependent_tasks=True)
        time.sleep(30)
        while not w.jobs.get_run(run.run_id).state.result_state:
            time.sleep(15)
        report(w, run)
"""

JOB_OUTPUT = """    elif verb == 'output':  # what a task of the last run printed
        last = next(w.jobs.list_runs(job_id=job_id(w), limit=1))
        run = w.jobs.get_run(last.run_id)
        task = next(t for t in run.tasks if t.task_key == sys.argv[2])
        print(w.jobs.get_run_output(task.run_id).logs.strip())
"""

JOB_WHO = """    elif verb == 'who':  # who the job runs as, and who hears of a failure
        s = w.jobs.get(job_id(w)).settings
        print(f'run as: {s.run_as.user_name}')
        emails = ', '.join(s.email_notifications.on_failure)
        print(f'on failure, email: {emails}')
"""

MONTH_END = """-- Gold: the month-end figures the ledger closes on, appended per run.
CREATE TABLE IF NOT EXISTS globalbank_dev.gold.month_end
  (month STRING, accounts BIGINT, deposits_eur DECIMAL(18,2));
INSERT INTO globalbank_dev.gold.month_end
SELECT month, count(*), sum(closing)
FROM globalbank_dev.gold.monthly_statements GROUP BY month
"""

MONTH_END_FIXED = """-- Gold: the month-end figures the ledger closes on: one row per month,
-- however many times the task runs.
CREATE TABLE IF NOT EXISTS globalbank_dev.gold.month_end
  (month STRING, accounts BIGINT, deposits_eur DECIMAL(18,2));
INSERT INTO globalbank_dev.gold.month_end REPLACE WHERE month = :month
SELECT month, count(*), sum(closing)
FROM globalbank_dev.gold.monthly_statements WHERE month = :month
GROUP BY month
"""

COUNT_SQL = """-- The month-end table, as the ledger reads it.
SELECT month, accounts, deposits_eur FROM globalbank_dev.gold.month_end
"""

q = lambda c: c + ' > /dev/null'
J = 'python -m globalbank.job'
LAND = [RESET, CAT, 'bash land.sh 2026-10-31 > /dev/null', 'bash land.sh 2026-09-01 core_cdc 2026-10-31 > /dev/null',
        'bash land.sh 2026-09-01 postings 2026-10-31 > /dev/null', 'bash land.sh 2026-10-01 chargebacks > /dev/null']
SETTLED = ['bash land.sh 2026-09-02 settlements 2026-10-31 > /dev/null']
UP = [q('python -m globalbank.deploy')]
BASE = LAND + SETTLED + UP
GO = {'continues': True}  # from the workspace as the step before left it

if __name__ == '__main__':
    step(P, '01-nightly', PARENT, ['requirements.txt', 'resources/nightly.yml', 'sql/fraud/flags.sql',
                                   'jobs/check.py', 'globalbank/job.py'],
         {'requirements.txt': REQUIREMENTS, 'resources/nightly.yml': nightly(), 'sql/fraud/flags.sql': FLAGS,
          'jobs/check.py': CHECK, 'globalbank/job.py': JOB},
         [f'{J} deploy'], BASE)
    step(P, '02-run', f'{P}/01-nightly', ['globalbank/job.py'], {'globalbank/job.py': JOB + JOB_WAIT},
         [f'{J} run'], [q(f'{J} deploy')], extra={**GO, 'volatile': ['digits']})
    step(P, '03-file-arrival', f'{P}/02-run', ['resources/nightly.yml'], {'resources/nightly.yml': nightly(trigger=True)},
         [f'{J} deploy | sed -n 1p', 'sleep 90', 'bash land.sh 2026-11-01 settlements | wc -l', f'{J} wait'],
         [], extra=GO)
    step(P, '04-repair', f'{P}/03-file-arrival', ['globalbank/job.py'], {'globalbank/job.py': JOB + JOB_WAIT + JOB_REPAIR},
         [f'{J} run', 'bash land.sh 2026-10-31 settlements | wc -l', f'{J} repair'],
         LAND + ['bash land.sh 2026-09-02 settlements 2026-10-30 > /dev/null'] + UP + [q(f'{J} deploy')])
    step(P, '05-idempotency', f'{P}/04-repair', ['resources/nightly.yml', 'sql/gold/month_end.sql', 'sql/gold/month_end_rows.sql'],
         {'resources/nightly.yml': nightly(trigger=True, month_end=True), 'sql/gold/month_end.sql': MONTH_END,
          'sql/gold/month_end_rows.sql': COUNT_SQL},
         [f'{J} run | sed -n 1p', f'{J} run | sed -n 1p', 'python -m globalbank.warehouse sql/gold/month_end_rows.sql'],
         [q(f'{J} wait'), q(f'{J} deploy')], extra=GO)  # a run the 31st's file started, finished first
    step(P, '06-parameters', f'{P}/05-idempotency', ['resources/nightly.yml', 'sql/gold/month_end.sql', 'globalbank/job.py'],
         {'resources/nightly.yml': nightly(trigger=True, month_end=True, params=True), 'sql/gold/month_end.sql': MONTH_END_FIXED,
          'globalbank/job.py': JOB + JOB_WAIT + JOB_REPAIR + JOB_OUTPUT},
         [f'{J} run run_date=2026-10-31 | sed -n 1p', f'{J} run run_date=2026-10-31 | sed -n 1p', f'{J} output check',
          'python -m globalbank.warehouse sql/gold/month_end_rows.sql'],
         [q(f'{J} deploy')], extra=GO)
    step(P, '07-run-as', f'{P}/06-parameters', ['resources/nightly.yml', 'globalbank/job.py'],
         {'resources/nightly.yml': nightly(trigger=True, month_end=True, params=True, owner=True),
          'globalbank/job.py': JOB + JOB_WAIT + JOB_REPAIR + JOB_OUTPUT + JOB_WHO},
         [f'{J} deploy | sed -n 1p', f'{J} who'], [], extra=GO)
    print('built')
