#!/bin/zsh
# H2: cobertura das variantes de mascara e de mapa de indice.
# Cada linha e decisiva (ancora de 129 bits no #130 + 81 confirmacoes).
set -e
cd "$(dirname "$0")/.."
O=analysis/sweeps
J=${JOBS:-8}
T0=1356998400
T1=1421345235
run() { echo "### $* :: $(date -u +%FT%TZ)"; python3 analysis/master_seed_sweep.py --jobs $J "$@" ; }

# --- variantes de mascara, gerador indexado, todas as seeds de 32 bits ---
run --family hashseq --encoder raw4be --mask high   --range 0-0x100000000 --output $O/h2-hashseq-mask-high.json
run --family hashseq --encoder raw4be --mask low_le --range 0-0x100000000 --output $O/h2-hashseq-mask-lowle.json
# --- variantes de indice ---
run --family hashseq --encoder raw4be --index-base 1              --range 0-0x100000000 --output $O/h2-hashseq-base1.json
run --family hashseq --encoder raw4be --index-map reverse         --range 0-0x100000000 --output $O/h2-hashseq-reverse.json
run --family hashseq --encoder raw4be --index-map rejection       --range 0-0x40000000  --output $O/h2-hashseq-rejection.json
# --- BIP32 endurecido sob as mesmas variantes, janela de timestamps ---
run --family bip32 --path "m/0h/i" --encoder mt256 --mask high      --range $T0-$T1 --output $O/h2-bip32-m0h-high.json
run --family bip32 --path "m/0h/i" --encoder mt256 --index-map reverse   --range $T0-$T1 --output $O/h2-bip32-m0h-reverse.json
run --family bip32 --path "m/0h/i" --encoder mt256 --index-map rejection --range $T0-$T1 --output $O/h2-bip32-m0h-rejection.json
run --family bip32 --path "m/ih"   --encoder mt256 --mask high      --range 0-0x100000000 --output $O/h2-bip32-mih-high.json
echo "### FIM H2 :: $(date -u +%FT%TZ)"
