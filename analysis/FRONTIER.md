> **HISTÓRICO — NÃO LEIA POR PADRÃO.** O ponto de entrada é [BRIEFING.md](../BRIEFING.md). Estado-da-arte de 2025; parcialmente desatualizado (#135 já foi resolvido).

# Fronteira — Criptoanálise Real, Mitos, e Como Participar de Verdade

> Survey honesto do estado-da-arte (jun/2026) separando o que é real do que é fantasia.
> Foco: o que está fora do toolkit padrão E é legítimo, e o caminho realista para o usuário
> participar da solução de um puzzle. Cada fato tem fonte.

## 0. Mito vs. realidade (leia antes de sonhar)

| Alegação | Veredito | Evidência |
|----------|----------|-----------|
| NSA/governo tem quebra secreta de ECDLP | **Mito** | Se existisse ataque sub-exponencial a secp256k1, TLS/bancos/PKI cairiam junto. Não há sinal disso. |
| Existe ataque não-genérico a secp256k1 | **Falso** | secp256k1 não tem estrutura explorável por index-calculus; segurança é puramente genérica Θ(√n). (arXiv 2508.14011) |
| LLMs "não sabem" técnicas que quebrariam | **Mito** | O melhor algoritmo público (Kangaroo, O(√n)) *é* o melhor conhecido. O que falta nos modelos são constantes/engenharia, não criptoanálise secreta. |
| Quântico resolve hoje | **Não** | Shor em secp256k1 exige ~2.330 qubits lógicos / ~317M físicos / 126M portas Toffoli. Não existe. (arXiv 2508.14011) |

**Conclusão honesta:** não há atalho matemático escondido. A dificuldade é real e computacional.

## 1. Estado-da-arte dos algoritmos (interval DLP)

Para os puzzles com pubkey exposta (#135,140,145,150,155,160), o segredo está num
**intervalo** conhecido → algoritmos de interval-DLP, não Shor.

| Algoritmo | Custo médio | Memória | Nota |
|-----------|-------------|---------|------|
| Pollard Kangaroo (clássico) | ~2.0·√N | baixa | base histórica |
| **RCKangaroo (RetiredCoder)** | **~1.15·√N** | baixa | **SOTA**; resolveu #130 (2024) |
| Gaudry-Schost | ~1.66·√N | baixa | interpola rho/kangaroo |
| Interleaved BSGS / grumpy-giants | melhor *average-case* | **√N (inviável)** | + rápido em ops, mas memória mata em #135 |
| + negation map | ×√2 speedup | — | aplicável em rho/kangaroo |

**Insight de fronteira (real, sub-implementado):** Galbraith-Wang-Zhang mostram que BSGS
intercalado supera kangaroo em *operações médias*. Por que ninguém usa em #135? **Memória**:
BSGS precisa de ~√N ≈ 2^67 entradas armazenadas — fisicamente impossível. Por isso kangaroo
(memória ~constante via distinguished points) vence na prática. Não é descuido da comunidade;
é trade-off correto. Útil só para puzzles bem menores.

## 2. Recordes recentes (a régua real)

- **#130** resolvido em 2024 via RCKangaroo (RetiredCoder) — maior interval-DLP secp256k1
  resolvido no contexto dos puzzles.
- Pons & Zieniewicz: intervalo de **114 bits** quebrado (referência acadêmica).
- Clusters de GPU avançaram intervalos secp256k1 até ~**129 bits** (alegado).
- **#135 (2^134..2^135) segue não resolvido** — ~**2^67.5 operações** com K=1.15.

## 3. A matemática crua de #135 (sem ilusão)

- Operações necessárias: ~2^67.5 ≈ **1.9 × 10^20**.
- RTX 4090 com collider: ~8 GKeys/s = 8×10^9/s.
- **1 GPU sozinha:** ~740 anos. **Pool de 1.000 RTX 4090:** ~9 meses. **10.000 GPUs:** ~1 mês.
- Ou seja: solucionável **coletivamente**, não individualmente. Participação = contribuir uma
  fatia de compute, não resolver sozinho.

## 4. Caminho REAL de participação

### Opção A — Pool distribuído de Kangaroo para #135 (mais realista)
- Ferramenta: `collider` (hevnsnt) — CUDA + Metal (Apple Silicon), K=1.15, v1.4.1 (mai/2026).
- Pool: `collisionprotocol.com` → `./collider --pool pool.collisionprotocol.com:17403 --worker <btc-address>`.
- Modelo: cada worker roda kangaroos TAME-only ou WILD-only; **o servidor é o único que
  recupera a chave** (anti-cheat). Recompensa proporcional aos distinguished points enviados,
  taxa ~5%.
- **Risco a verificar:** pool mostrava 0 workers ativos — confirmar se está vivo antes de
  comprometer compute. Alternativa: rodar `collider`/`RCKangaroo` em pool próprio/coletivo.
- Hardware honesto: precisa de GPU NVIDIA decente; sem isso, contribuição é marginal.

### Opção B — Brute-force pool para #71 (loteria)
- Sem pubkey → só força bruta sobre 2^70. ~316 anos na velocidade agregada atual da comunidade.
- Participar = sortear uma sub-faixa e torcer. Odds individuais ~loteria, mas é "participação".

### Opção C — A contribuição que está ao nosso alcance de verdade (ver §5)

## 5. O que NÓS podemos contribuir publicamente (honesto)

Não temos uma quebra criptográfica — ninguém tem. Mas há contribuição **real e rara**:

1. **Metodologia de resultado-negativo rigorosa.** A maioria dos "puzzle hunters" persegue
   padrões-fantasma. Nós aplicamos Monte Carlo + permutação + Bonferroni + **análise de poder**
   (efeito mínimo detectável). Publicar isso **poupa esforço da comunidade** e é metodologia
   genuinamente pouco usada nesse nicho. Ver [FINDINGS.md §10](FINDINGS.md).
2. **Dataset reprodutível e legível por IA** (`../data/puzzles.json` + scripts stdlib puros).
3. **Survey honesto fato-vs-mito** (este arquivo) — combate desinformação sobre "quebras
   secretas" que circula em fóruns.

> Enquadramento honesto da "contribuição da Anthropic": é **rigor metodológico e ferramental
> aberto**, não um break. Reivindicar quebra criptográfica seria falso e prejudicaria a
> credibilidade. O valor real é mostrar *como descartar fraqueza de gerador corretamente* e
> *quantificar o que NÃO se pode afirmar*.

## 6. Próximos passos sugeridos (acionáveis)

- [ ] Verificar se `collisionprotocol.com` está ativo; se sim, decidir orçamento de GPU.
- [ ] Avaliar `RCKangaroo` (RetiredCoder) como engine alternativa para #135.
- [ ] Rascunhar writeup público da metodologia de resultado-negativo (ver `PUBLIC_WRITEUP.md`).
- [ ] (Opcional) Replicar nossos testes em #135-160 quando/se mais assinaturas surgirem.

## Fontes

- [arXiv 2508.14011 — Brace for impact: ECDLP challenges for quantum cryptanalysis](https://arxiv.org/abs/2508.14011)
- [BitcoinTalk — Solving ECDLP with Kangaroos (RCKangaroo, RetiredCoder)](https://bitcointalk.org/index.php?topic=5517607)
- [GitHub — hevnsnt/collider (K=1.15)](https://github.com/hevnsnt/collider)
- [Collision Protocol — pool #135](https://collisionprotocol.com/)
- [GitHub — JeanLucPons/Kangaroo](https://github.com/JeanLucPons/Kangaroo)
- [Galbraith, Wang, Zhang — Improved BSGS for interval ECDLP (eprint 2015/605)](https://eprint.iacr.org/2015/605.pdf)
