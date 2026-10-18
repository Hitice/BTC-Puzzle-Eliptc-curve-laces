---
name: puzzle-research
description: Protocolo de pesquisa do repositorio Bitcoin Puzzle (saatoshi_rising, 2015). Use sempre que trabalhar neste repo - ao receber uma ideia ou hipotese nova do usuario sobre como as chaves foram geradas, implementar ou rodar uma varredura de seed (master_seed_sweep, run_sweeps, sweep_ctl), registrar cobertura ou status em HYPOTHESES.json, avaliar se um resultado negativo "fecha" algo, investigar software/PRNG historico (bx, Electrum, bitcoinj, JS, Python random), ou diante de qualquer ACERTO/hit, chave candidata ou seed recuperada - mesmo que o usuario nao cite o protocolo.
---

# Pesquisa do Bitcoin Puzzle

O objetivo do repo e achar um caminho de solucao que nao seja forca bruta nem
Kangaroo. O unico caminho que nao prejudica o Bitcoin e uma fraqueza especifica do
gerador de 2015 (seed recuperavel). Estado atual: `python3 analysis/status.py`;
contexto: `BRIEFING.md` (nao leia os .md marcados como historico).

## 1. Divisao de papeis: imaginacao do usuario, exaustao sua

O usuario traz ideias, inclusive especulativas ou de pesquisa em estagio
intermediario. Sua parte e transformar cada ideia em teste e esgotar as variantes
simples dela, inclusive as nao obvias. Prior baixo muda a ORDEM da fila, nao decide
se a ideia merece teste. Conhecimento conta: a H9 (bx 2.0) saiu de ler codigo-fonte
historico, nao de compute.

Para cada ideia:

1. **Formalize** como um processo gerador concreto: qual programa/comando, em que
   data, produziria as 256 chaves e como. Se nao der para escrever o pseudocodigo,
   a ideia ainda nao e testavel; diga o que falta e proponha a versao testavel mais
   proxima, em vez de descartar.
2. **Procure a fonte primaria**: codigo da versao exata (git tag/commit pela data,
   ex. `git rev-list -1 --before=2015-01-15`), spec, paper. Releia o que o codigo
   faz de fato; documentacao e paginas de terceiros erram (ex.: Milksad dizia "MSB",
   o codigo usa `% 255`).
3. **Enumere as variantes** pelas dimensoes abaixo antes de rodar qualquer coisa.
4. **Estime custo** (candidatos x taxa medida) e ordene: barato e plausivel primeiro.
5. **Controle positivo**, depois varredura, depois registro (secoes 2-4).

Dimensoes de variante que costumam ser esquecidas:
- **Fonte da seed**: inteiro, timestamp (s, ms, us), frase, PRNG (qual biblioteca,
  qual plataforma: libstdc++/libc++/MSVC diferem), bytes de outro hash.
- **Codificacao**: tamanho em bytes, endianness, hex vs bytes, ASCII, com/sem `\n`,
  bugs de reducao (`% 255`, `& 0xff`, MSB).
- **Derivacao**: BIP32 caminho (`m/i`, `m/0/i`, `m/0h/i`, `m/44h/...`), endurecido ou
  nao, Electrum v1 ramo, hash sequencial/encadeado.
- **Indice**: base 0 ou 1, stride, ordem reversa, descarte por rejeicao.
- **Mascara**: `low` (declarada), `high`, `low_le`.

## 2. A regra que governa o repo

Nenhuma hipotese fecha sem controle positivo executado: uma instancia sintetica
que o teste comprovadamente detecta. Sem isso o resultado e "sem poder", nao
"negativo". A auditoria de poder mostrou testes estatisticos aprovando um BIP32
com seed de 32 bits; nao repita a classe "estatistica das 82 chaves".

Ao implementar um gerador/encoder novo:
- Valide contra a implementacao original sempre que possivel: compile o trecho
  C/C++ real (scratchpad), compare centenas de seeds, use vetores normativos
  (ex. [rand.predef]: minstd_rand0 10000a saida = 1043618065).
- Adicione o par (familia, encoder) ao `self_test()` do `master_seed_sweep.py` e
  rode `python3 analysis/master_seed_sweep.py --self-test` (todos devem passar).

Um negativo exclui so a combinacao exata testada. Ao relatar, liste o que ficou
de fora.

Nao assuma que as 256 chaves sairam de uma unica geracao. As primeiras podem ter
sido feitas a mao (#1-#4 = 1, 11, 111, 1000 em binario), pode haver lotes, offsets
ou dois geradores intercalados. Cada chave com n bits e sozinha um filtro de
2^-(n-1); nunca descarte um candidato por falhar nas outras. No sweep:
- acerto so da ancora vai para `anchor_only` (antes de 2026-10-18 era descartado;
  JSON sem esse campo = modelo de carteira unica, refazer com
  `analysis/rerun_old_sweeps.py`);
- `--skip-below N --index-base=-K`: primeiras chaves fora, carteira comecando depois;
- `--any-index J`: cada filho 0..J-1 contra todas as chaves com n >= 56 (intercalacao,
  lotes, ordem qualquer); custo ~J vezes maior.
Estatistica de padrao nao enxerga mistura de geradores; o teste exato por chave, sim.

## 3. Ledger (HYPOTHESES.json)

- Nunca edite `HYPOTHESES.json` a mao. Hipoteses estaticas ficam em `STATIC` dentro
  de `analysis/build_hypotheses.py`; a cobertura de varredura vem sozinha de
  `analysis/sweeps/*.json`. Depois de mexer: `python3 analysis/build_hypotheses.py`.
- Cada linha de cobertura vale so para o seu (family, encoder, mask, index_map).
  Confira essas colunas antes de citar cobertura.
- Atualize o ledger e o BRIEFING; nao crie novos .md de conclusao.

## 4. Filas de varredura

- `./analysis/run_sweeps.sh`, `./analysis/run_sweeps_h2.sh`; `JOBS=8` usa o M3 inteiro.
- `./analysis/sweep_ctl.sh {status|pause|resume|stop|nice}`. `pause` = SIGSTOP, sem perda.
- Nao ha checkpoint: um item interrompido recomeca do zero. Os scripts pulam itens
  cujo JSON ja existe (o JSON so e gravado no fim).
- Filas ja morreram em silencio. Antes de citar cobertura, confira que o JSON
  existe e que `candidates` cobre a faixa pretendida.
- Taxas medidas (8 proc.): hashseq ~5 M/s; BIP32 endurecido ~1 M/s; BIP32 com
  um `k*G` ~16-20 k/s (secp_fast em Python e o gargalo).

## 5. Se aparecer um acerto

Um acerto da a seed e, com ela, todas as chaves restantes (~900 BTC). O risco
passa a ser vazamento e front-running, nao matematica.

1. **Nao cole seed nem chave na conversa**, em commits ou em logs. O transcript e
   os logs saem da maquina; o git e para sempre.
2. Tire o JSON da varredura do repositorio antes de qualquer `git add`: ele contem
   `seed_hex` e `predicted_71`. Mova para fora do repo com permissao 0600.
3. Verifique de forma independente, sem imprimir segredos:
   ```bash
   python3 .claude/skills/puzzle-research/scripts/verify_hit.py --self-test
   python3 .claude/skills/puzzle-research/scripts/verify_hit.py \
       --family bip32 --path m/i --encoder bx2-minstd0 --candidate <t> [--mask ...]
   ```
   Confirmado = 82/82 chaves resolvidas, 160/160 enderecos e 96/96 pubkeys
   #161-#256. Os segredos vao para `~/puzzle-hit-*.json` (0600, fora do repo).
4. **Nada vai para a mempool publica.** #66 e #69 foram roubados por bots via RBF.
   Gasto so por mineracao privada (pool que inclua a tx sem broadcast). Pare e
   decida com o usuario antes de qualquer transacao.

## 6. Comunicacao

Relate cobertura, nao promessas: o que rodou, quantos candidatos, controles,
o que ficou fora. Nao infle nem descarte por prior; separe fato verificado de
inferencia. Nao tente identificar a pessoa por tras de saatoshi_rising: a OSINT
busca artefatos tecnicos (codigo, MPK, seed), nao a identidade.
