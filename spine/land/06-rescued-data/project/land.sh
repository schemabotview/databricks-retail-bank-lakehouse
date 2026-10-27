#!/usr/bin/env bash
# Land one day of card authorizations: generate the processor's files
# for that day, then copy them into the landing volume, as they are.
set -euo pipefail

day=$1
volume=dbfs:/Volumes/globalbank_dev/landing/card_auths

python -m globalbank_sim --out landing --from "$day" --to "$day" \
  --only card_auths
databricks fs cp -r "landing/card_auths/$day" "$volume/$day"
