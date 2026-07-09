# Análise Estatística Completa — Bitcoin Puzzle Challenge

**Data:** 2026-06-20  
**Amostra:** 82 puzzles resolvidos (#1–#70 consecutivos + #75, #80, #85, #90, #95, #100, #105, #110, #115, #120, #125, #130)  
**Objetivo:** Determinar se existe algum padrão ou ruído de geração explorável nas chaves privadas dos puzzles resolvidos que permita prever a posição das chaves não resolvidas.

---

## 1. Estatísticas Gerais

| Métrica | Observado | Esperado (uniforme) | Veredito |
|---------|-----------|---------------------|----------|
| Posição média no range | 51.73% | ~50% | Normal |
| Desvio padrão da posição | 27.32% | ~28.87% | Normal |
| Mediana da posição | 50.18% | 50% | Normal |
| Hamming weight médio | 51.62% | ~50% | Normal |
| Teste de Runs (Z-score) | +0.482 | < 1.96 | Aleatório |

### Distribuição por quartil

| Quartil | Observado | Esperado |
|---------|-----------|----------|
| Q1 (0–25%) | 19.5% | 25% |
| Q2 (25–50%) | 29.3% | 25% |
| Q3 (50–75%) | 28.0% | 25% |
| Q4 (75–100%) | 23.2% | 25% |

Conclusão: distribuição compatível com uniforme.

---

## 2. Anomalia Investigada: Autocorrelação Lag-3

**Observação inicial:** r(3) = +0.217 (moderada)

### Testes aplicados

| Teste | Método | Resultado | P-value |
|-------|--------|-----------|---------|
| Bartlett | Analítico (IC 95%) | Não significativo | Z = 1.815 (< 1.96) |
| Ljung-Box Q | Lags 1–5 conjuntos | Não rejeita H0 | Q = 6.23 (< 11.07) |
| Monte Carlo | 1.000.000 simulações | Não significativo | p = 6.33% |
| Permutação | 500.000 shuffles | Não significativo | p = 6.33% |
| Bonferroni | Correção para 5 lags | Não significativo | p = 6.33% > α = 1% |
| Robustez | Remoção de outliers | Mantém valor | 0 outliers removidos |

### Autocorrelações completas (lag 1–5)

| Lag | r(k) | Significância |
|-----|------|---------------|
| 1 | +0.0673 | Nenhuma |
| 2 | -0.1610 | Fraca |
| 3 | +0.2170 | Fraca (borda) |
| 4 | +0.0472 | Nenhuma |
| 5 | -0.0582 | Nenhuma |

**Veredito:** RUÍDO ESTATÍSTICO. O valor +0.217 cai na borda do intervalo de confiança [-0.24, +0.21] e nenhum dos 4 testes independentes rejeita a hipótese nula. Com N=70, o poder estatístico é insuficiente para detectar correlações fracas.

---

## 3. Anomalia Investigada: Primeiro Nibble Enviesado

**Observação inicial:** O nibble hex `0x1` aparece como primeiro dígito em 25.6% das chaves (esperado 6.25% se uniforme entre 0–F).

### Causa identificada

O primeiro nibble **não pode** ser uniforme entre 0–F porque o range de cada puzzle impõe restrições:

| n mod 4 | Bits no 1º nibble | Nibbles possíveis | Qtd puzzles |
|---------|--------------------|--------------------|-------------|
| 0 | 4 bits | 8,9,A,B,C,D,E,F | 17 |
| 1 | 1 bit | **1 (forçado)** | 18 |
| 2 | 2 bits | 2,3 | 18 |
| 3 | 3 bits | 4,5,6,7 | 17 |

Os 18 puzzles com `n mod 4 = 1` forçam matematicamente o nibble `1`. Não é um padrão do gerador.

### Testes aplicados

| Teste | Resultado | P-value |
|-------|-----------|---------|
| Chi-quadrado (obs vs esperado estrutural) | Não rejeita H0 | χ² = 5.52 (< 23.68) |
| Monte Carlo (500K simulações uniformes) | Não significativo | p = 91.87% |

**Veredito:** ARTEFATO MATEMÁTICO. A distribuição observada é **exatamente** a esperada para chaves uniformemente aleatórias nos seus ranges. Não existe bias.

---

## 4. Anomalia Investigada: Periodicidade na FFT

**Observação inicial:** DFT das posições normalizadas revelou picos em:
- Período 35.0 (magnitude 6.84)
- Período 3.9 (magnitude 6.26)
- Período 3.0 (magnitude 5.82)

### Testes aplicados

| Teste | Método | Resultado | P-value |
|-------|--------|-----------|---------|
| Fisher g-statistic | Analítico | Não significativo | p = 44.8% |
| Monte Carlo (mag máxima) | 200.000 simulações | Não significativo | p = 51.1% |
| Permutação (mag máxima) | 200.000 shuffles | Não significativo | p = 44.5% |

### Teste individual das top 3 frequências (com Bonferroni)

| Frequência | Período | P-value individual | P-value Bonferroni (34 freqs) |
|------------|---------|--------------------|-----------------------------|
| 2 | 35.0 | 1.89% | 64.3% |
| 18 | 3.9 | 3.68% | 100% |
| 23 | 3.0 | 5.78% | 100% |

A magnitude máxima observada (6.84) fica **abaixo** da média simulada (6.98). Dados puramente aleatórios produzem picos iguais ou maiores em 51% dos casos.

**Veredito:** RUÍDO ESTATÍSTICO. Não existe periodicidade nos dados. Os picos FFT são compatíveis com flutuação aleatória.

---

## 5. Outras Métricas Verificadas

### Entropia por byte
- Média: 2.46 bits (crescente com o tamanho da chave — esperado)
- Puzzles baixos (#1–#24) têm entropia baixa por terem poucos bytes — normal

### Deltas entre posições consecutivas
- 55.1% positivos vs 43.5% negativos — balanceado
- Média |delta| = 31.17% — normal para uniforme
- 8 saltos grandes (>60%) identificados — esperado para N=70

### Distribuição de todos os nibbles
- Todos os 16 nibbles entre 4.6% e 8.4% — nenhum desvio ultrapassa 3pp do esperado

### Último nibble
- Distribuição irregular visualmente (0x4 com 12.2%, 0xA com 1.2%) mas com N=82 a variância esperada é alta — consistente com ruído amostral

---

## 6. Conclusão Final

**As chaves dos puzzles resolvidos são estatisticamente indistinguíveis de valores uniformemente aleatórios dentro dos seus respectivos ranges.**

Todas as três anomalias identificadas na análise exploratória foram testadas com múltiplos métodos rigorosos (analíticos, Monte Carlo, permutação, Bonferroni) e **nenhuma sobreviveu** aos testes de significância:

| Anomalia | Causa real | P-value mais favorável |
|----------|-----------|----------------------|
| Autocorrelação lag-3 | Flutuação amostral | 6.33% (> 5%) |
| Primeiro nibble enviesado | Restrição matemática do range | 91.87% |
| Periodicidade FFT | Flutuação aleatória | 44.5% |

### Implicações práticas

1. **Não é possível prever** a posição de chaves não resolvidas a partir do padrão das resolvidas
2. A wallet determinística + mascaramento por bit range **elimina efetivamente** qualquer correlação entre chaves
3. O criador foi honesto: "there is no pattern"
4. Os únicos caminhos viáveis continuam sendo:
   - **Força bruta** para puzzles sem chave pública exposta (ex: #71)
   - **Pollard's Kangaroo / BSGS** para puzzles com chave pública exposta (#135, #140, #145, #150, #155, #160)

---

## 7. Análise de Assinaturas ECDSA (Nonce Attack)

Extração das assinaturas (r, s) das transações de saída dos puzzles com pubkey exposta
(#135, #140, #145, #150, #155, #160) + resolvidos de referência (#65, #70, #75, #80, #130).
Total de 33 assinaturas analisadas. Script: `ecdsa_signatures.py`. Dados: `../data/signatures.json`.

| Teste | Resultado |
|-------|-----------|
| Reuso de nonce (r duplicado) | Nenhum (33/33 únicos) |
| Reuso cruzado entre puzzles | Nenhum |
| Nonce pequeno (k baixo) | Não (r com 255-256 bits) |
| Entropia dos bytes de r | Normal |
| BIP-62 low-s | 100% (software moderno) |
| Sighash | SIGHASH_ALL em todas |

**Bloqueio fundamental:** cada chave de puzzle tem **apenas 1 assinatura** do criador.
Ataques de lattice (HNP) exigem múltiplas assinaturas da mesma chave com nonce enviesado.
Com 1 assinatura por chave, não há sistema de equações para resolver. **Via fechada.**

Observação: MSB de r ficou 30% ≥ 0x80 vs 70% < 0x80 (n=33), mas compatível com flutuação.

---

## 8. Estrutura de Derivação (bits compartilhados)

A máscara preserva os bits baixos da chave original da wallet. Se a derivação entre chaves
consecutivas tivesse estrutura, isso apareceria nos bits baixos. Script: `test_derivation.py`.

| Hipótese | Resultado |
|----------|-----------|
| key_i = seed + i (linear) | Rejeitada (1/66 pares com diff=1) |
| key_i = seed * i / consistência cruzada | Rejeitada |
| Correlação entre LSBs consecutivos | Não significativa (p=0.08) |
| XOR Hamming dos bits compartilhados | 50.3% (independentes) |
| Informação mútua nos LSBs | Sem dependência (p=0.68) |

**Conclusão:** derivação é hash-based (BIP32 ou equivalente). Cada chave é
criptograficamente independente. **Via fechada.**

---

## 9. Gap Analysis — hipóteses não cobertas antes

Segunda rodada, caçando o que escapou. Scripts: `gap_analysis.py`, `verify_signals.py`,
`mod23_deepdive.py`.

| Hipótese nova | Método | Resultado |
|---------------|--------|-----------|
| **PRNG LCG** (`w→a·w+c mod 2^k`) | Resolver A,C por tripla + verificar | Rejeitado (0/34 predições) |
| Passo/razão constante mod N | Diferenças/razões das chaves completas | Rejeitado |
| Bias modular (primos ≤47) | Chi² + Monte Carlo + Bonferroni | Ruído (ver abaixo) |
| Bias por posição de bit | z-test por bit livre | Nenhum bit anômalo |
| MSB de `r` (ECDSA) | Binomial exato + multi-bit | Ruído de comparação múltipla |
| Tendência posição vs índice | Regressão linear | Sem tendência (r=0.01) |

### O caso mod 23 (e a lição metodológica)

`mod 23` apareceu como "enviesado" (chi²=43.7, p=0.008) e **persistiu** mesmo excluindo
puzzles pequenos. Investigação a fundo o derrubou:

- **Bonferroni:** de 14 primos testados, deram p<0.05 os primos {5, 23, 31} — espalhados,
  nenhum sobrevive a α=0.00357. Exatamente o padrão de falsos positivos esperado.
- **Segmentação:** o sinal **não aparece em nenhum segmento isolado** (#1-15: p=0.12;
  #16-50: p=0.16; #51-130: p=0.13). Só existia no agregado.
- **Split-half:** 1ª metade p=0.52 (limpo), 2ª metade p=0.045. Não replica → ruído/outliers.

### Sobre os puzzles iniciais (escolha humana?)

Os primeiros — #1=`1`, #2=`11`, #3=`111` (binário) — parecem escolhidos a mão. Porém:
(a) o segmento #1-15 passa nos testes de aleatoriedade; (b) ranges pequenos são
**deterministicamente não-uniformes** (poucos valores possíveis), então devem ser tratados à
parte para não contaminar agregados — o que fizemos; (c) **mesmo que os primeiros fossem
hand-picked, os ranges grandes (= alvos não resolvidos) passam em tudo**, e os pequenos já
estão resolvidos. Conclusão: irrelevante para a solução.

> **Resultado da 2ª rodada: nada novo.** Nenhum atalho. Confirma a 1ª rodada com margem maior.

---

## 10. Limites do que afirmamos (análise de poder) — "e se estivermos errados?"

Uma conclusão negativa só vale se houver **poder estatístico** para detectar o efeito.
Medimos isso injetando padrões artificiais de força conhecida (n=82). Script:
`power_and_changepoint.py`.

### Efeito mínimo detectável (80% de poder)

| Padrão | Detectável só se... | Abaixo disso = zona cega |
|--------|---------------------|--------------------------|
| Autocorrelação (AR1) | ρ ≥ **0.4** | ρ ≤ 0.25 passa despercebido |
| Bias modular | afeta > **70%** das chaves | bias parcial invisível |
| Subconjunto com geração distinta | ≥ **20 de 82** chaves | ≤ 12 chaves invisível |
| Mudança de regime (change-point) | — | **nenhuma existe** (p=0.96) |

### O que isto significa honestamente

- **Afirmações fortes (com poder):** não há autocorrelação ≥0.4, nem bias modular majoritário,
  nem subconjunto grande com geração diferente, nem ponto de mudança. LCG/linear/bit-bias
  descartados nas rodadas anteriores.
- **Zona cega (não podemos descartar):** padrões sutis (ρ<0.25, poucas chaves afetadas),
  padrão não-linear complexo não coberto por teste específico, ou estrutura visível apenas
  com a **seed/chaincode** original.

### Por que a zona cega não muda a prática

Um padrão fraco o bastante para sobreviver aos testes é fraco demais para reduzir 2^70 (#71)
a algo factível — ganharia poucos bits, faltariam dezenas. **A única "exceção" que mudaria o
jogo é recuperar a seed/chaincode da wallet determinística** (daria todas as chaves), e isso
não é uma questão estatística sobre as chaves reveladas — está fora do alcance de qualquer
análise dos dados públicos.

### Sobre os puzzles iniciais (confirmação)

Inspeção direta confirma: #1=`1`, #2=`11`, #3=`111` (únicos "todos-uns" binários) parecem
escolha humana. Porém o change-point não acusa desvio (p=0.96) e, decisivo: são resolvidos e
**não preditivos** dos ranges grandes. Tratá-los à parte é correto (ranges pequenos são
deterministicamente não-uniformes), mas não esconde nenhum sinal — eles passam nos testes.

> **Conclusão (revisada — ver §13):** as vias *estatísticas* estão esgotadas com poder adequado
> para padrões fortes/médios. Restam brute-force (#71) e Kangaroo (#135+). **Correção:** a versão
> anterior dizia "a única fronteira é a seed" — exclusão injustificada. O resíduo real é
> empírico (gerador de 2015 incompressível?), não exclusivamente histórico. Ver mapa de 5
> domínios em §13.

---

## 11. Relações EC entre os 6 pubkeys expostos

Cheque barato e raramente feito: se os pubkeys de #135,140,145,150,155,160 (mesma wallet)
tivessem relação EC simples, seria **estrutura não-genérica** e furaria o limite de Shoup.
Script: `pubkey_relations.py` (secp256k1 em Python puro). Os 6 pubkeys validados na curva.

| Teste | Faixa | Resultado |
|-------|-------|-----------|
| Q_i = t·G (multiplo pequeno de G) | t < 2²⁰ | Nenhum |
| Q_j − Q_i = t·G (diferença pequena de chaves) | \|t\| < 2²⁰ | Nenhuma |
| Q_j = m·Q_i (razão inteira pequena) | 2 ≤ m < 2¹⁶ | Nenhuma |

**Negativo.** Pubkeys são pontos EC independentes — consistente com derivação hash-based já
comprovada. Sem estrutura explorável; a parede √N permanece.

### Por que "intervalo < 1% da curva" não ajuda (esclarecimento)

Intuição comum e falsa. A dureza do interval-DLP depende do **tamanho absoluto** do intervalo,
não da fração do grupo. #135 ocupa 2⁻¹²² do grupo (fração ínfima), mas tem 2¹³⁴ chaves em termos
absolutos. A "pequenez" relativa *é* o que reduz a busca de 2²⁵⁶ para 2¹³⁴ — já está 100%
aproveitada. Não há desconto adicional por ser fração pequena. Kangaroo já paga só √(intervalo).
Formalmente: o intervalo = "os bits altos são conhecidos (zero)"; isso vale `log2(N/L)` bits de
graça, já usados. Os bits restantes têm entropia cheia. Localização do intervalo é irrelevante
(DLP é invariante a deslocamento: resolver em [a, a+L) ≡ resolver em [0, L) via Q' = Q − a·G).

---

## 12. Bits parciais da chave (bit-security do DL)

Hipótese testada: computar só *alguns* bits da chave (início/fim) seria mais barato que a
chave inteira? Script demonstrativo: `bit_security_demo.py`.

**Não.** Argumento de deslocamento (provado rodando): um oráculo que devolvesse os bits altos
de k poderia ser chamado recursivamente (~bits/b vezes) para recuperar a chave **inteira**
(verificado: recupera corretamente em 2⁴⁰, 2⁶⁰, 2⁸⁰). Se cada chamada fosse < √N, o DLP
completo sairia em poucas chamadas × (<√N) ≪ √N — violando Shoup. Logo o oráculo barato
**não existe**: computar parte da chave é tão caro quanto computar tudo.

**Corolário (ML ingênuo), com ressalva epistêmica:** um preditor que acertasse 1 bit do DL com
vantagem não-desprezível seria amplificável num solver completo (auto-correção do DL). *Sob a
crença (empírica, não provada) de que o DLP é difícil*, tal preditor eficiente não existe → IA
treinada nas chaves resolvidas não generaliza para as não resolvidas. Isto é uma **redução
condicional** + evidência empírica, não um teorema incondicional.

> **Síntese — correção epistêmica (ver §13):** versões anteriores deste doc afirmavam "não há
> quarta porta analítica" e "a única exceção é a seed". Isso era uma **exclusão injustificada**.
> O enquadramento correto são 5 domínios de ataque, cada um com status epistêmico distinto
> (teorema vs. empírico vs. aberto). Nenhum domínio *cria* informação (a info de `P=kG` é fixa);
> a questão é se a info fixa **basta** para achar k barato — o que só acontece se as chaves não
> forem realmente aleatórias.

---

## 13. Mapa de 5 domínios de ataque (correção epistêmica)

Substitui o enquadramento falho ("matemática invulnerável → só resta história"). Princípio-mestre:
**nenhum observador cria informação** — a info de `P=kG` é fixa; só muda a representação. E
**nunca atribuir a um teorema alcance maior que seu modelo** (Shoup cobre só algoritmos genéricos).

| # | Domínio | Conteúdo | Status epistêmico |
|---|---------|----------|-------------------|
| 1 | Estrutura matemática da curva | index-calculus, pairing/MOV, anomalia, primo especial | **Empírico/indutivo** — sem ataque conhecido; *não* provado inexistente (como P≠NP) |
| 2 | Complexidade computacional | novo algoritmo clássico, quântico (Shor), melhoria assintótica/constante, nova representação | Genérico clássico = **teorema** (Shoup Ω(√N)); não-genérico/quântico/futuro = **aberto** |
| 3 | Implementação / RNG | entropia reduzida no gerador de 2015, bugs, side-channel | **Aberto** — único caminho se houve fraqueza real; não testável dos dados públicos |
| 4 | Informação histórica | software, hardware, seed anotada, vazamento | **Aberto, improvável** — exige evidência externa; P conjunta ínfima vs. rodar Kangaroo |
| 5 | Metaestrutura / compressibilidade | estatística, K-complexity, meta-ML sobre instâncias | Funde-se com #3 (compressível ⇔ gerador fraco); auto-redutibilidade fecha *subfamílias* (**teorema parcial**); resto **empírico**, limitado pela incomputabilidade de K(x) |

### Distinções que versões anteriores apagaram (dívida corrigida)

- **Posterior de k:** informacionalmente é uma *delta de Dirac* (k determinado por P). A
  "uniformidade" é **computacional** (adversário eficiente), não informacional.
- **Auto-redutibilidade:** prova worst≡average-case → mata subfamília fácil e meta-ML que
  transfere. *Não* prova ausência de heurísticas, props auxiliares ou ataques de implementação —
  esses caem **empiricamente**, não logicamente.
- **Kolmogorov:** `K(x)` é incomputável; testamos **proxies** (LCG, compressores, testes
  estatísticos), nunca incompressibilidade em sentido estrito.
- **"20 anos sem ataque":** argumento **indutivo**, não prova. Status de #1, não de #2-genérico.
- **#2 e #5 são ortogonais a #1:** Shor quebra ECDLP *sem* estrutura não-genérica (muda o
  *modelo*, não explora a *curva*) — prova de que "complexidade" é eixo separado de "estrutura".

> **Onde de fato resta sinal não-fechado:** o resíduo real são #3 e #5 fundidos numa única
> pergunta empírica — *"o gerador de 2015 produziu chaves algoritmicamente incompressíveis?"* —
> parcialmente respondida (proxies negativos, com poder medido em §10), nunca fechável em
> absoluto. Tudo o mais é teorema (estreito) ou crença indutiva (forte).

---

## 14. Gerador fraco baseado em HASH (categoria que faltava) — `weak_generator_scan.py`

Lacuna real: as rodadas anteriores testaram relações **aritméticas** (LCG, linear, derivação),
mas nunca relações de **hash** contra os dados reais. Categoria distinta, testável, barata, e
**fora de bruteforce/kangaroo**. Testado contra as 82 chaves conhecidas:

| Hipótese | Método | Resultado |
|----------|--------|-----------|
| Index-hash: chave_i = H(enc(i)) | 7 hashes × 7 codificações × 7 seeds, mascarado ao range | **Rejeitado** |
| Seed-hash: chave_i = H(seed‖i) | seeds adivinháveis (satoshi, bitcoin, …) | **Rejeitado** |
| Hash-chain: low(chave_{i+1}) = low(H(chave_i)) | 69 pares consecutivos | **Rejeitado** |
| Incompressibilidade (proxy de K(x)) | zlib/bz2/lzma nos bytes baixos | Incompressível (lzma 1.174 = baseline aleatório) |

**Sobre os "acertos" aparentes:** o melhor esquema (sha1/str0pad) bate em {#1,2,3,4,6,13} —
**todos ≤13 bits**, e em **nenhum** dos 117 puzzles com ≥14 bits. Artefato de comparação
múltipla: #1 sempre bate (range trivial), #2 com ½, … #13 com 1/4096, e testamos 343 esquemas.
Um gerador real bateria em #130 (checagem de ~129 bits). Como erra todos os grandes → ruído.
Critério honesto adotado: só conta como real se bater em algum puzzle com ≥30 bits (acaso ~2⁻³⁰).
Nenhum bate. Hash-chain idem (acertos só em índices baixos, sem concentração).

**Veredito:** a porta "gerador fraco baseado em hash/índice" está **fechada contra os dados
reais** — com poder decisivo vindo dos puzzles grandes. Não é "ninguém achou"; é "testamos e os
puzzles de ~100-130 bits rejeitam por margem astronômica".

---

## Arquivos de suporte

Caminhos relativos a este arquivo (`analysis/`):

| Arquivo | Descrição |
|---------|-----------|
| `statistics.py` | Estatística descritiva geral |
| `test_autocorrelation.py` | Significância da autocorrelação (lag 1-5) |
| `test_nibble_fft.py` | Significância do bias de nibble e FFT |
| `test_derivation.py` | Estrutura de derivação via bits baixos |
| `ecdsa_signatures.py` | Extração + análise de nonce ECDSA |
| `gap_analysis.py` | 2ª rodada: LCG, modular, bit-bias, tendência |
| `verify_signals.py` | Verificação MC dos sinais mod-23 e ECDSA-MSB |
| `mod23_deepdive.py` | Bonferroni + segmentação + split-half do mod 23 |
| `power_and_changepoint.py` | Análise de poder + change-point (limites das negativas) |
| `pubkey_relations.py` | Relações EC entre os 6 pubkeys expostos (secp256k1 puro) |
| `bit_security_demo.py` | Prova (via redução) que bits parciais ~ chave inteira |
| `kangaroo_lab.py` | Bancada de medição de K para testar melhorias de constante |
| `weak_generator_scan.py` | Gerador fraco hash/índice + compressão (rejeitado vs dados reais) |
| `../data/puzzles.json` | Fonte de verdade machine-readable (todos os 160) |
| `../data/signatures.json` | Assinaturas ECDSA extraídas |
| `../data/solved.md` | Dump bruto dos resolvidos |
| `../data/unsolved.md` | Dump bruto dos não resolvidos |
| `../data/challenge.md` | Descrição original do desafio |
| `../viz/map_3d.html` | Visualização 3D interativa |
