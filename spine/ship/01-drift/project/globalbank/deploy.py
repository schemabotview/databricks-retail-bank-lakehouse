"""Deploy globalbank_pipeline: upload pipelines/*.py, create or update it."""
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.pipelines import FileLibrary, PipelineLibrary
from databricks.sdk.service.workspace import ImportFormat

NAME = 'globalbank_pipeline'


def deploy(w):
    folder = f'/Workspace/Users/{w.current_user.me().user_name}/globalbank'
    w.workspace.mkdirs(f'{folder}/pipelines')
    sources = sorted(Path('pipelines').glob('*.py'))
    for source in sources:
        w.workspace.upload(f'{folder}/{source}', source.open('rb'),
                           format=ImportFormat.RAW, overwrite=True)
    settings = dict(
        name=NAME, serverless=True, catalog='globalbank_dev', schema='bronze',
        libraries=[PipelineLibrary(file=FileLibrary(path=f'{folder}/{s}'))
                   for s in sources])
    found = list(w.pipelines.list_pipelines(filter=f"name LIKE '{NAME}'"))
    if found:
        w.pipelines.update(found[0].pipeline_id, **settings)
        return found[0].pipeline_id, 'updated', sources
    return w.pipelines.create(**settings).pipeline_id, 'created', sources


if __name__ == '__main__':
    _, verb, sources = deploy(WorkspaceClient())
    print(f"{NAME}: {verb}, {len(sources)} source file(s):"
          f" {', '.join(s.name for s in sources)}")
