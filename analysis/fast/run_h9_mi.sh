#!/bin/zsh
# H9, caminhos com ultimo nivel NAO endurecido (m/i = padrao de `bx hd-private`), varredor em C.
# Testa so a ancora #130 com offsets de indice -4..+4 e as 3 mascaras; acerto e conclusivo (2^-129)
# e deve ser confirmado com verify_hit.py. Saida: analysis/sweeps/h9mi-<path>-<encoder>.txt (DONE no fim).
set -e
cd "$(dirname "$0")/../.."
O=analysis/sweeps
B=analysis/fast/bx2_mi_sweep
T=$(python3 -c "import sys; sys.path.insert(0,'analysis'); from master_seed_sweep import load_solved; print('%x'%load_solved()[130])")
TH=${THREADS:-8}
run() { # path encoder range
  local tag=${1//\//_}; local out=$O/h9mi-$tag-$2.txt
  if [[ -s $out ]] && grep -q '^DONE' $out; then echo "### SKIP (ja existe $out)"; return 0; fi
  : > $out
  echo "### --path $1 --encoder $2 --range $3 :: $(date -u +%FT%TZ)"
  nice -n 5 $B --path $1 --encoder $2 --range $3 --threads $TH --offsets -4,-3,-2,-1,0,1,2,3,4 --target $T --out $out
}
for p in m/i m/0/i m/0h/i; do
  for e in bx2-minstd0 bx2-minstd bx2-minstd0-256 bx2-minstd-256; do run $p $e 1-2147483647; done
  run $p bx2-mt19937 0-4294967296
done
echo "### FIM H9-mi :: $(date -u +%FT%TZ)"
