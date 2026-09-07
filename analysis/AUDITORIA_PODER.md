# Auditoria de 2026-09-07: erros remanescentes e poder dos resultados negativos

Sessão local, no repositório em `main` (`827479b`). **Nenhuma chave nova de puzzle
foi recuperada.** O que esta rodada estabelece é onde o repositório está correto,
onde ainda está errado, e por que a hipótese do gerador continua aberta — não por
falta de testes, mas porque os testes feitos não tinham poder contra ela.

## 1. O que reconferi e passou

| Verificação | Resultado |
| --- | --- |
| 82 chaves resolvidas → endereço | 82/82 conferem |
| Formato dos 82 endereços | **100% P2PKH com pubkey comprimida**, 0 não comprimida |
| Intervalo `[2^(n-1), 2^n)` de cada chave | 82/82 dentro |
| `pubkey` armazenada vs. derivada | 82/82 conferem |
| `analysis/secp_fast.py` (novo) | igual à multiplicação genérica em 30 escalares aleatórios + vetor conhecido |

## 2. Erros ainda presentes no CÓDIGO (não apenas na documentação)

A [revisão de setembro](../breach-review/REVISAO.md) documentou o erro `r` × `k`,
mas **o código não foi corrigido**. Quem rodar os scripts hoje reproduz as
conclusões erradas.

- `analysis/ecdsa_signatures.py:285` — `if r_bits < 200` tratado como indício de
  nonce pequeno. `r = x(kG) mod n` não é `k`; para `k = 1`, `r` tem 255 bits.
- `analysis/ecdsa_signatures.py:317` — comentário `r = k*G mod p, onde k e o nonce`.
- `analysis/ecdsa_signatures.py:423` — seção intitulada `MSB DO NONCE (primeiro byte de r)`.
- `analysis/test_derivation.py` — o dicionário `SOLVED` é fixo no código e para no
  **#70**. Os puzzles #75–#130 são descartados, justamente os que carregam mais
  bits conhecidos (74 a 129 bits). Todos os testes de derivação rodaram sobre a
  fatia mais pobre dos dados.
- `analysis/weak_generator_scan.py` — a escolha do melhor candidato usa
  `len(matches) > best[0] or power > best[1]`, que pode substituir um candidato
  melhor por um pior. O espaço varrido é de 392 combinações (7 seeds × 7
  codificações × 8 hashes).
- `analysis/kangaroo_lab.py` — o próprio cabeçalho marca `BUGADO`; o baseline é inválido.
- `README.md` — a tabela "Hipóteses já descartadas (NÃO re-testar sem dado novo)" é
  o item operacionalmente mais perigoso: instrui agentes futuros a não repetir
  testes que nunca tiveram poder. Ver seção 4.

## 3. Erros nos dados

- **`#135` está resolvido.** Verificado on-chain: `16RGFo6hjq9ym6Pj7N5H7L1NR1rVPJyw2v`
  recebeu 13,50004408 BTC e gastou 13,50004408 BTC; saldo zero; último gasto no
  bloco 960138. `data/puzzles.json` ainda diz `unsolved` com 13,5 BTC e o inclui
  em `meta.unsolved_with_pubkey`. A lista correta hoje é **[140, 145, 150, 155, 160]**.
  A chave privada do #135 não foi localizada publicada; o gasto expõe pubkey, não chave.
- `#71` continua não resolvido: 58 saídas recebidas, 0 gastas.
- `data/signatures.json` cobre apenas o tx de 2019 (20 endereços, 33 assinaturas).
  O gasto de 2017 não estava no repositório. Corrigido na seção 6.

## 4. Achado central: os resultados negativos não têm poder

Em **qualquer** carteira determinística aditiva — BIP32 e Electrum v1 incluídos —
a chave filha é `child_i = m + H(...) mod n`. As diferenças entre chaves de puzzle
são pseudo-aleatórias **por construção**, tenha a seed mestre 256 bits ou 16. Logo,
testes de relação *entre* chaves não conseguem, nem em princípio, distinguir uma
seed forte de uma seed trivialmente enumerável.

Isso foi demonstrado, não argumentado. Gerei um conjunto sintético de 82 chaves com
BIP32 `m/0/i`, seed = os 4 bytes de `12345` — um gerador que se quebra por
enumeração em 22 segundos — e submeti esse conjunto aos detectores do próprio repo:

| Detector do repo | Veredito sobre o gerador FRACO |
| --- | --- |
| `weak_generator_scan.py` — index/seed-hash | `-> Index/seed-hash REJEITADO` |
| `weak_generator_scan.py` — compressão | `lzma ratio=1.174`, idêntico ao baseline aleatório `1.174` |
| `gap_analysis.py` — LCG | `1. LCG detection: negativo (hash-based)` |
| `gap_analysis.py` — tendência posicional | `sem tendencia (posicao independe do indice)` |
| `gap_analysis.py` — bias modular | uniforme |
| **`master_seed_sweep.py` (novo)** | **seed 12345 recuperada; #71 sintético previsto exatamente** |

Reprodução: o dataset sintético é gerado pelo bloco em `AUDITORIA_PODER.md` §8 e os
scripts do repo rodam sobre ele sem alteração.

**Consequência.** As linhas *Derivação linear*, *Bits baixos compartilhados*,
*PRNG LCG*, *Gerador fraco hash/índice*, *Autocorrelação*, *Periodicidade* e
*Bias modular* da tabela do README não são evidência de que o gerador é forte.
Elas são compatíveis com uma seed de 32 bits. O que elas excluem é bem menor do
que a tabela sugere.

Isto **não** é evidência de que a seed real é fraca. É a demonstração de que a
pergunta continua sem resposta e de que só um tipo de teste pode respondê-la.

## 5. Evidência nova sobre a identidade do gerador

- Os **256** endereços do puzzle usam pubkey comprimida (82 conferidos localmente,
  96 conferidos a partir do gasto de 2017; os demais por consistência do mesmo tx).
- A entrada de financiamento do **próprio criador** no tx de 2017 —
  `1CENDvi6tmKGrR8RxqwURpX9WHbbKip1db`, 83,531 BTC — usa pubkey **não comprimida**.
- Em 15/01/2015 não existia Electrum 2.x (março/2015) nem carteira HD no Bitcoin
  Core (0.13, 2016). Electrum 1.x e Armory da época produziam endereços **não
  comprimidos** — o repo já verificou isso na fonte para o Electrum 1.9.8.

Leitura: as chaves do puzzle não saíram do caminho normal de geração de endereços
de uma carteira da época; foram serializadas por código próprio. Isso **não elimina**
a derivação do Electrum v1 (o criador mascarou as chaves de qualquer forma, então a
serialização dele é independente da carteira), mas reduz a prioridade dessa hipótese
e aumenta a de **BIP32 dentro de um script** (pybitcointools, bitcoinjs-lib,
python-bitcoinlib). A varredura da seção 7 cobre BIP32 diretamente.

## 6. Dados acrescentados: `data/puzzles_161_256.json`

Extraído do gasto de 11/07/2017, tx `5d45587cfd1d5b0fb826805541da7d94c61fe432259e68ee26f4a04544384164`
(97 entradas, 109 saídas):

- **96 chaves públicas** dos puzzles #161–#256, cada uma conferida contra o próprio
  endereço e validada na curva; todas comprimidas.
- **96 assinaturas** `(r, s, sighash)` com 96 valores de `r` distintos.
- A entrada de financiamento do criador, com pubkey não comprimida.

Utilidade: 96 alvos independentes de 160–255 bits para **confirmar** qualquer
hipótese de gerador, e material de OSINT sobre o criador.
Limite: `z` não foi reconstruído aqui; este arquivo não é, por si, uma via de ataque.

## 7. Ferramenta nova: varredura de seed mestre

`analysis/master_seed_sweep.py` (+ `analysis/secp_fast.py`, secp256k1 com comb de
base fixa, 122 µs por `k*G`).

Modelo: `puzzle_n = 2^(n-1) | (child_{base+n-1} mod 2^(n-1))`.
Âncora: puzzle **#130**, 129 bits conhecidos, testados com **uma** derivação.
Falso positivo por candidato: `2^-129`. Sobreviventes são confirmados contra as
outras 81 chaves. Um acerto é conclusivo.

Famílias: `bip32` (caminho arbitrário, endurecido ou não), `hashseq`
(`child_i = H(seed || enc(i))`), `hashchain`, `electrum1` (OldAccount com o
alongamento de 100.000 SHA256).
Codificadores de seed: inteiro cru (4/8 bytes, BE/LE), ASCII, hex, SHA256,
`mt256`/`mt128hex` (o que `random.seed(t)` do Python produziria).

Controles executados, 8/8 passaram: recuperação positiva da seed, rejeição do
conjunto adulterado em um bit, e ausência de acerto dos dados reais na faixa de
controle — para cada família.

Taxas medidas neste M3 (8 processos):

| Família | candidatos/s |
| --- | ---: |
| `hashseq` | 5,3 M |
| `bip32 m/ih` (endurecido, sem EC) | ~800 k |
| `bip32 m/0/i` (uma multiplicação EC) | ~16 k |
| `electrum1` | ~250 |

Ou seja: todo o espaço de seeds de 32 bits sai em ~13 min para `hashseq`, ~1,5 h
para BIP32 endurecido; a janela de timestamps 2013-01-01 → 15/01/2015 (64,3 M
valores) sai em ~1,1 h para `bip32 m/0/i`.

```bash
python3 analysis/master_seed_sweep.py --self-test
./analysis/run_sweeps.sh                      # fila padrão, resultados em analysis/sweeps/
python3 analysis/master_seed_sweep.py --family bip32 --path "m/0/i" \
    --encoder mt256 --range 1356998400-1421345235 --jobs 8
```

## 8. Limites honestos desta rodada

- Uma varredura sem acerto exclui **exatamente** o espaço varrido. Não diz nada
  sobre seeds fora dele.
- A prioridade de `random.seed(timestamp)` é baixa: a
  [auditoria de entropia](ELECTRUM_ENTROPY_AUDIT.md) mostrou que o caminho padrão
  do Electrum 1.9.8 chega a `os.urandom`. O argumento a favor de varrer assim mesmo
  é o custo, não a plausibilidade.
- Se a seed veio de `os.urandom`, nenhuma varredura de seed resolve o puzzle, e o
  caminho volta a ser força bruta (#71) ou kangaroo (#140+).
- Nada aqui contradiz o limite de Shoup nem sugere fraqueza na secp256k1.
