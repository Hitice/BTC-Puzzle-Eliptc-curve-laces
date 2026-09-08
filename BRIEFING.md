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
| 121 assinaturas nas cinco transações em cache | ECDSA e TXIDs reconstruídos; inclui o witness de 2023; nenhum `r` repetido. Valores/scripts dos prevouts vêm do cache |
| Financiamento de 2015 | `1Czoy8xtddvcGrEhUUCZDQ9QqdRfKh697F`, pubkey comprimida. `1CENDvi6...` é a entrada adicional de **2017**, não comprimida |

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
| `analysis/master_seed_sweep.py` | Enumera seeds mestres nos modelos registrados. Âncora: puzzle #130, 129 bits, em **uma** derivação. Confirma nas outras 81 chaves. Famílias: `bip32` (caminho arbitrário), `hashseq`, `hashchain`, `electrum1`. Máscaras `--mask low\|high\|low_le`, índices `--index-map consecutive\|reverse\|rejection` com `--index-base`/`--index-stride`. Controles **20/20** |
| `analysis/java_random_recovery.py` | Testa quatro layouts de saída direta do Java Random; enumeração completa dos 16 bits ocultos de estado a partir do #70. Controles Java independentes. H5 no registro |
| `analysis/v8_native_masks.py` | Fecha o caso byte8 do V8 3.14.5 por enumeração exata; três máscaras, nove controles. Não requer Z3. H6 no registro |
| `analysis/secp_fast.py` | secp256k1 com comb de base fixa, 122 µs por `k*G` |
| `analysis/run_sweeps.sh` | fila base (máscara `low`, índice consecutivo) → `analysis/sweeps/` |
| `analysis/run_sweeps_h2.sh` | fila das variantes de máscara e índice (H2) |
| `analysis/creator_tx_forensics.py` | indicadores forenses das transações do criador |
| `analysis/verify_creator_signatures.py` | Reconstrói TXIDs, peso, taxas e verifica 121 assinaturas; controle oficial BIP143 e comparação com os cinco alvos da revisão |
| `analysis/funding_nonce_audit.py` | Testa as cinco entradas de financiamento adicionais: nonce até 65.536 e somas/diferenças nesse limite em 590 pares. Controles sintéticos |
| `analysis/interval_polynomial_lab.py` | H7: formulação exata de pertinência ao intervalo por polinômios; 41 controles em intervalos pequenos. Sem aceleração: preparação enumera W pontos e consulta custa W−1 multiplicações de campo |
| `analysis/phrase_seed_sweep.py` + `run_phrase_sweeps.py` | **H3, ramo de frases — antes inexistente.** O sweep original só aceita faixas de inteiros; este cobre seeds humanas (dicionário 235.976 × 4 caixas + gerador temático) × 4 modos de seed × 10 famílias × 3 máscaras. Controles 6/6; 116.864.880 testes de âncora, zero sobreviventes |
| `analysis/mpk_highindex_verifier.py` | **H8.** Teste exato de MPK usando as 96 pubkeys de #161–#256, sem nenhuma chave privada. Âncora #256 tem só 2 candidatos de `k` → falso positivo 2⁻²⁵⁵. Controles 12/12; 38.184 combinações varridas, zero. Fornece o `m*G == MPK` que faltava |
| `analysis/interval_polynomial_structure.py` | H7, auditoria de estrutura. Constrói `F_{A+s}·F_{A−s}` a partir dos **coeficientes** de `F_A` via resultante com o S3 de Semaev, sem multiplicação escalar sobre A. Contraste: `psi_N`, grau ~2^510, avaliado em ~12k multiplicações |
| `analysis/status.py` | estado atual em um comando |

Taxas medidas (M3, 8 processos): `hashseq` 5,3 M/s · BIP32 endurecido ~800 k/s ·
BIP32 com um `k*G` ~16 k/s · `electrum1` ~250/s.

```bash
python3 analysis/status.py                      # estado
python3 analysis/master_seed_sweep.py --self-test   # controles, ~80 s
./analysis/run_sweeps.sh                        # fila padrão (4 jobs, nice 19)
./analysis/sweep_ctl.sh {status|pause|resume|stop|nice}   # controle da fila
```

As filas rodam com `nice -n 19` e 4 processos por padrão, para não travar a
máquina. `pause` usa SIGSTOP: congela na hora, sem perder progresso; `resume`
retoma de onde parou. Ajuste com `JOBS=8 ./analysis/run_sweeps.sh`.

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

Resultados pontuais concluídos em 08/09/2026: H5 (Java bruto, quatro layouts)
e H6 (V8 3.14.5 bruto, seis combinações de layout/máscara). Sem correspondências.
O caso V8 byte8 terminou por enumeração nativa, **não** pelo timeout do SMT.
Esses testes têm poder contra as construções brutas especificadas; não testam
esses PRNGs como fontes de seed de uma carteira que depois usa hashes/HD.

- Estatística das 82 chaves (autocorrelação, FFT, bias modular, compressibilidade,
  bias de bit, change-point). Poder zero, demonstrado.
- Busca de estrutura na secp256k1 (relações entre pubkeys, "órbitas", flatness).
- Teoremas (Shoup, autorredução, redução de bits). Corretos e sem consequência prática.
- Otimizar constante de Kangaroo / força bruta local. Ordens de grandeza fora de alcance.

## 9. Frente aberta — ordem recomendada

Detalhe formal, espaço e critério de aceitação em `HYPOTHESES.json`.

**H7, pesquisa matemática solicitada pelo usuário — auditada em 08/09/2026.**
A função `F_I(X) = produto (X − x(jG)), j em I` permite decidir metades de um
intervalo prometido abaixo de `N/2`. Formulação e custos reproduzidos e
verificados de forma independente: 41 chaves sintéticas, `W−1` multiplicações de
campo por consulta, preparação enumerando os pontos. As duas perguntas em aberto
foram fechadas:

1. **Construir `F_I` sem enumerar os fatores: sim, e é conhecido.** Identidade
   verificada, `Res_u(F_A(u), S3(u, x(sG), X)) = F_A(x(sG))² · F_{A+s}(X) · F_{A−s}(X)`,
   com `S3` = terceiro polinômio de somatório de Semaev (ePrint 2004/031).
   Coeficientes reconstruídos com **zero** multiplicações escalares sobre `A`.
   Sem ganho: o grau de saída é `2|A|`, então escrever o resultado já custa
   `2|A|` e a cadeia até a largura `W` custa `Ω(W)`.
2. **Grau alto não é o obstáculo — confirmado.** `psi_N` (polinômio de divisão)
   tem grau ~2^510 e é avaliado em ~12.240 multiplicações de campo, decidindo
   pertinência à `n`-torção. Esse é o análogo de `X^(2^100)` procurado, e ele
   existe porque o conjunto de raízes é um **subgrupo**, fechado sob a lei de
   grupo. Um intervalo `[L, L+W)` não tem esse fechamento.

O que resta é a existência de um circuito aritmético pequeno para `X → F_I(X)`.
Um circuito de tamanho `s` daria DLP em intervalo em `O(s·log W)`; o limite
genérico é `Ω(√W)` e o melhor algoritmo conhecido é o canguru de Pollard a
~`2√W`. Esse circuito não é um passo em direção à quebra do ECDLP, ele **é** a
quebra. Não confundir controles em intervalos de 16–256 candidatos com puzzles
resolvidos.

1. **H1 forense** — atribuir o software das transações do criador. Dados já
   extraídos em `data/creator_txs.json`; validação em
   `analysis/creator-signature-verification.json`. A leitura do código histórico
   de Electrum 1.9.8 e Core 0.9.3 não atribuiu o gerador: a ordenação pode vir do
   chamador. Faltam controles de atribuição com software conhecido. O software
   que assina uma transação posterior não identifica o gerador de 2015.
2. **H2 variantes de máscara e índice** — *implementado em 2026-09-07*, controles
   **20/20**. Máscaras: `low` (declarada pelo criador), `high` (n bits altos),
   `low_le` (filho em little-endian). Mapas de índice: `consecutive` com offset e
   stride arbitrários, `reverse` (#256 no começo da carteira), `rejection` (sorteio
   sequencial descartando filhos sem o bit n-1 setado). Ramo de troco sai pelo
   caminho BIP32 (`m/1/i`). Falta rodar a cobertura: `./analysis/run_sweeps_h2.sh`.
   **Cada linha de cobertura vale só para o par (mask, index_map) registrado nela** —
   confira essas colunas antes de citar cobertura.
3. **H3 seeds humanas** — *primeira varredura executada em 08/09/2026.* O ramo de
   frases não tinha implementação: `master_seed_sweep.py` só aceita `--range` de
   inteiros. Coberto agora: 973.874 frases (dicionário do sistema com variantes de
   caixa + gerador temático) × seeds `sha256`/`sha256d`/`raw`/`bip39` × 10 famílias
   × 3 máscaras = **116.864.880 testes de âncora, zero sobreviventes**, 31 min.
   Controles 6/6. Isso exclui o espaço enumerado, **não** o H3: falta frase
   arbitrária, outros idiomas, e BIP39 com mnemônico desconhecido.
4. **H4 OSINT** — conta `saatoshi_rising`, financiamento de 2015
   `1Czoy8xtddvcGrEhUUCZDQ9QqdRfKh697F`, entrada adicional de 2017
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
