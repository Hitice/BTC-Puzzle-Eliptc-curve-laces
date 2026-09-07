#!/bin/zsh
# Fila de varreduras de seed mestre. Cada linha e decisiva: ancora de 129 bits
# no puzzle #130 + confirmacao nas outras 81 chaves. Falso positivo ~2^-129.
set -e
cd "$(dirname "$0")/.."
O=analysis/sweeps
J=${JOBS:-8}
# Janela de tempo plausivel: 2013-01-01 ate a tx de financiamento (2015-01-15).
T0=1356998400
T1=1421345235

run() { echo "### $* :: $(date -u +%FT%TZ)"; python3 analysis/master_seed_sweep.py --jobs $J "$@" ; }

# 1) gerador ingenuo indexado, TODAS as seeds de 32 bits
run --family hashseq --hash sha256  --index-enc be4 --encoder raw4be --range 0-0x100000000 --output $O/hashseq-sha256-be4-raw32.json
run --family hashseq --hash sha256d --index-enc be4 --encoder raw4be --range 0-0x100000000 --output $O/hashseq-sha256d-be4-raw32.json
run --family hashseq --hash sha256  --index-enc str --encoder ascii  --range $T0-$T1     --output $O/hashseq-sha256-str-ascii-time.json
# 2) BIP32 endurecido (sem custo de EC), todas as seeds MT de 32 bits
run --family bip32 --path "m/ih"  --encoder mt256 --range 0-0x100000000 --output $O/bip32-mih-mt256-32.json
run --family bip32 --path "m/0h/i" --encoder mt256 --range $T0-$T1 --output $O/bip32-m0h-i-mt256-time.json
# 3) BIP32 nao-endurecido, seed derivada de random.seed(timestamp)
run --family bip32 --path "m/0/i" --encoder mt256 --range $T0-$T1 --output $O/bip32-m0-i-mt256-time.json
run --family bip32 --path "m/i"   --encoder mt256 --range $T0-$T1 --output $O/bip32-mi-mt256-time.json
echo "### FIM :: $(date -u +%FT%TZ)"
