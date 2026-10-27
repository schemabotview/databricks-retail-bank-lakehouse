#!/usr/bin/env bash
# Land one day of a source: generate its files for that day, then copy
# them into the source's landing volume, as they are.
set -euo pipefail

day=$1
source=${2:-card_auths}
volume=dbfs:/Volumes/globalbank_dev/landing/$source

python -m globalbank_sim --out landing --from "$day" --to "$day" \
  --only "$source"
if [ -d "landing/$source/$day" ]; then  # a folder per day
  databricks fs cp -r "landing/$source/$day" "$volume/$day"
else                                     # a file per day
  databricks fs cp "landing/$source/$source-$day.csv" "$volume/"
fi
