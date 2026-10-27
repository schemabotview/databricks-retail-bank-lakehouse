"""One way in: a Spark session on the workspace's serverless compute."""
from databricks.connect import DatabricksSession


def get_spark():
    # Host and token come from the environment (DATABRICKS_HOST and
    # DATABRICKS_TOKEN) or a profile in ~/.databrickscfg: never this file.
    return DatabricksSession.builder.serverless().getOrCreate()
