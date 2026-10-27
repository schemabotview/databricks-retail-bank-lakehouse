#!/usr/bin/env bash
# Land a source's files for a day, or a range of days: generate them as the
# source sends them, then copy them into its landing volume, as they are.
set -euo pipefail

first=$1
source=${2:-card_auths}
last=${3:-$first}
batch=landing/.batch  # only this run's files

rm -rf "$batch"
python -m globalbank_sim --out "$batch" --from "$first" --to "$last" \
  --only "$source"
databricks fs cp -r "$batch/$source" \
  "dbfs:/Volumes/globalbank_dev/landing/$source"
