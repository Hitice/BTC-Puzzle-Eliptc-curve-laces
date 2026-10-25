#!/bin/zsh
# Item 3: MT19937 com semeadura/saida de numpy e PHP 5 (ruby == numpy para seeds de 32 bits).
set -e
cd "$(dirname "$0")/.."
O=analysis/sweeps
J=${JOBS:-8}
run() { local o=${argv[${argv[(i)--output]}+1]}; [[ -s $o ]] && { echo "### SKIP $o"; return 0; }
  echo "### $* :: $(date -u +%FT%TZ)"; nice -n 0 python3 analysis/mt_variants_sweep.py --jobs $J --gens numpy,php "$@"; }
run --range 0-1048576 --output $O/mtvar-numpy-php-small.json
run --range 1418753234-1423937234 --output $O/mtvar-numpy-php-30d.json
echo "### FIM MTVAR :: $(date -u +%FT%TZ)"
