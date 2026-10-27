#!/usr/bin/env bash
# The nightly run, by hand: one script after another, in the order typed.
set -euo pipefail

day=$1
bash land.sh "$day" > /dev/null
bash land.sh "$day" core_cdc > /dev/null
python -m globalbank.ledger post "$day"        # silver: card transactions
python -m globalbank.land                       # bronze: card authorizations
python -m globalbank.land core_cdc              # bronze: core changes
python -m globalbank.cdc customers "$day"       # silver: customers
