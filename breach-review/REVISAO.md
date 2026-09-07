# Bitcoin Puzzle: revisão do repositório e novos testes de brechas

Data: 7 de setembro de 2026. Repositório: [Hitice/BTC-Puzzle-Eliptc-curve-laces](https://github.com/Hitice/BTC-Puzzle-Eliptc-curve-laces). Versão examinada: `43961e513a5949f3d6f621bee70620db00dc5468`.

**Há erros verificáveis nos testes e no alcance de algumas conclusões. Nenhuma chave de puzzle ainda não resolvido foi recuperada nesta investigação.** Os erros justificam corrigir a pesquisa; não demonstram que exista uma brecha explorável no desafio.

O código foi clonado e lido após o repositório se tornar público. As 82 chaves resolvidas presentes nele coincidem com a base pública conferida criptograficamente na auditoria anterior desta conversa. Os valores `r`, `s` e as chaves públicas dos cinco alvos #140, #145, #150, #155 e #160 também coincidem com as assinaturas daquela auditoria. A base anterior contém ainda a chave publicada do #135, totalizando 83; a classificação de #135 no snapshot do repo está desatualizada em relação a esse conjunto.

## 1. O script confunde propriedades de `r` com propriedades do nonce

Em [ecdsa_signatures.py](https://github.com/Hitice/BTC-Puzzle-Eliptc-curve-laces/blob/43961e513a5949f3d6f621bee70620db00dc5468/analysis/ecdsa_signatures.py), a função `analyze_signatures` trata `r` pequeno como indício de nonce pequeno e apresenta a distribuição dos bytes de `r` como distribuição do nonce. A seção global também chama o primeiro byte de `r` de MSB do nonce.

A relação correta é:

\[
R=kG,\qquad r=x(R)\bmod n.
\]

`r` não é o inteiro `k`. Seus bits não são os bits do nonce. Um contraexemplo suficiente é `k=1`: o valor de `r` é a coordenada x do gerador, `79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798`, com **255 bits**.

O controle incluído gera uma assinatura válida com esse nonce, verifica-a e a entrega à função original do repo. O alerta de `r` pequeno não dispara. Portanto, os resultados desse teste não sustentam a conclusão de ausência de nonce pequeno. A ausência de repetição de `r` continua sendo uma observação útil, dentro das assinaturas efetivamente coletadas.

Há também uma limitação de cobertura: `get_outgoing_txs` consulta uma página de transações do endereço, sem percorrer o histórico por paginação. O número de assinaturas encontradas deve ser apresentado como cobertura da coleta, sem pressupor histórico completo.

## 2. Uma assinatura pode bastar quando existem restrições fortes

[SUMMARY.md](https://github.com/Hitice/BTC-Puzzle-Eliptc-curve-laces/blob/43961e513a5949f3d6f621bee70620db00dc5468/SUMMARY.md) e a seção 7 de [FINDINGS.md](https://github.com/Hitice/BTC-Puzzle-Eliptc-curve-laces/blob/43961e513a5949f3d6f621bee70620db00dc5468/analysis/FINDINGS.md) descartam reticulados/HNP pelo fato de haver uma assinatura por chave do criador. Isso é excessivo: o intervalo conhecido de `d`, combinado com uma restrição forte em `k`, pode permitir recuperação com uma assinatura.

Implementei `single_signature_lattice.py`, usando redução de Gauss em dimensão 2 e enumeração exata de um retângulo. A relação ECDSA é:

\[
sk\equiv z+rd\pmod n.
\]

Escrevendo `d=A+x`, `0 <= x < D`, e assumindo `k=f*u`, `1 <= u < K`:

\[
x\equiv au+b\pmod n,\quad a=sr^{-1}f\bmod n,\quad b=-zr^{-1}-A\bmod n.
\]

O programa usa a base `(nK, 0)`, `(aK, D)`, reduz essa base e calcula com frações exatas os limites dos coeficientes que podem atingir o retângulo permitido. Todos os candidatos dentro desses limites são examinados. Cada chave candidata precisa reproduzir a chave pública; uma correspondência também confere `x(kG) mod n = r`. Os dois sinais de `s` são testados, cobrindo a equivalência do nonce causada por low-S.

O limite de recursos não é interpretado como resultado negativo: se a caixa de coeficientes ultrapassar o teto, o programa interrompe com erro. Todos os dez testes reais terminaram sem atingir esse teto.

### Controles e resultados reais

Os controles recuperaram a chave sintética de um puzzle de 140 bits com **uma assinatura**, para cada um dos dois modelos. Controles com nonce fora dos modelos foram rejeitados. A enumeração foi ainda comparada a uma referência exaustiva com módulo 101, para todos os 101 valores possíveis do coeficiente `a`.

Nas assinaturas reais, foram testados estes limites, sempre incluindo o sinal equivalente módulo `n`:

| Puzzle | Nonce pequeno | Nonce com bits inferiores zero | Verificações de chave pública, somando os modelos | Correspondências |
| --- | --- | --- | ---: | ---: |
| #140 | `1 <= k < 2^127` | `k = 2^129*u`, `1 <= u < 2^127` | 4.097 | 0 |
| #145 | `1 <= k < 2^122` | `k = 2^134*u`, `1 <= u < 2^122` | 4.097 | 0 |
| #150 | `1 <= k < 2^117` | `k = 2^139*u`, `1 <= u < 2^117` | 4.091 | 0 |
| #155 | `1 <= k < 2^112` | `k = 2^144*u`, `1 <= u < 2^112` | 4.096 | 0 |
| #160 | `1 <= k < 2^107` | `k = 2^149*u`, `1 <= u < 2^107` | 4.073 | 0 |
| **Total** | | | **20.454** | **0** |

No segundo modelo também se exige `k < n`. O tempo medido para controles e varreduras foi aproximadamente 24,3 segundos neste ambiente; não é um benchmark universal.

Esse custo não significa enumerar `2^127` nonces. Com a relação modular e o intervalo da chave, a ordem de grandeza esperada de candidatos à congruência é `D*K/n`, cerca de 1.024 por sinal na configuração usada. Isso explica o ganho **sob a hipótese de nonce restrito**. Sem essa hipótese, a recuperação geral continua fora do que este experimento realiza.

O resultado exclui esses dois modelos, nesses limites, para essas cinco assinaturas. Não exclui todos os vieses, vazamentos, relações ou geradores de nonce.

## 3. O teste de gerador descarta uma lista pequena de candidatos

[weak_generator_scan.py](https://github.com/Hitice/BTC-Puzzle-Eliptc-curve-laces/blob/43961e513a5949f3d6f621bee70620db00dc5468/analysis/weak_generator_scan.py) testa sete seeds literais, sete codificações do índice e até oito funções hash. Isso é uma busca finita e bem definida. A conclusão de que a família de geradores fracos baseados em hash/índice está fechada não decorre desses testes.

O controle reproduzível usa:

```text
seed = 12345, codificada em dois bytes big-endian
d_i = máscara_do_puzzle_i(SHA256(seed || índice_i_em_quatro_bytes_big_endian))
```

O modelo e a seed foram fixados antes da avaliação. Ao receber 82 chaves sintéticas desse gerador, a função original `scan_index_hash` imprime que index/seed-hash foi rejeitado. Entretanto, enumerar as 65.536 seeds possíveis e conferir somente os índices #32, #50 e #70 recupera a seed exata. Ela acerta **79 de 79 chaves reservadas**, além do valor sintético do #71.

Essa pequena enumeração demonstra o efeito de uma seed fraca; não é uma solução para o puzzle real. Nenhuma evidência liga essa seed ou esse esquema ao gerador original.

O teste de hash-chain também tem alcance mais estreito que a conclusão sugerida. Ele calcula `H(d_i)`, onde `d_i` já foi mascarado. Uma carteira poderia manter um estado inteiro `x_i`, atualizar `x_(i+1)=H(x_i)` e publicar somente `máscara(x_i)`. As partes descartadas pela máscara alteram o hash. No controle, a cadeia verdadeira acerta **41 de 41 transições**; o teste que aplica hash à chave mascarada acerta **zero**. Isso diferencia os modelos, sem demonstrar vulnerabilidade da cadeia oculta.

## 4. Estatística e teoremas não fecham as hipóteses restantes

O repo reconhece algumas limitações em seus textos, mas outras conclusões excedem esses limites:

- **Não rejeitar uniformidade não identifica BIP32.** Geradores distintos, incluindo alguns com seeds fracas, podem produzir amostras sem os vieses procurados. A análise de poder cobre as alternativas simuladas; não limita o ganho de qualquer ataque concebível. O [NIST SP 800-22](https://csrc.nist.gov/pubs/sp/800/22/r1/upd1/final) distingue explicitamente teste estatístico de certificação criptográfica de um gerador.
- **Compressão comum não mede a complexidade de Kolmogorov.** Não comprimir com zlib/bz2/lzma não demonstra ausência de estrutura explorável. Uma descrição curta por programa e seed tampouco implica recuperação eficiente dessa seed.
- **O limite de Shoup tem um modelo definido.** O [trabalho original](https://www.shoup.net/papers/dlbounds1.pdf) limita algoritmos genéricos. Ele não é uma prova de impossibilidade de qualquer algoritmo que use a representação concreta da curva ou informação adicional sobre a geração das chaves.
- **A autorredução aleatória tem um custo dependente da densidade.** Se um resolvedor funciona numa fração `epsilon` dos pontos uniformes, deslocamentos aleatórios podem encontrá-la com custo esperado proporcional a `1/epsilon`, desde que o resultado seja verificável. Isso não descarta famílias fáceis extremamente esparsas, nem preserva automaticamente a informação sobre um gerador ao deslocar um ponto.
- **O oráculo de bits do demo recebe a chave verdadeira.** `bit_security_demo.py` assume expressamente um oráculo perfeito para ilustrar uma redução. O experimento não implementa esse oráculo a partir da chave pública. A redução precisa contabilizar o custo de todas as chamadas, o domínio e os erros para sustentar uma afirmação assintótica.

## 5. O que a evidência orienta a investigar

Na auditoria anterior desta conversa, **15 de 15 nonces recuperáveis das assinaturas de 2019** coincidiram exatamente com o primeiro candidato de HMAC-SHA256 do [RFC 6979](https://www.rfc-editor.org/rfc/rfc6979), considerando low-S. São as assinaturas dos puzzles #65, #70, ..., #135, cujas chaves já eram públicas no conjunto conferido. Essa é evidência forte sobre a geração dos nonces dessas assinaturas. Não revela a carteira ou a seed que produziu as chaves em 2015, e não permite afirmar que os cinco alvos restantes usam o mesmo procedimento.

A direção de pesquisa mais justificável com os dados disponíveis é **identificar a implementação do gerador original e testar falhas específicas dela**. A [mensagem pública do criador](https://bitcointalk.org/index.php?topic=1306983.msg18765941#msg18765941) descreve uma carteira determinística e uma máscara, sem fornecer ali os detalhes necessários para identificar a derivação.

Um próximo candidato útil precisa especificar software/versão ou uma evidência histórica que o vincule ao puzzle, formato da seed, derivação, índices e máscara. Deve reproduzir chaves conhecidas exatamente e prever chaves reservadas antes de ser considerado evidência de uma brecha. Correspondências precisam reproduzir o endereço público. Não há, nos materiais examinados, base para prometer que esse caminho resultará em uma solução.

## Reprodução e procedência

O pacote é independente do repositório. Não inclui o clone nem publica alterações nele. Arquivos principais:

| Arquivo | Conteúdo |
| --- | --- |
| `single_signature_lattice.py` | Dois testes exatos de nonce restrito, controles e verificação ECDSA |
| `target-signatures.json` | As cinco assinaturas públicas, com `r`, `s`, `z`, chave pública e índice da entrada |
| `lattice-results.json` | Resultados completos dos testes reais e controles |
| `counterexamples.py` | Controles do nonce `k=1`, seed de 16 bits e hash-chain |
| `counterexample-results.json` | Resultados e saída das funções originais executadas sobre dados sintéticos |
| `provenance.json` | Commit, hashes dos arquivos de origem e comparação dos dados |
| `SHA256SUMS` | Integridade dos arquivos entregues |

Os valores de `z` vieram da reconstrução de SIGHASH_ALL na auditoria anterior, que validou TXIDs, saídas anteriores e assinaturas. A transação dos cinco alvos é [17e4e323…](https://mempool.space/tx/17e4e323cfbc68d7f0071cad09364e8193eedf8fefbcbd8a21b4b65717a4b3d3), entradas 15 a 19, numeradas a partir de zero. Este novo pacote verifica as assinaturas sobre os hashes fornecidos; a reconstrução integral das transações está no pacote anterior `bitcoin-puzzle-lab.zip`.

Ambiente usado: Python 3.12.13, cryptography 46.0.0. Após extrair o ZIP:

```bash
cd breach-review
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python single_signature_lattice.py --self-test
.venv/bin/python single_signature_lattice.py --output reproduced-lattice.json
.venv/bin/python counterexamples.py --output reproduced-controls.json
```

Para reproduzir também a saída das funções originais sobre os controles, forneça um clone local da versão revisada:

```bash
.venv/bin/python counterexamples.py --repo /caminho/BTC-Puzzle-Eliptc-curve-laces --output reproduced-repo-controls.json
```

Esses experimentos são offline, usam dados públicos e controles sintéticos, e não criam transações.
