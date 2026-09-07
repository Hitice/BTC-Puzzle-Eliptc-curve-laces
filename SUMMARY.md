> **HISTÓRICO — NÃO LEIA POR PADRÃO.** O ponto de entrada é [BRIEFING.md](BRIEFING.md). As afirmações de esgotamento de domínios estão corrigidas em `analysis/AUDITORIA_PODER.md`.

# Resumo Executivo — Tudo que Fizemos, as Provas, e o que NÃO Fizemos

> **Documento histórico, com conclusões corrigidas em 07/09/2026.** As afirmações
> abaixo sobre nonce pequeno, impossibilidade de lattice com uma assinatura,
> identificação de gerador e fechamento de famílias não devem orientar novos testes
> sem a [revisão](breach-review/REVISAO.md). O estado vigente está no
> [README](README.md) e na [continuação](analysis/GENERATOR_CONTINUATION.md).

> Capstone do workspace. Para o índice navegável e o estado, ver [README.md](README.md).
> Para o detalhe técnico de cada teste, ver [analysis/FINDINGS.md](analysis/FINDINGS.md).

---

## Parte 1 — O que construímos (infraestrutura)

| Artefato | O que é |
|----------|---------|
| `data/puzzles.json` | Fonte de verdade: 160 puzzles, machine-readable (range, endereço, pubkey, chave se resolvida) |
| `data/signatures.json` | 33 assinaturas ECDSA extraídas da blockchain (alvos + referência) |
| `viz/map_3d.html` | Visualização 3D interativa das chaves resolvidas |
| `README.md` / `FINDINGS.md` / `FRONTIER.md` / `EXTERNAL_RESEARCH.md` | Documentação para leitura/inferência de IA |

---

## Parte 2 — Tudo que testamos (13 análises) e o veredito

### Rodada 1 — Estatística das chaves resolvidas (n=82)
1. **Descritiva** (`statistics.py`): posição média no range 51.7% (esperado 50%), desvio 27.3% (esperado 28.87%), Hamming 51.6%, runs Z=+0.48. → Indistinguível de uniforme.
2. **Autocorrelação** (`test_autocorrelation.py`): lag-3 r=+0.217 parecia sinal. Morto por Bartlett (Z=1.82<1.96), Ljung-Box (Q=6.23<11.07), Monte Carlo (p=0.063), permutação (p=0.063), Bonferroni. → Ruído.
3. **Nibble + FFT** (`test_nibble_fft.py`): bias do 1º nibble = artefato matemático (MC p=0.92); periodicidade FFT = ruído (Fisher p=0.45, MC p=0.51, permutação p=0.45).
4. **Derivação** (`test_derivation.py`): linear (key=seed+i) rejeitado (1/66); correlação LSB p=0.08; XOR 50.3%; informação mútua p=0.68. → Hash-based, independente.
5. **Nonce ECDSA** (`ecdsa_signatures.py`): 33 sigs; sem reuso de r, sem nonce pequeno, 100% low-s (BIP-62), 1 sig por alvo. → Ataque de lattice/HNP impossível.

### Rodada 2 — Caça ao que escapou (gap analysis)
6. **Gap** (`gap_analysis.py`): LCG rejeitado (0/34 predições), passo/razão mod N (não), bias por bit (nenhum), tendência posição×índice (r=0.01). Apenas mod-23 acendeu.
7. **Verificação de sinais** (`verify_signals.py`): MSB de r p=0.035 — mas LSB de r também p=0.013 (2 de 5 bits) → comparação múltipla. mod-23 confirmado via MC.
8. **mod-23 a fundo** (`mod23_deepdive.py`): Bonferroni (nenhum dos 14 primos sobrevive), segmentação (sinal não existe em nenhum segmento isolado), split-half (não replica). → Ruído.
9. **Poder + change-point** (`power_and_changepoint.py`): change-point p=0.96 (sem mudança de regime); poder — detectável só se ρ≥0.4, bias modular >70%, subconjunto ≥20/82.

### Rodada 3 — Curva elíptica e teoria
10. **Relações EC** (`pubkey_relations.py`): secp256k1 em Python puro; 6 pubkeys validados na curva; sem relação multiplicativa (m<2¹⁶), aditiva (t<2²⁰) ou múltiplo pequeno de G. → Pontos independentes.
11. **Bits parciais** (`bit_security_demo.py`): demonstração executada — ver Parte 3.
12. **Bancada de kangaroo** (`kangaroo_lab.py`): mede K empírico para testar melhorias de constante (pendente: EC puro lento).

---

## Parte 3 — As provas, detalhadas

### Prova A — Limite inferior de Shoup (TEOREMA, citado)
Em grupos genéricos, qualquer algoritmo de DLP faz Ω(√N) operações. **Escopo estrito:** só
algoritmos genéricos (tratam elementos como rótulos opacos + oráculo da operação). Não cobre
ataques não-genéricos, quânticos, ou modelos futuros. É o piso que kangaroo/rho/BSGS atingem.

### Prova B — Redução de deslocamento (EXECUTADA, condicional)
`bit_security_demo.py` rodou em intervalos 2⁴⁰, 2⁶⁰, 2⁸⁰: um oráculo hipotético de bits-altos
recupera a chave **inteira** em ~bits/8 chamadas (5, 8, 10 respectivamente; chave recuperada
corretamente). **Logo:** se computar parte da chave fosse < √N, o DLP inteiro sairia < √N —
contradiz Shoup. Conclusão: bits parciais são tão caros quanto a chave toda. *Condicional* ao
modelo genérico (não é impossibilidade incondicional).

### Prova C — Auto-redutibilidade aleatória (TEOREMA, escopo limitado)
`Q' = Q + rG` transforma qualquer instância em qualquer outra → worst-case ≡ average-case.
**Mata:** subfamília fácil, meta-ML que transfere entre instâncias. **Não mata:** heurísticas,
ataques de implementação, props auxiliares (esses caem empiricamente, não por este teorema).

### Prova D — Informação é fixa (princípio)
`P=kG` é bijeção → informacionalmente k é uma *delta de Dirac* (totalmente determinado). A
"aleatoriedade" das chaves é **computacional** (adversário eficiente), não informacional.
Nenhum observador cria informação; só re-representa. A questão é se a info fixa **basta** para
achar k barato — só se as chaves não forem realmente aleatórias.

### Resultados negativos como prova estatística
Cada "ruído" acima é uma rejeição com p-value via Monte Carlo/permutação + correção de Bonferroni
+ análise de poder (efeito mínimo detectável). Não é "não achamos"; é "medimos e está abaixo do
limiar, e eis o limiar".

---

## Parte 4 — O mapa de 5 domínios (enquadramento final)

| # | Domínio | Status |
|---|---------|--------|
| 1 | Estrutura da curva | Empírico/indutivo (sem ataque conhecido; não provado inexistente) |
| 2 | Complexidade computacional | Teorema só p/ genérico clássico (Shoup); quântico/futuro = aberto |
| 3 | Implementação / RNG 2015 | Aberto — não testável dos dados públicos |
| 4 | Informação histórica | Aberto, improvável (P conjunta ínfima) |
| 5 | Metaestrutura / compressibilidade | Funde-se com #3; subfamílias fechadas (teorema parcial); resto empírico, limitado por K(x) incomputável |

**Resíduo real não-fechado:** #3+#5 fundidos numa pergunta empírica — *o gerador de 2015 produziu
chaves algoritmicamente incompressíveis?* — parcialmente respondida (proxies negativos), nunca
fechável em absoluto.

---

## Parte 5 — O que NÃO fizemos, e por quê

### Não fizemos por ser inviável/impossível
| Não feito | Porquê |
|-----------|--------|
| Força bruta real no #71 | 2⁷⁰ ops; ~316 anos na velocidade agregada da comunidade; sem hardware; custo energético |
| Kangaroo real no #135 | 2⁶⁷·⁵ ops; exige fazenda de GPU por meses; sem hardware |
| Ataque quântico (Shor) | Exige ~2.330 qubits lógicos / ~317M físicos; não existe |
| Lattice/HNP no ECDSA | Precisa de várias sigs/chave com nonce enviesado; alvos têm 1 sig cada |
| Recuperar seed/chaincode | Não está nos dados públicos; está com o criador |
| DLP com pré-processamento | Armazenamento astronômico; não ajuda alvo único |
| Batch multi-alvo (√k) | Intervalos disjuntos e exponenciais; custo dominado pelo maior; não ajuda |

### Não fizemos por estar fora do escopo lógico (provado fútil)
| Não feito | Porquê |
|-----------|--------|
| ML para prever chaves | Auto-correção do DL: preditor com vantagem → solver completo → quebraria o hash |
| Computar "só alguns bits" | Redução de deslocamento (Prova B): colapsa no DLP inteiro |
| Explorar a "fração <1%" | Fração = bits altos zero = já 100% usada; só o tamanho absoluto conta |

### Não fizemos por ser moonshot / baixa probabilidade
| Não feito | Porquê |
|-----------|--------|
| Caçar estrutura não-genérica em secp256k1 | 20 anos de evidência negativa (indutiva); quebraria a internet inteira se existisse |
| OSINT/arqueologia do criador | P conjunta ínfima (HD wallet ∧ identificável ∧ versão ∧ bug ∧ ...) ≪ rodar Kangaroo |
| Testar TODOS os geradores de baixa complexidade | K(x) incomputável; testamos só famílias específicas (LCG, linear, estatística) |
| Testar o RNG real de 2015 | Não há implementação rodando para sondar; não inferível dos dados públicos |

### Não fizemos por decisão/pendência
| Não feito | Porquê |
|-----------|--------|
| Loop evolutivo p/ melhorar constante do kangaroo | Bancada baseline ainda não concluiu (EC puro lento); ganho seria só de constante (não fura √N) |
| Writeup público da metodologia | Aguarda sua decisão de veículo (GitHub/blog/BitcoinTalk) e enquadramento da marca |
| Participar de pool distribuído (#135) | Exige GPU; pool aparE com 0 workers; preocupação energética/ambiental sua |

---

## Conclusão honesta em uma linha

Esgotamos os domínios **1, 4, 5** (teorema + empírico com poder medido) e a fatia testável do
**3**; o **2-genérico** é teorema (√N), o **2-não-genérico/quântico** permanece aberto por
princípio. Não há atalho barato. O único resíduo legítimo é empírico e provavelmente vazio:
*o gerador de 2015 era incompressível?* — e mesmo um "não" parcial seria fraco demais para
tornar #71 factível sem compute.
