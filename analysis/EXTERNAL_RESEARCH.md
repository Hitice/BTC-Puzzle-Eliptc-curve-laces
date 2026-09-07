> **HISTÓRICO — NÃO LEIA POR PADRÃO.** O ponto de entrada é [BRIEFING.md](../BRIEFING.md). Leia só a seção 4 (front-running / mineração privada) se for lidar com broadcast.

# Pesquisa Externa Consolidada — Fóruns, Reddit, BitcoinTalk, GitHub

> Inteligência coletada de fontes públicas (jun/2026) e cruzada com nossos achados
> internos ([FINDINGS.md](FINDINGS.md)). Cada fato tem fonte. Sanitizado para leitura/
> inferência de IA: sem ruído, sem duplicação, números concretos, claims atribuídos.

## TL;DR (machine-readable)

```yaml
creator_statement: "no pattern; consecutive keys from deterministic wallet masked with leading zeros"
creator_confirms_random: true          # alinhado com nosso FINDINGS (hash-based, independente)
weak_rng_found: false                   # nenhuma fonte confirma RNG fraco; chaves random dentro do range
kangaroo_complexity: "O(2^(n/2))"       # sqrt do range quando pubkey exposta
target_71:
  method: brute-force                   # sem pubkey exposta
  community_speed_may2025: "1.16 Tkeys/s"
  eta_at_community_speed: "~316 years"
  eta_single_rtx4090: "~25000 years"
target_135:
  method: kangaroo
  ops_estimate: "2^67.5"
  status: unsolved
front_running_risk: true                # broadcast público da solução é roubado por bots via RBF
front_running_mitigation: "minerar fora da mempool pública (private mining / Slipstream)"
bsgs_ceiling: "~32-64 bit; inviável na escala do #135"
```

## 1. Geração das chaves (confirma nosso FINDINGS)

- O criador (*saatoshi_rising*) afirmou explicitamente: **"there is no pattern. It is just
  consecutive keys from a deterministic wallet, masked with leading 000...0001 to set
  difficulty."** Fonte: BitcoinTalk topic #1306983.
- Nenhuma fonte pública reporta RNG fraco ou bias explorável. As chaves resolvidas se
  comportam como aleatórias dentro de seus ranges — **idêntico à nossa conclusão estatística**
  (ver FINDINGS.md §1–§8).
- "Reduced-entropy" refere-se apenas ao **range** reduzido (2^(n-1)..2^n), não a fraqueza no
  gerador. Fonte: privatekeyfinder.io, secretscan.org.

> **Implicação para IA:** não há contradição entre fontes externas e nossa análise. A via de
> "encontrar padrão de geração" está fechada por consenso independente.

## 2. Matemática dos puzzles com pubkey exposta (#135,140,145,150,155,160)

- Pollard's Kangaroo reduz a busca de `O(2^n)` para **`O(2^(n/2))`** (raiz quadrada do range),
  pois a pubkey é conhecida após o primeiro gasto.
- **#130** (resolvido set/2024): exigiu ~`2^65` operações, "vários anos em 256 GPUs Tesla V100".
- **#135**: ~**`2^67.5`** operações — próximo alvo kangaroo. Não resolvido (jun/2026).
- **BSGS**: teto prático ~32–64 bits por causa do custo de RAM; **inviável na escala do #135**.
  Útil só para ranges menores.
- Eficiência de implementação: `collider` (hevnsnt) reporta K=1.15, CUDA+Metal.

## 3. Puzzle #71 (alvo brute-force, sem pubkey)

- Sem pubkey exposta → **só brute-force** (kangaroo não se aplica).
- Velocidade agregada da comunidade (mai/2025): **1.16 Tkeys/s** → ETA ~**316 anos**.
- GPU única (RTX 4090): ~**25.000 anos**. Farm de 1.000 GPUs: ~25 anos.
- Espaço total: `2^70` ≈ 1.18×10^21 chaves. Estratégia de pools: subdividir em ~33.5M ranges.
- Ferramentas: **BitCrack** (`--keyspace 400000000000000000:7fffffffffffffffff`),
  **KeyHunt / KeyHunt-Cuda**. GPU mínima recomendada: GTX 1060+.

## 4. Risco de front-running (CRÍTICO se uma chave for encontrada)

- Transmitir a solução na **mempool pública** expõe a chave/assinatura → bots fazem RBF e
  **roubam o prêmio**. Já aconteceu com **#66** e **#69** (ver challenge.md histórico).
- **#67 e #68** foram minerados **fora da mempool pública** para evitar interceptação.
- Mitigação: minerar a transação de forma privada (private mining / serviço tipo "Slipstream").

> **Implicação para IA:** qualquer pipeline de solução DEVE incluir broadcast privado. Achar a
> chave sem isso = perder o prêmio.

## 5. Conceito "Quantum Canary" (contexto, não acionável)

- Os puzzles com pubkey exposta funcionam como alarme: se **#135+ forem resolvidos em
  dias/semanas em sequência**, é sinal de que computação quântica viável (Shor) chegou.
- Hoje sem relevância prática — quebra quântica de secp256k1 exige ~milhares de qubits lógicos.

## 6. Ferramentas mapeadas (referência)

| Ferramenta | Tipo | Uso | Fonte |
|------------|------|-----|-------|
| BitCrack | GPU brute-force | #71 e similares (sem pubkey) | github HomelessPhD/BTC32 |
| KeyHunt / KeyHunt-Cuda | CPU/GPU | brute-force + BSGS | mizogg.com |
| Kangaroo (JeanLucPons) | GPU | pubkey exposta, ≤125-bit interval | bitcointalk 5244940 |
| collider (hevnsnt) | GPU CUDA+Metal | kangaroo, K=1.15 | github hevnsnt/collider |
| dockangaroo | container | kangaroo pronto p/ rodar | github lggurgel/dockangaroo |

## Cross-referência com achados internos

| Tópico | Externo | Nosso FINDINGS | Status |
|--------|---------|----------------|--------|
| Padrão na geração | "no pattern" (criador) | Aleatório (Monte Carlo) | ✅ concordam |
| RNG fraco | Não reportado | Não detectado | ✅ concordam |
| Derivação | Deterministic wallet | Hash-based / independente | ✅ concordam |
| Nonce ECDSA | — (não discutido) | Sem fraqueza (1 sig/chave) | ✅ nosso é mais profundo |
| Caminho viável | Brute-force / Kangaroo | Brute-force / Kangaroo | ✅ concordam |

**Conclusão:** as fontes externas **corroboram independentemente** nossa análise. Nenhum
caminho novo fora de brute-force (#71) e Kangaroo (#135+) foi reportado pela comunidade.
O diferencial do nosso estudo é a profundidade na análise de assinaturas ECDSA e derivação,
que a literatura pública de fóruns não cobre.

## Fontes

- [BitcoinTalk — tópico original (#1306983)](https://bitcointalk.org/index.php?topic=1306983.0)
- [BitcoinTalk — Pollard's kangaroo ECDLP solver](https://bitcointalk.org/index.php?topic=5244940)
- [privatekeys.pw — diretório do puzzle](https://privatekeys.pw/puzzles/bitcoin-puzzle-tx)
- [mizogg.com — guia de solução](https://mizogg.com/learn/puzzle-solving.html)
- [btcpuzzlesearch.com — Quantum Canary / status](https://btcpuzzlesearch.com/)
- [Medium — The 1000 BTC Puzzle deep dive](https://medium.com/@deepml1818/the-1000-btc-puzzle-a-deep-dive-for-newcomers-and-crypto-veterans-c41b89688ce8)
- [GitHub — hevnsnt/collider (Kangaroo K=1.15)](https://github.com/hevnsnt/collider)
- [GitHub — HomelessPhD/BTC32](https://github.com/HomelessPhD/BTC32)
- [GitHub — lggurgel/dockangaroo](https://github.com/lggurgel/dockangaroo)
