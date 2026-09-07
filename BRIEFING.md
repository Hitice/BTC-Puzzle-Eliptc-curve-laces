# BRIEFING — ponto de entrada único

> **Para a IA que abrir este repositório: leia SÓ este arquivo antes de agir.**
> Ele é auto-suficiente. Os outros documentos são histórico e custam ~44 k tokens
> juntos; a lista do que NÃO ler está na seção 7. Rode `python3 analysis/status.py`
> para o estado atual em vez de ler resultados em prosa.

## 1. Objetivo

Bitcoin Puzzle (saatoshi_rising, 2015): 256 chaves privadas, a de índice `n` em
`[2^(n-1), 2^n)`, com BTC depositado. Objetivo deste workspace: **encontrar um
caminho de solução que não seja força bruta nem Kangaroo**, porque nenhum dos dois
é viável para um usuário com um MacBook M3 (#71 ≈ 4,7 milhões de anos).

Declaração do criador (2017): *"There is no pattern. It is just consecutive keys
from a deterministic wallet (masked with leading 000...0001 to set difficulty)."*

Modelo de máscara assumido em todo o repo:
```
puzzle_n = 2^(n-1) | (child_{base + n - 1} mod 2^(n-1))
```

## 2. Estado em uma linha

Nenhuma chave nova recuperada. A implementação do gerador de 2015 não foi
identificada. **A hipótese do gerador continua aberta — não por falta de testes,
mas porque quase todos os testes feitos não tinham poder contra ela.**

## 3. A regra que governa este repositório

> **Nenhuma hipótese pode ser marcada como fechada sem um controle positivo
> executado: uma instância sintética que o teste comprovadamente detecta.
> Sem isso, o resultado é "sem poder", não "negativo".**

Motivo: `child_i = m + H(...)` em qualquer carteira determinística aditiva (BIP32,
Electrum v1). As diferenças entre chaves de puzzle são pseudo-aleatórias tanto com
seed de 256 bits quanto com seed de 16. Foi demonstrado: um conjunto sintético
BIP32 com seed de 32 bits (quebrável em 22 s) **passa em todos** os testes
estatísticos do repo — `weak_generator_scan` imprime "REJEITADO", `gap_analysis`
imprime "LCG negativo", a compressão dá o mesmo ratio que ruído puro.
Detalhes: [analysis/AUDITORIA_PODER.md](analysis/AUDITORIA_PODER.md).

Todo teste vive em `HYPOTHESES.json`, com espaço enumerado, controle positivo,
cobertura e resultado. **Atualize esse arquivo, não crie novos .md de conclusão.**

## 4. Fatos verificados (pode confiar, foram reconferidos)

| Fato | Como foi verificado |
|---|---|
| 82 chaves resolvidas ↔ endereços | 82/82 conferem, todas P2PKH **comprimidas** |
| 96 pubkeys dos #161–#256 | extraídas do gasto de 2017, cada uma confere com seu endereço, todas na curva, 96 `r` distintos |
| #135 está **resolvido** (fundos gastos) | on-chain, bloco 960138. Chave privada não publicada |
| #71 não resolvido | on-chain: 58 saídas recebidas, 0 gastas |
| Alvos com pubkey exposta hoje | **[140, 145, 150, 155, 160]** |
| Nonces de 2019 | 15/15 batem RFC 6979 (auditoria anterior). Não diz nada sobre 2015 |
| As 256 saídas de 2015 estão em ordem de índice | valores estritamente crescentes, 256 valores distintos |

## 5. Datasets (use estes, não os .md)

| Arquivo | Conteúdo |
|---|---|
| `data/puzzles.json` | 160 puzzles, machine-readable. **Fonte de verdade** |
| `data/puzzles_161_256.json` | 96 pubkeys + assinaturas dos #161–#256 (gasto de 2017) + entrada de financiamento do criador |
| `data/creator_txs.json` | indicadores forenses das 5 transações do criador (2015/2017/2019×2/2023) |
| `data/signatures.json` | assinaturas do gasto de 2019 (20 endereços) |
| `analysis/sweeps/*.json` | cobertura já varrida do espaço de seeds |

## 6. Ferramentas prontas

| Ferramenta | O que faz |
|---|---|
| `analysis/master_seed_sweep.py` | **o único teste com poder.** Enumera seeds mestres. Âncora: puzzle #130, 129 bits, em **uma** derivação; falso positivo 2⁻¹²⁹. Confirma nas outras 81 chaves. Famílias: `bip32` (caminho arbitrário), `hashseq`, `hashchain`, `electrum1`. Máscaras `--mask low\|high\|low_le`, índices `--index-map consecutive\|reverse\|rejection` com `--index-base`/`--index-stride`. Controles **20/20** |
| `analysis/secp_fast.py` | secp256k1 com comb de base fixa, 122 µs por `k*G` |
| `analysis/run_sweeps.sh` | fila base (máscara `low`, índice consecutivo) → `analysis/sweeps/` |
| `analysis/run_sweeps_h2.sh` | fila das variantes de máscara e índice (H2) |
| `analysis/creator_tx_forensics.py` | indicadores forenses das transações do criador |
| `analysis/status.py` | estado atual em um comando |

Taxas medidas (M3, 8 processos): `hashseq` 5,3 M/s · BIP32 endurecido ~800 k/s ·
BIP32 com um `k*G` ~16 k/s · `electrum1` ~250/s.

```bash
python3 analysis/status.py                      # estado
python3 analysis/master_seed_sweep.py --self-test   # controles, ~40 s
./analysis/run_sweeps.sh                        # fila padrão
```

## 7. NÃO leia estes arquivos (e por quê)

| Arquivo | ~tokens | Por quê |
|---|---:|---|
| `analysis/FINDINGS.md` | 5.500 | conclusões sem poder; corrigidas na AUDITORIA_PODER |
| `analysis/REFORMULATIONS.md` | 5.900 | especulação sobre complexidade de Kolmogorov; não gera teste |
| `data/solved.md`, `data/unsolved.md` | 11.000 | dumps humanos; use `data/puzzles.json` |
| `data/challenge.md` | 5.500 | scrape de site; os fatos úteis estão na seção 4 |
| `SUMMARY.md`, `analysis/FRONTIER.md` | 3.900 | histórico; a tabela "hipóteses descartadas" é enganosa (seção 3) |

Leia sob demanda, e só se for mexer naquilo especificamente:
`breach-review/REVISAO.md` (bugs de ECDSA e reticulados),
`analysis/GENERATOR_CONTINUATION.md` + `analysis/ELECTRUM_ENTROPY_AUDIT.md`
(pista Electrum, hoje despriorizada), `analysis/EXTERNAL_RESEARCH.md`
(front-running: **qualquer solução exige mineração privada** — #66 e #69 foram
roubados na mempool via RBF).

## 8. Classes de trabalho estéreis — não repita

- Estatística das 82 chaves (autocorrelação, FFT, bias modular, compressibilidade,
  bias de bit, change-point). Poder zero, demonstrado.
- Busca de estrutura na secp256k1 (relações entre pubkeys, "órbitas", flatness).
- Teoremas (Shoup, autorredução, redução de bits). Corretos e sem consequência prática.
- Otimizar constante de Kangaroo / força bruta local. Ordens de grandeza fora de alcance.

## 9. Frente aberta — ordem recomendada

Detalhe formal, espaço e critério de aceitação em `HYPOTHESES.json`.

1. **H1 forense** — atribuir o software das transações do criador. Dados já
   extraídos em `data/creator_txs.json`. Falta a pesquisa externa sobre
   comportamento de carteiras da época. Produz evidência que direciona H2 e H3.
2. **H2 variantes de máscara e índice** — *implementado em 2026-09-07*, controles
   **20/20**. Máscaras: `low` (declarada pelo criador), `high` (n bits altos),
   `low_le` (filho em little-endian). Mapas de índice: `consecutive` com offset e
   stride arbitrários, `reverse` (#256 no começo da carteira), `rejection` (sorteio
   sequencial descartando filhos sem o bit n-1 setado). Ramo de troco sai pelo
   caminho BIP32 (`m/1/i`). Falta rodar a cobertura: `./analysis/run_sweeps_h2.sh`.
   **Cada linha de cobertura vale só para o par (mask, index_map) registrado nela** —
   confira essas colunas antes de citar cobertura.
3. **H3 seeds humanas** — `seed = SHA256(frase)` e BIP39 com passphrase escolhida.
   ~8 k/s nesta máquina; wordlist de 10⁷ em ~20 min. Nunca varrido.
4. **H4 OSINT** — conta `saatoshi_rising`, endereço de financiamento
   `1CENDvi6tmKGrR8RxqwURpX9WHbbKip1db`, origem do reforço de 2023, busca por
   gist/pastebin de 2015 com script de 256 chaves. Custo zero de compute.

## 10. Probabilidades, sem enfeite

| Caminho | Chance realista |
|---|---|
| Seed veio de CSPRNG → nada funciona, nunca | **90–97%** |
| Seed fraca **e** dentro de um espaço enumerável | 1–3% |
| OSINT revelar o gerador ou a seed | 1–3% |
| Compute próprio resolver #71 ou #140 | ~0 |

O trabalho se justifica por ser barato e falsificável, não por ser provável.
Não prometa resultado; registre cobertura.
