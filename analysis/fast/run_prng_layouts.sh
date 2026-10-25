#!/bin/zsh
# PRNGs nao criptograficos como material direto de chave (prng_layout_sweep). Itens 2, 3, 4, A e B.
# Pausa as filas longas enquanto roda; retoma ao sair.
set -e
cd "$(dirname "$0")/../.."
./analysis/sweep_ctl.sh pause >/dev/null 2>&1 || true
pkill -STOP -f bx2_mi_sweep 2>/dev/null || true
resume_all() { ./analysis/sweep_ctl.sh resume >/dev/null 2>&1 || true; pkill -CONT -f bx2_mi_sweep 2>/dev/null || true; }
trap resume_all EXIT INT TERM
B=analysis/fast/prng_layout_sweep
K=analysis/fast/solved_keys_le128.txt
O=analysis/sweeps/prng
mkdir -p $O
TH=${THREADS:-8}
run() { # gen range tag
  local out=$O/$1-$3.txt
  if [[ -s $out ]] && grep -q '^DONE' $out; then echo "### SKIP $out"; return 0; fi
  : > $out; echo "### --gen $1 --range $2 ($3) :: $(date -u +%FT%TZ)"
  nice -n 0 $B --gen $1 --range $2 --keys $K --threads $TH --out $out
}
SMALL=0-1048576; DAY=1421258834-1421431634; M30=1418753234-1423937234; FULL=0-4294967296
# item 2 e 3: janelas plausiveis
for g in glibc msvc pm mtnp mtphp; do run $g $SMALL small; run $g $DAY day; run $g $M30 30d; done
# A: V8 2013-2015 (Chrome 28-48 / Node 0.12), espaco completo de s0
run v8 $FULL full
# item 4: SpiderMonkey/Java LCG48 por recuperacao de estado (word: 2^22; byte: 2^40 por combinacao)
out=$O/lcg48-recover-word.txt
if ! { [[ -s $out ]] && grep -q '^DONE' $out; }; then : > $out; echo "### lcg48 recover word :: $(date -u +%FT%TZ)"; nice -n 0 $B --gen lcg48 --recover --keys $K --threads $TH --units word --out $out; fi
# B: libc completos
for g in glibc msvc pm; do run $g $FULL full; done
# MT completos
for g in mtnp mtphp; do run $g $FULL full; done
# item 4, bytes: fit primeiro (mais plausivel: hex/bytes por puzzle), depois s256
for ch in fit s256; do for od in be le; do for mk in low high; do
  out=$O/lcg48-recover-byte-$ch-$od-$mk.txt
  if [[ -s $out ]] && grep -q '^DONE' $out; then echo "### SKIP $out"; continue; fi
  : > $out; echo "### lcg48 recover byte $ch $od $mk :: $(date -u +%FT%TZ)"
  nice -n 0 $B --gen lcg48 --recover --keys $K --threads $TH --units byte --chunks $ch --orders $od --masks $mk --out $out
done; done; done
echo "### FIM PRNG :: $(date -u +%FT%TZ)"
