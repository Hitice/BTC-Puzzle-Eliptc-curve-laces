# Bitcoin Puzzle — Workspace de Análise

> **Se você é uma IA começando agora: leia [BRIEFING.md](BRIEFING.md) e pare por aí.**
> Ele é auto-suficiente (~1,8 k tokens). Este README é o índice histórico (~2,3 k) e
> o conjunto completo de documentos custa ~44 k tokens.

> **PONTO DE ENTRADA PARA IA.** Leia este arquivo primeiro. Ele resume o estado da
> investigação para que você não re-derive nem re-teste o que já foi descartado.

> **Revisão de 07/09/2026:** há conclusões excessivas nas análises originais abaixo.
> Leia [a revisão](breach-review/REVISAO.md) e a
> [continuação sobre o gerador](analysis/GENERATOR_CONTINUATION.md) antes de considerar
> uma hipótese descartada. A [auditoria da seed do Electrum](analysis/ELECTRUM_ENTROPY_AUDIT.md)
> rastreia uma implementação candidata, ainda sem vínculo demonstrado ao puzzle.
>
> **Auditoria de poder (07/09/2026):** os resultados negativos sobre derivação e
> geradores **não têm poder** contra a hipótese que dizem fechar — demonstrado
> executando os detectores do repo sobre um gerador comprovadamente fraco, que eles
> aprovaram. Leia [analysis/AUDITORIA_PODER.md](analysis/AUDITORIA_PODER.md) **antes**
> da tabela "Hipóteses já descartadas" abaixo. `data/puzzles.json` foi corrigido:
> **#135 está resolvido**.

## O que é

Análise do "Bitcoin Puzzle Challenge" criado por *saatoshi_rising* em 2015: 160 chaves
privadas em ranges de bits crescentes (puzzle #n vive em `[2^(n-1), 2^n - 1]`), cada uma
com BTC depositado. Objetivo do workspace: investigar se existe **algum caminho de solução
fora de brute-force e Kangaroo/BSGS**.

## Estado atual (one-liner)

**Nenhuma chave nova recuperada; implementação do gerador ainda não identificada.**
O único teste com poder contra a hipótese do gerador é enumerar a SEED mestre —
`analysis/master_seed_sweep.py` faz isso (âncora de 129 bits no #130, controles 8/8).
As 82 chaves do conjunto local foram reconferidas contra endereços e pubkeys.
A revisão registra resultados negativos para dois modelos restritos de nonce em
cinco alvos; isso não demonstra segurança geral dos nonces. Estatística não identifica
BIP32 nem elimina todos os geradores fracos. O novo filtro de MPK do Electrum antigo
passou pelos controles, mas falta uma MPK candidata vinculada ao desafio. Os demais
textos e tabelas preservam análises anteriores e devem ser lidos com as correções
da revisão, inclusive quanto ao status desatualizado do #135 no conjunto local.

## Estrutura

```
Puzzle/
├── README.md                         <- você está aqui (índice + estado)
├── SUMMARY.md                        <- resumo executivo: provas + o que NÃO fizemos e porquê
├── data/                             <- dados (fonte de verdade)
│   ├── puzzles.json                  <- TODOS os 160 puzzles, machine-readable (USE ESTE)
│   ├── build_puzzles_json.py         <- gerador reproduzível do puzzles.json
│   ├── solved.md                     <- dump bruto dos resolvidos (humano)
│   ├── unsolved.md                   <- dump bruto dos não resolvidos (humano)
│   ├── challenge.md                  <- descrição original do desafio
│   ├── signatures.json               <- assinaturas ECDSA do gasto de 2019 (20 endereços)
│   └── puzzles_161_256.json          <- pubkeys + assinaturas dos #161-#256 (gasto de 2017)
├── analysis/                         <- investigação
│   ├── AUDITORIA_PODER.md            <- LEIA PRIMEIRO: erros remanescentes + poder dos negativos
│   ├── master_seed_sweep.py          <- varredura de SEED MESTRE (BIP32/Electrum v1/hash) — o teste com poder
│   ├── secp_fast.py                  <- secp256k1 com comb de base fixa (122 us por k*G)
│   ├── run_sweeps.sh                 <- fila de varreduras -> analysis/sweeps/
│   ├── FINDINGS.md                   <- CONCLUSÕES internas consolidadas (leia antes de testar)
│   ├── EXTERNAL_RESEARCH.md          <- inteligência de fóruns/Reddit/GitHub + cross-ref
│   ├── FRONTIER.md                   <- estado-da-arte, mito-vs-fato, como participar
│   ├── REFORMULATIONS.md             <- reformulações especulativas + autocrítica + experimento
│   ├── orbit_compressibility.py      <- experimento: A2 medido (incompressibilidade da órbita)
│   ├── scale_sweep.py                <- varredura de escala 2¹¹–2¹⁶: A2 corroborada multi-escala
│   ├── gpu_orbit_sweep.py            <- mesma varredura, detectores em GPU (CuPy) / CPU fallback
│   ├── statistics.py                 <- estatística descritiva geral
│   ├── test_autocorrelation.py       <- autocorrelação lag 1-5 (descartado)
│   ├── test_nibble_fft.py            <- bias de nibble + periodicidade FFT (descartado)
│   ├── test_derivation.py            <- estrutura de derivação via bits baixos (descartado)
│   ├── ecdsa_signatures.py           <- extração + análise de nonce ECDSA (descartado)
│   ├── gap_analysis.py               <- 2ª rodada: LCG, modular, bit-bias (descartado)
│   ├── verify_signals.py             <- verificação MC dos sinais residuais
│   ├── mod23_deepdive.py             <- Bonferroni + segmentação do mod 23 (ruído)
│   ├── power_and_changepoint.py      <- análise de poder: limites das conclusões negativas
│   ├── pubkey_relations.py           <- relações EC entre pubkeys expostos (descartado)
│   ├── bit_security_demo.py          <- prova: bits parciais ~ chave inteira (Shoup)
│   ├── kangaroo_lab.py               <- BUGADO: não resolve de forma confiável (K=0.309/nan); baseline INVÁLIDO
│   └── weak_generator_scan.py        <- gerador fraco hash/índice + compressão (rejeitado vs dados reais)
└── viz/
    ├── map_3d.py                     <- gerador da visualização 3D
    └── map_3d.html                   <- visualização interativa (abrir no navegador)
```

## Como usar `data/puzzles.json` (para IA)

Schema por puzzle:
```json
{
  "puzzle": 71, "bits": 71,
  "range_start_hex": "...", "range_end_hex": "...", "range_size": 1180591620717411303424,
  "status": "unsolved" | "solved",
  "address": "1PWo...", "pubkey": null | "02...", "pubkey_exposed": false,
  "balance_btc": 7.10,                 // só unsolved
  "privkey_hex": "0000...", "privkey_int": 123, "position_in_range": 0.64  // só solved
}
```
`meta.unsolved_with_pubkey` lista os puzzles atacáveis por Kangaroo/BSGS: **[140,145,150,155,160]**
(#135 saiu da lista: foi resolvido e os fundos foram gastos — verificado on-chain em 07/09/2026).
`meta.smallest_unsolved` = **71** (menor range não resolvido = alvo de brute-force).

## Hipóteses já descartadas (NÃO re-testar sem dado novo)

> **Leia antes:** as linhas sobre derivação, LCG, autocorrelação, periodicidade,
> bias modular e gerador fraco hash/índice foram medidas com **poder zero** contra
> uma seed mestre fraca — um conjunto sintético de BIP32 com seed de 32 bits passa
> por todas elas. Ver [AUDITORIA_PODER.md](analysis/AUDITORIA_PODER.md) §4. "Descartado"
> aqui significa "aquele modelo específico não bate", não "o gerador é forte".

| Hipótese | Veredito | Onde |
|----------|----------|------|
| Padrão na posição das chaves no range | Aleatório (uniforme) | statistics.py |
| Autocorrelação entre chaves (lag 1-5) | Ruído (p>0.05) | test_autocorrelation.py |
| Periodicidade (FFT) | Ruído (p=0.45) | test_nibble_fft.py |
| Bias no nibble inicial/final | Artefato matemático | test_nibble_fft.py |
| Derivação linear (key=seed+i) | Rejeitado (1/66) | test_derivation.py |
| Bits baixos compartilhados / MI | Independentes | test_derivation.py |
| Reuso/bias de nonce ECDSA | Sem fraqueza (1 sig/chave) | ecdsa_signatures.py |
| PRNG LCG (a·w+c mod 2^k) | Rejeitado (0/34) | gap_analysis.py |
| Bias modular (primos ≤47) | Ruído (Bonferroni + split) | mod23_deepdive.py |
| Bias por posição de bit | Nenhum anômalo | gap_analysis.py |
| Tendência posição vs índice | Sem tendência (r=0.01) | gap_analysis.py |
| Gerador fraco hash/índice (chave=H(i), cadeias) | Rejeitado vs dados reais | weak_generator_scan.py |

## Caminhos ainda abertos

1. **Brute-force** GPU para #71 (range 2^70) — único viável por força. ~316 anos na velocidade
   agregada da comunidade (1.16 Tkeys/s, mai/2025). Ferramentas: BitCrack, KeyHunt.
2. **Pollard's Kangaroo** para #135,140,145,150,155,160 (pubkey exposta). #135 ≈ 2^67.5 ops.
   BSGS inviável nessa escala. Ferramentas: Kangaroo (JeanLucPons), collider.
3. **OSINT** — rastrear o criador / setup original (fora do escopo criptográfico).

> **ATENÇÃO (front-running):** se uma chave for encontrada, o broadcast na mempool pública é
> roubado por bots via RBF (aconteceu com #66 e #69). Qualquer solução exige **mineração
> privada**. Ver [analysis/EXTERNAL_RESEARCH.md](analysis/EXTERNAL_RESEARCH.md) §4.

## Reprodutibilidade

- Tudo é Python stdlib puro (sem dependências externas). `python <script>.py`.
- `data/puzzles.json` é regenerável: `python data/build_puzzles_json.py`.
