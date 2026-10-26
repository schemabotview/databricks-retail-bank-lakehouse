#!/usr/bin/env bash
# Start a spine step from its parent: scripts/newstep.sh <course/NN-name> <parent course/NN-name>
# Copies the parent's project; write step.json and session.txt yourself.
set -euo pipefail
step=spine/$1 parent=spine/$2
rm -rf "$step"; mkdir -p "$step"
cp -r "$parent/project" "$step/project"
find "$step/project" -name __pycache__ -prune -exec rm -rf {} +
