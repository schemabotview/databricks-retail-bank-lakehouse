"""The nightly job: deploy | run [k=v] | wait | repair | output | who."""
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
FILES = ['sql/gold/daily_balances.sql', 'sql/gold/monthly_statements.sql',
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
              + (t.state.state_message or '')[:48].split('\n')[0])


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
