# Electrum 1.9.8: origem da seed e localização da MPK

Data da leitura: 2026-09-07. Auditoria estática de fontes públicas, não execução
da carteira histórica. Não foi identificado vínculo entre essa versão e o puzzle.

## Caminho efetivo da criação

A fábrica `Wallet.__new__` seleciona `OldWallet` para uma carteira nova por padrão.
Seleciona `NewWallet` se a opção `bip32` estiver explicitamente habilitada. Portanto,
a existência de classes BIP32 não significa que fossem o padrão dessa versão.

Em `OldWallet.init_seed`, uma seed ausente provoca `random_seed(128)`. Uma seed
fornecida pelo usuário segue outro caminho e pode ser hexadecimal ou mnemônica.
Logo, a segurança da criação automática não demonstra a entropia de seeds importadas.

Fonte: [wallet.py](https://raw.githubusercontent.com/spesmilo/electrum/1.9.8/lib/wallet.py),
`OldWallet.init_seed` e `Wallet.__new__`.

`random_seed` chama `ecdsa.util.randrange(2**128)` e formata o resultado como
hexadecimal de 32 caracteres. Não usa timestamp nessa função.

Fonte: [bitcoin.py](https://raw.githubusercontent.com/spesmilo/electrum/1.9.8/lib/bitcoin.py),
`random_seed`.

## Origem dos bytes na dependência

O instalador exige `ecdsa>=0.9`, sem fixar uma versão exata. Nas tags 0.9 e 0.10
examinadas, `randrange` usa `os.urandom` quando o chamador não fornece uma função
de entropia. O caminho acima não fornece essa função. A seleção do inteiro usa
rejeição de candidatos fora do intervalo; não usa o módulo Python `random`.

Fontes:

- [setup.py](https://raw.githubusercontent.com/spesmilo/electrum/1.9.8/setup.py)
- [python-ecdsa 0.9 util.py](https://raw.githubusercontent.com/tlsfuzzer/python-ecdsa/python-ecdsa-0.9/ecdsa/util.py)
- [python-ecdsa 0.10 util.py](https://raw.githubusercontent.com/tlsfuzzer/python-ecdsa/python-ecdsa-0.10/ecdsa/util.py)

**Inferência limitada:** enumerar horários ou estados do Mersenne Twister não
reproduz esse caminho padrão. Uma hipótese de RNG fraco precisa indicar uma falha
do ambiente, substituição da fonte de entropia, outra versão ou seed fornecida
externamente. Nada disso foi demonstrado para o puzzle nesta investigação.

Isso também não certifica `os.urandom` em qualquer sistema de 2015. Não conhecemos
o sistema operacional, build da dependência, estado do sistema ou código do criador.
A tag 0.11 não foi examinada: a leitura pela ferramenta falhou.

## A MPK aparece automaticamente na blockchain?

O código de assinatura reconhece um `KeyID` do formato `old(MPK,ramo,indice)`.
Esse é um artefato útil se existir um arquivo público de transação incompleta
com procedência. A existência do campo não implica que seja publicado on-chain.

`Transaction.get_input_info` inclui `KeyID` nos metadados. `as_dict` anexa esses
metadados quando a transação está incompleta. Já `serialize` monta a entrada P2PKH
assinada com assinatura e pubkey do filho; não escreve `KeyID` no script.

Fontes: [wallet.py](https://raw.githubusercontent.com/spesmilo/electrum/1.9.8/lib/wallet.py),
`add_keypairs_from_KeyID`; [transaction.py](https://raw.githubusercontent.com/spesmilo/electrum/1.9.8/lib/transaction.py),
`serialize`, `get_input_info` e `as_dict`.

**Consequência prática:** as pubkeys extraídas dos gastos dos puzzles não devem
ser tratadas automaticamente como MPKs. Para usar `electrum_old_mpk.py`, falta
uma candidata independente: publicação de carteira somente de observação,
metadados de transação incompleta ou outro artefato público com vínculo ao desafio.
Não encontramos esse artefato nesta rodada.

## Decisão de pesquisa

Manter Electrum antigo como hipótese sem identificação positiva. A busca por
timestamp/PRNG de propósito geral perde prioridade para essa implementação padrão.
Continuam distintos: geração automática, importação de seed e código personalizado
de derivação/máscara. Não há nesta rodada recuperação de seed ou chave de puzzle.
