#!/bin/zsh
# Fila RAPIDA: seeds plausiveis para um humano, itens de segundos a poucos minutos.
# Ordem por plausibilidade, nao por familia. Ideia: se a seed foi escolhida por uma
# pessoa (numero pequeno, data, timestamp do dia), ela esta aqui, nao no meio de 2^32.
# Cada linha e decisiva (ancora #130 + 81 confirmacoes; anchor_only registrado).
set -e
cd "$(dirname "$0")/.."
# Pausa as filas longas (SIGSTOP, sem perda) enquanto esta roda; retoma ao sair.
./analysis/sweep_ctl.sh pause >/dev/null 2>&1 || true
pkill -STOP -f bx2_mi_sweep 2>/dev/null || true
pkill -STOP -f pyrandom_range_sweep.py 2>/dev/null || true
resume_all() { ./analysis/sweep_ctl.sh resume >/dev/null 2>&1 || true; pkill -CONT -f bx2_mi_sweep 2>/dev/null || true; pkill -CONT -f pyrandom_range_sweep.py 2>/dev/null || true; }
trap resume_all EXIT INT TERM
O=analysis/sweeps/fast
mkdir -p $O
J=${JOBS:-8}
run() {
  local o=${argv[${argv[(i)--output]}+1]}
  if [[ -s $o ]]; then echo "### SKIP (ja existe $o)"; return 0; fi
  echo "### $* :: $(date -u +%FT%TZ)"; nice -n 0 python3 analysis/master_seed_sweep.py --jobs $J "$@" ;
}
# janelas
SMALL=0-1048576                         # inteiros pequenos (seed(42), seed(2015), ...)
DAY=1421258834-1421431634               # +-1 dia do bloco 339085 (1421345234), em segundos
WEEK=1420740434-1421950034              # +-7 dias, em segundos
MS=1421341634000-1421348834000          # +-1 h em milissegundos
US=1421345000000000-1421345500000000    # +-250 s em microssegundos (so hashseq)
BLK=338000-340000                       # alturas de bloco
DATES=(20150100-20150200 15012015-15012016 1152015-1152016 20140101-20160101 1012013-1012016 2013-2016)

for fam in "--family hashseq --hash sha256 --index-enc be4" "--family hashseq --hash sha256 --index-enc str" "--family hashseq --hash sha256d --index-enc be4" \
           "--family bip32 --path m/ih" "--family bip32 --path m/0h/i" \
           "--family bip32 --path m/i" "--family bip32 --path m/0/i" "--family bip32 --path m/0h/0/i" "--family bip32 --path m/44h/0h/0h/0/i"; do
  for enc in raw4be ascii sha256 mt256 int256 asciihex; do
    tag=$(echo $fam | sed 's/--family //; s/ --hash /-/; s/ --index-enc /-/; s/ --path /-/; s#/#_#g')
    run ${=fam} --encoder $enc --range $SMALL --output $O/$tag-$enc-small.json
    run ${=fam} --encoder $enc --range $DAY   --output $O/$tag-$enc-day.json
    run ${=fam} --encoder $enc --range $BLK   --output $O/$tag-$enc-blk.json
    for d in $DATES; do run ${=fam} --encoder $enc --range $d --output $O/$tag-$enc-date-${d%%-*}.json; done
  done
done
# timestamps em ms/us (encoders de 8 bytes e texto) nas familias baratas
for enc in raw8be ascii sha256; do
  for fam in "--family hashseq --hash sha256 --index-enc be4" "--family hashseq --hash sha256 --index-enc str" "--family bip32 --path m/ih" "--family bip32 --path m/0h/i"; do
    tag=$(echo $fam | sed 's/--family //; s/ --hash /-/; s/ --index-enc /-/; s/ --path /-/; s#/#_#g')
    run ${=fam} --encoder $enc --range $MS --output $O/$tag-$enc-ms1h.json
  done
done
# semana inteira em segundos nas familias baratas
for enc in raw4be ascii sha256 mt256; do
  for fam in "--family hashseq --hash sha256 --index-enc be4" "--family hashseq --hash sha256 --index-enc str" "--family bip32 --path m/ih" "--family bip32 --path m/0h/i"; do
    tag=$(echo $fam | sed 's/--family //; s/ --hash /-/; s/ --index-enc /-/; s/ --path /-/; s#/#_#g')
    run ${=fam} --encoder $enc --range $WEEK --output $O/$tag-$enc-week.json
  done
done
# H11 nas mesmas janelas
for r in "$SMALL small" "$DAY day" "$BLK blk"; do
  set -- ${=r}
  o=$O/pyrandom-int-$2.json
  if [[ -s $o ]]; then echo "### SKIP $o"; else
    echo "### pyrandom --range $1 :: $(date -u +%FT%TZ)"; nice -n 0 python3 analysis/pyrandom_range_sweep.py --jobs $J --seed-kind int --range $1 --orders asc --output $o
  fi
done
echo "### FIM FAST :: $(date -u +%FT%TZ)"
