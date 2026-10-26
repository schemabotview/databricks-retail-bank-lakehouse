#!/usr/bin/env bash
# Install the course's pinned toolchain, as on a learner's machine (COURSE-PLAN.md, "Pinned versions"):
#   CPython 3.12.15 in /usr/local as `python3.12` — databricks-connect 18.3 (serverless environment
#     version 5) requires Python 3.12, so the course runs on 3.12, not the Spark course's 3.14.
#     `python` is NOT relinked: the Spark and Python courses own it on a shared machine; the spine
#     puts a `python` → python3.12 link first on PATH for its replays.
# The Databricks CLI is added here when Course 2 pins it (it needs a workspace to show anything).
# Usable as a cloud environment's setup script. Needs network access to PyPI and GitHub.
set -euo pipefail
PIN=3.12.15
if [ "$(python3.12 -c 'import platform; print(platform.python_version())' 2>/dev/null)" != "$PIN" ]; then
  work=$(mktemp -d)
  python3 -m pip download "uv==0.13.5" --no-deps -q -d "$work"
  python3 -m zipfile -e "$work"/uv-*.whl "$work/uv"
  uv=$(find "$work/uv" -path '*data/scripts/uv'); chmod +x "$uv"
  "$uv" python install "$PIN" --install-dir "$work/py"
  # Copy the interpreter's own files only: its bin/python and bin/python3 would shadow the system's.
  src="$work/py/cpython-$PIN-linux-x86_64-gnu"
  cp -a "$src/lib/." /usr/local/lib/
  cp -a "$src/include/." /usr/local/include/ 2>/dev/null || true
  cp -a "$src/bin/python3.12" /usr/local/bin/python3.12
  rm -f ~/.local/bin/python3.12  # uv links it AHEAD of /usr/local/bin on PATH
  rm -rf "$work"
fi
python3.12 -c 'import platform; assert platform.python_version() == "'$PIN'"'
echo "python3.12 $PIN in /usr/local"
