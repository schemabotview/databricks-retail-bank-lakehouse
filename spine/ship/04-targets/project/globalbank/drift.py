"""Has the deployed job drifted from resources/nightly.yml? Someone clicks."""
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.jobs import JobSettings

from globalbank.job import NAME, job_id, settings

w = WorkspaceClient()
# What a person did in the web UI, done here as the API call the UI makes:
edited = w.jobs.get(job_id(w)).settings
edited.max_concurrent_runs = 3
edited.tags = {'edited': 'by hand'}
w.jobs.reset(job_id(w), new_settings=edited)
print(f'{NAME}, edited in the workspace')

code = settings(w).as_dict()
live = w.jobs.get(job_id(w)).settings.as_dict()
for key in sorted(set(code) | set(live)):
    if key in ('tasks', 'environments') or code.get(key) == live.get(key):
        continue
    print(f'  {key:<20} repo: {code.get(key, "-")!s:<10}'
          f' workspace: {live.get(key)}')
