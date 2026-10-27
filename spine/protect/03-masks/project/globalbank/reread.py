"""The naive way: read every file in the volume, on every run."""
from globalbank.session import get_spark

SOURCE = '/Volumes/globalbank_dev/landing/card_auths/'

spark = get_spark()
auths = spark.read.json(SOURCE + '*/')  # every day's folder
files = auths.select('_metadata.file_path').distinct().count()
print(f'read {auths.count():,} rows from {files} files')
