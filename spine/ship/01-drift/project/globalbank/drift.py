"""Has the deployed job drifted from resources/nightly.yml? Someone clicks."""
from databricks.sdk import WorkspaceClient

from globalbank.job import NAME, job_id

w = WorkspaceClient()
deployed = w.jobs.get(job_id(w)).settings  # as job.py deployed it from the repo
# What a person did in the web UI, done here as the API call the UI makes:
edited = w.jobs.get(job_id(w)).settings
edited.max_concurrent_runs = 3
edited.tags = {'edited': 'by hand'}
w.jobs.reset(job_id(w), new_settings=edited)
print(f'{NAME}, edited in the workspace')

code, live = deployed.as_dict(), w.jobs.get(job_id(w)).settings.as_dict()
for key in sorted(set(code) | set(live)):
    if code.get(key) != live.get(key):
        print(f'  {key:<20} repo: {code.get(key, "-")!s:<10}'
              f' workspace: {live.get(key)}')
print('resources/nightly.yml: unchanged; nothing records the edit')
