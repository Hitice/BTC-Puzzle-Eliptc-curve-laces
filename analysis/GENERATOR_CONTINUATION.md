# Continuação: origem das chaves

Data: 2026-09-07. Investigação preliminar; nenhuma chave nova recuperada.

## Estado herdado

`breach-review/REVISAO.md` corrige o alcance das conclusões anteriores. Os resultados
salvos excluem dois modelos restritos de nonce para cinco assinaturas, não todos os
geradores. Os 116 testes de assinatura e as 83 chaves conferidas pertencem à auditoria
anterior relatada pelo usuário; seu pacote completo não está neste workspace.

## Evidência pública conferida nesta continuação

A mensagem de 27/04/2017 do usuário que se apresenta como criador descreve chaves
consecutivas de uma carteira determinística, com máscara de zeros iniciais e um bit 1.
Não especifica carteira, versão, seed, caminho ou índice inicial. A declaração não é
uma identificação de BIP32 nem uma demonstração de segurança do gerador.

Fonte: https://bitcointalk.org/index.php?topic=1306983.msg18765941#msg18765941

A página https://privatekeys.pw/puzzles/bitcoin-puzzle-tx não pôde ser aberta pela
ferramenta de navegação nesta sessão. Não foi feita atualização de saldos/status.

## Hipótese histórica concreta: Electrum OldAccount

O código da versão 1.9.8 contém um esquema determinístico anterior ao modelo BIP32:

- `stretch_key`: 100.000 iterações de SHA256 sobre estado concatenado à seed original;
- `get_sequence`: hash de índice decimal, ramo e chave pública mestra;
- chave filha: soma do expoente mestre com o resultado de `get_sequence`, módulo n.

Fonte primária: https://raw.githubusercontent.com/spesmilo/electrum/1.9.8/lib/account.py

Hipótese a testar: as chaves do puzzle são o resultado dessa derivação, posteriormente
mascarado como `2**(i-1) | (child & (2**(i-1)-1))`.

O modelo não é coberto por testar apenas `H(seed || índice)` ou `H(chave mascarada)`.
Isso justifica mantê-lo como candidato, não classificá-lo como provável ou vulnerável.
Não encontramos evidência que vincule Electrum ao criador.

O código antigo exporta chaves não comprimidas. Isso não elimina uma derivação interna
seguida de máscara e exportação própria em formato comprimido; exige distinguir
derivação e serialização no experimento.

## Dados necessários e critério de teste

1. Fixar uma fonte independente de candidatos a seed ou chave pública mestra. Sem
   isso, o nome da carteira sozinho não produz um ataque eficiente.
2. Reproduzir o código histórico, inclusive bytes, função Hash, ramo, índice inicial
   e redução modular; validar primeiro em controles sintéticos independentes.
3. Fixar as variantes antes da comparação real. Usar #32, #50 e #70 como filtros e
   reservar outras chaves para confirmação. Esses índices já foram usados em controles
   anteriores: o conjunto reservado é validação do modelo, não dados nunca examinados.
4. Exigir igualdade exata e reprodução dos endereços. Registrar número de candidatos,
   parâmetros e cobertura. Ausência de correspondência exclui só a busca executada.

## BIP32 como candidato separado

BIP32 exige cadeia de derivação e chain code; determinismo não identifica esse padrão.
A especificação descreve o risco de chave privada filha não endurecida em conjunto
com chave pública estendida do pai. Uma chave do puzzle mascarada não é automaticamente
a chave filha original, e uma pubkey comum não é uma chave pública estendida.

Fonte primária: https://raw.githubusercontent.com/bitcoin/bips/master/bip-0032.mediawiki

## Próximo trabalho justificado

Procurar evidência pública sobre implementação e artefatos de derivação. Priorizar
candidatos por ligação histórica verificável, não por semelhança estatística.
Não iniciar enumeração arbitrária de seeds nem declarar uma carteira identificada.

## Rodada executada: filtro de MPK e verificação independente

### Resultado histórico

Não foi encontrada nesta busca uma seed ou MPK com vínculo demonstrado ao puzzle.
A cronologia sozinha não identifica Electrum: `account.py` da própria versão 1.9.8
contém `OldAccount` e `BIP32_Account`. O código histórico do Armory também contém
derivação determinística. Não há fundamento para considerar Electrum a única
possibilidade apenas pela expressão usada na mensagem do criador.

Fontes primárias adicionais:

- https://raw.githubusercontent.com/spesmilo/electrum/1.9.8/lib/bitcoin.py (`Hash` é SHA256 duplo)
- https://raw.githubusercontent.com/etotheipi/BitcoinArmory/v0.92.3/armoryengine/PyBtcAddress.py
- https://raw.githubusercontent.com/spesmilo/electrum/master/tests/test_wallet_vertical.py (`test_electrum_seed_old`)

### Novo teste implementado

`electrum_old_mpk.py` recebe uma MPK pública candidata. Para cada filho calcula
`h_i = SHA256d(ascii(indice:ramo:) || MPK) mod n`. Se a chave mestre privada é m,
a chave original seria `x_i = (m + h_i) mod n`.

Uma chave resolvida do puzzle i fornece `x_i mod 2^(i-1)`. Logo:

```
m = (d_i - h_i + q_i*n) mod 2^(i-1), q_i em {0,1}
1 <= m + h_i - q_i*n <= n-1
```

O programa intersecta congruências e intervalos exatos para ambos os valores de
q_i. Representa os sobreviventes como progressões aritméticas, sem enumerar seeds
nem todos os valores de m. Um conjunto vazio rejeita a MPK com aquele mapeamento.
Um conjunto não vazio NÃO identifica m: ainda falta impor `m*G = MPK`.

O primeiro puzzle fornece zero bits livres, como deve ocorrer; acertos em puzzles
pequenos não são considerados identificação. O filtro pode rejeitar cedo quando
as restrições entre diferentes chaves forem contraditórias.

### Validação executada

- Quatro testes automatizados passaram.
- Vetor oficial Electrum: reprodução exata da MPK e dos endereços de recebimento
  e troco, verificando também a serialização da seed como texto hexadecimal.
- 1.000 sequências com cinco interseções cada: igualdade com uma referência
  exaustiva em módulos pequenos, incluindo ordens variadas de quantidade de bits.
- 12 controles sintéticos positivos (três mestres, dois ramos, dois deslocamentos)
  preservaram o mestre correto; as 12 versões com um bit alterado foram rejeitadas.
- As 82 chaves do arquivo local foram verificadas contra os 82 endereços e as
  82 pubkeys armazenadas, além de intervalo e codificação. Nenhuma divergência.
- Como controle negativo, a MPK do vetor oficial foi rejeitada nas quatro variantes:
  ramos 0/1 e filho inicial 0/1. Não há evidência de que essa MPK seja do criador;
  esse resultado não elimina a hipótese Electrum.

Resultados: `generator-review-results.json`. Os controles da revisão anterior
que dependem de `cryptography` não foram reproduzidos nesta rodada.

Reprodução, da raiz do repositório (Python 3.9+; somente biblioteca padrão, com RIPEMD160):

```bash
python3 -m unittest discover -s analysis -p test_electrum_old_mpk.py -v
python3 analysis/run_generator_review.py
python3 analysis/electrum_old_mpk.py --mpk HEX_DA_MPK_PUBLICA --output resultado.json
```

### O que falta para aplicar ao gerador real

Uma MPK pública candidata com procedência, ou um candidato de seed/implementação
com fundamento independente. Pubkeys comuns de puzzles não devem ser promovidas
a MPKs sem justificativa. O filtro cobre somente OldAccount, máscara dos bits baixos,
ramo fixo e os dois índices iniciais registrados; não cobre BIP32, Armory, índices
arbitrários, intercalados ou outras máscaras. Nenhuma chave nova foi recuperada.
