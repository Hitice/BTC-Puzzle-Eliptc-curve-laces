#!/bin/zsh
# H10: cadeia deterministica do Armory (wallet 1.35) com raiz de fonte enumeravel.
# Cada linha e decisiva (82 chaves conferidas em ordem de indice; ancora #130).
# Custo ~2,6 k*G por candidato errado (rejeicao pelos puzzles pequenos).
set -e
cd "$(dirname "$0")/.."
O=analysis/sweeps
J=${JOBS:-8}
T0=1356998400
T1=1421345235
# Pula itens ja concluidos: o JSON de saida so e gravado ao fim da varredura.
run() {
  local o=${argv[${argv[(i)--output]}+1]}
  if [[ -s $o ]]; then echo "### SKIP (ja existe $o) :: $*"; return 0; fi
  echo "### $* :: $(date -u +%FT%TZ)"; nice -n 19 python3 analysis/master_seed_sweep.py --jobs $J "$@" ;
}

# raiz = inteiro pequeno (restauracao com chave escolhida), k_0 e o 1o endereco
run --family armory --encoder int256 --range 1-0x1000000 --output $O/h10-armory-int256-24.json
# mesma raiz, contando o proprio root como indice 0
run --family armory --armory-root --encoder int256 --range 1-0x1000000 --output $O/h10-armory-root0-int256-24.json
# #1-#4 parecem feitas a mao (1, 11, 111, 1000 em binario): carteira comeca no #4 ou #5
run --family armory --encoder int256 --index-base=-3 --skip-below 4 --range 1-0x1000000 --output $O/h10-armory-int256-24-from4.json
run --family armory --encoder int256 --index-base=-4 --skip-below 5 --range 1-0x1000000 --output $O/h10-armory-int256-24-from5.json
# raiz = sha256(str(i)) (estilo brainwallet de numero)
run --family armory --encoder sha256 --range 0-0x1000000 --output $O/h10-armory-sha256-24.json
# raiz = random.seed(timestamp) do Python, janela 2013-01-01 .. financiamento
run --family armory --encoder mt256 --range $T0-$T1 --output $O/h10-armory-mt256-time.json
echo "### FIM H10 :: $(date -u +%FT%TZ)"
