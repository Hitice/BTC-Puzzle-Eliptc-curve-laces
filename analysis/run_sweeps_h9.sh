#!/bin/zsh
# H9: `bx seed` do libbitcoin-explorer 2.0.0 (random_fill: default_random_engine semeado por
# UMA chamada de random_device, byte = engine() % 255). Caminhos endurecidos (sem k*G):
# m/ih (`bx hd-private --hard`) e m/0h/i. m/i (padrao) precisa de EC rapida; fica fora daqui.
# minstd/minstd0: estado mod 2^31-1 -> 2^31-2 seeds. mt19937 (MSVC): 2^32 seeds.
set -e
cd "$(dirname "$0")/.."
O=analysis/sweeps
J=${JOBS:-8}
# Pula itens ja concluidos: o JSON de saida so e gravado ao fim da varredura.
run() {
  local o=${argv[${argv[(i)--output]}+1]}
  if [[ -s $o ]]; then echo "### SKIP (ja existe $o) :: $*"; return 0; fi
  echo "### $* :: $(date -u +%FT%TZ)"; nice -n 19 python3 analysis/master_seed_sweep.py --jobs $J "$@" ;
}
for enc in bx2-minstd0 bx2-minstd bx2-minstd0-256 bx2-minstd-256; do
  run --family bip32 --path m/ih   --encoder $enc --range 1-2147483647 --output $O/h9-bip32-mih-$enc.json
done
run --family bip32 --path m/ih --encoder bx2-mt19937 --range 0-4294967296 --output $O/h9-bip32-mih-bx2-mt19937.json
for enc in bx2-minstd0 bx2-minstd; do
  run --family bip32 --path m/0h/i --encoder $enc --range 1-2147483647 --output $O/h9-bip32-m0h-i-$enc.json
done
echo "### FIM H9 :: $(date -u +%FT%TZ)"
