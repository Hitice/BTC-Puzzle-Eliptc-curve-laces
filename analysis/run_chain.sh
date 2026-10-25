#!/bin/zsh
# Cadeia completa: H9 -> H10 -> refazer JSONs antigos (anchor_only) -> fila base -> H2.
cd "$(dirname "$0")/.."
export JOBS=${JOBS:-8}
echo "### CHAIN START :: $(date -u +%FT%TZ)"
./analysis/run_sweeps_h9.sh  >> analysis/sweeps/run-h9.log  2>&1
./analysis/run_sweeps_h10.sh >> analysis/sweeps/run-h10.log 2>&1
python3 analysis/rerun_old_sweeps.py --run --jobs $JOBS >> analysis/sweeps/run-rerun.log 2>&1
./analysis/run_sweeps.sh     >> analysis/sweeps/run.log     2>&1
./analysis/run_sweeps_h2.sh  >> analysis/sweeps/run-h2.log  2>&1
echo "### CHAIN END :: $(date -u +%FT%TZ)"
