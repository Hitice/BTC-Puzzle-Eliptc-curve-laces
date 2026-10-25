#!/bin/zsh
# H11: random do Python sorteando cada chave direto na faixa (pyrandom_range_sweep.py).
set -e
cd "$(dirname "$0")/.."
O=analysis/sweeps
J=${JOBS:-6}
T0=1356998400
T1=1421345235
run() {
  local o=${argv[${argv[(i)--output]}+1]}
  if [[ -s $o ]]; then echo "### SKIP (ja existe $o) :: $*"; return 0; fi
  echo "### $* :: $(date -u +%FT%TZ)"; nice -n 10 python3 analysis/pyrandom_range_sweep.py --jobs $J "$@" ;
}
# 1) seed = timestamp em segundos (2013-01-01 .. financiamento), ordem ascendente
run --seed-kind int --range $T0-$T1 --orders asc --output $O/h11-pyrandom-int-time-asc.json
# 2) seeds pequenas (0 .. 2^24), as duas ordens
run --seed-kind int --range 0-16777216 --output $O/h11-pyrandom-int-24.json
# 3) frases (dicionario + tematico), semeadura do Python 3 e do Python 2
run --seed-kind py3str --dict --output $O/h11-pyrandom-py3str-dict.json
run --seed-kind py2str --dict --output $O/h11-pyrandom-py2str-dict.json
# 4) timestamp em segundos, ordem descendente
run --seed-kind int --range $T0-$T1 --orders desc --output $O/h11-pyrandom-int-time-desc.json
echo "### FIM H11 :: $(date -u +%FT%TZ)"
