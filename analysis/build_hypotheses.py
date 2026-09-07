#!/usr/bin/env python3
"""Gera HYPOTHESES.json: o registro de hipoteses do repositorio.

Regra do repositorio: uma hipotese so pode ter status "closed" se
positive_control.executed for true. Sem controle positivo o status maximo e
"no-power" (o teste rodou mas nao detectaria a hipotese nem se ela fosse
verdadeira) ou "covered" (varredura exaustiva de um espaco declarado).

A cobertura das varreduras e lida de analysis/sweeps/*.json, entao este arquivo
se mantem atualizado sozinho. Rode depois de cada varredura.
"""
import glob, json, os, subprocess, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
OUT = os.path.join(ROOT, "HYPOTHESES.json")

STATIC = [
 {"id": "H0-stats", "title": "Padrao estatistico nas chaves resolvidas",
  "statement": "As 82 chaves conhecidas exibem autocorrelacao, periodicidade, bias modular, "
               "bias de bit ou compressibilidade detectavel.",
  "space": "82 chaves; lags 1-5; primos <=47; FFT; zlib/bz2/lzma",
  "test": {"scripts": ["statistics.py", "test_autocorrelation.py", "test_nibble_fft.py",
                       "gap_analysis.py", "mod23_deepdive.py", "verify_signals.py",
                       "power_and_changepoint.py"]},
  "positive_control": {"required": True, "executed": True,
                       "result": "FALHOU: conjunto sintetico BIP32 com seed de 32 bits "
                                 "(quebravel em 22 s) passa em todos os testes."},
  "power_against_weak_seed": "zero",
  "status": "no-power",
  "note": "Resultado negativo NAO e evidencia de gerador forte. Nao repetir."},

 {"id": "H0-ec", "title": "Estrutura explotavel na secp256k1 ou entre pubkeys",
  "statement": "Existe relacao multiplicativa/aditiva pequena entre pubkeys expostos, "
               "ou estrutura nao-generica na curva.",
  "space": "6 pubkeys; m < 2^16; t < 2^20",
  "test": {"scripts": ["pubkey_relations.py", "orbit_compressibility.py", "scale_sweep.py"]},
  "positive_control": {"required": True, "executed": False},
  "power_against_weak_seed": "n/a",
  "status": "open-but-negligible-prior",
  "note": "Se existisse, quebraria toda a Bitcoin. Custo alto, prior desprezivel. Nao repetir."},

 {"id": "H0-nonce", "title": "Fraqueza de nonce ECDSA nas assinaturas do criador",
  "statement": "Reuso de r, nonce pequeno, ou nonce relacionado permite recuperar chave.",
  "space": "116 assinaturas (96 de 2017 + 20 de 2019); k < 2^127 e k = 2^j*u nos 5 alvos",
  "test": {"scripts": ["ecdsa_signatures.py", "../breach-review/single_signature_lattice.py"]},
  "positive_control": {"required": True, "executed": True,
                       "result": "PASSOU: reticulado recupera chave sintetica de 140 bits "
                                 "com UMA assinatura, nos dois modelos de nonce."},
  "power_against_weak_seed": "n/a",
  "status": "covered",
  "coverage": "20.454 verificacoes de chave publica, 0 correspondencias, nos 5 alvos. "
              "Nenhum r repetido em 116 assinaturas. 15/15 nonces de 2019 batem RFC 6979.",
  "note": "Fecha os dois modelos testados, nao todos os geradores de nonce. "
          "Bug corrigido em 2026-09-07: r nao e k (ecdsa_signatures.py)."},

 {"id": "H1-forensics", "title": "Atribuicao do software das transacoes do criador",
  "statement": "Os indicadores de construcao e assinatura das 5 transacoes do criador "
               "identificam o software usado, restringindo o gerador de 2015.",
  "space": "nVersion, nLockTime, nSequence, ordenacao de entradas/saidas, taxa absoluta "
           "vs por vB, low-S, DER estrito, ints minimos, compressao de pubkey, politica de troco",
  "test": {"scripts": ["creator_tx_forensics.py"], "data": "data/creator_txs.json"},
  "positive_control": {"required": True, "executed": False,
                       "note": "Controle valido: pegar transacoes de origem conhecida da mesma "
                               "epoca (Core 0.9/0.10, Electrum 1.9.x, blockchain.info, pybitcointools) "
                               "e verificar que os indicadores as separam."},
  "status": "open",
  "facts_extracted": [
      "2015: nVersion=1; 2017/2019/2023: nVersion=2. nSequence sempre 0xFFFFFFFF, locktime 0.",
      "2015: a UNICA assinatura e low-S -> sem informacao (50% por acaso). NAO tratar como fingerprint.",
      "2017: 97/97 low-S -> normalizacao deterministica em 2017 (p=2^-97 por acaso).",
      "Todas as transacoes tem saidas em ordem crescente de valor; em 2015 sao 256 valores "
      "distintos, ou seja as saidas estao em ordem de indice do puzzle.",
      "Taxas absolutas redondas (0,004 / 0,02 / 0,01 BTC) sugerem construcao manual/script, "
      "nao estimativa de carteira grafica.",
      "Entrada de financiamento do criador (1CENDvi6...) usa pubkey NAO comprimida; "
      "todas as 256 chaves do puzzle usam pubkey comprimida."],
  "next": "Pesquisa externa sobre comportamento de carteiras de 2014-2015 e execucao do controle."},

 {"id": "H2-mask-variants", "title": "Variantes de mascara e de indice",
  "statement": "O mapeamento chave-filha -> chave-de-puzzle nao e truncamento dos bits baixos "
               "com indice consecutivo a partir de 0 ou 1.",
  "space": "truncamento de bits altos (child >> (256-n)); amostragem por rejeicao; "
           "offset de indice arbitrario; ordem invertida (#256 = indice 0); ramo de troco; "
           "indices intercalados",
  "test": {"scripts": ["master_seed_sweep.py"], "status": "NAO IMPLEMENTADO"},
  "positive_control": {"required": True, "executed": False},
  "status": "open",
  "criticality": "ALTA: se o modelo de mascara estiver errado, TODA cobertura registrada "
                 "em H3-seed-sweep e vazia."},

 {"id": "H3-seed-sweep", "title": "Seed mestre fraca ou enumeravel",
  "statement": "A seed mestre do gerador de 2015 veio de fonte enumeravel (inteiro pequeno, "
               "timestamp, PRNG nao-criptografico, frase escolhida).",
  "space": "ver coverage; ancora = puzzle #130 (129 bits), confirmacao nas outras 81 chaves",
  "test": {"scripts": ["master_seed_sweep.py"], "command": "./analysis/run_sweeps.sh"},
  "positive_control": {"required": True, "executed": True,
                       "result": "PASSOU 8/8: recupera a seed em bip32 (4 caminhos), hashseq (2), "
                                 "hashchain e electrum1; rejeita conjunto adulterado em 1 bit; "
                                 "nao acerta os dados reais na faixa de controle."},
  "false_positive_rate": "2^-129 por candidato na ancora; medido empiricamente com filtro "
                         "enfraquecido a 20 bits: 35 observados vs 40,0 esperados (-0,79 sigma)",
  "status": "open",
  "coverage": "PREENCHIDO AUTOMATICAMENTE"},

 {"id": "H4-osint", "title": "Artefato publico do criador",
  "statement": "Existe artefato publico (post, gist, pastebin, carteira watch-only, metadados "
               "de transacao incompleta) que revela a implementacao, a MPK ou a seed.",
  "space": "conta saatoshi_rising no BitcoinTalk; 1CENDvi6tmKGrR8RxqwURpX9WHbbKip1db; "
           "origem do reforco de 2023; buscas por codigo de 2015 gerando 256 chaves com mascara",
  "test": {"scripts": [], "note": "pesquisa manual/web; sem compute"},
  "positive_control": {"required": False, "note": "hipotese de busca, nao de teste estatistico"},
  "status": "open",
  "note": "Unico caminho em que um unico achado encerra o problema. Custo zero de compute."},
]


def sweep_coverage():
    rows = []
    for p in sorted(glob.glob(os.path.join(HERE, "sweeps", "*.json"))):
        try:
            d = json.load(open(p))
        except Exception:
            continue
        if "candidates" not in d:
            continue
        rows.append({"file": os.path.relpath(p, ROOT), "family": d.get("family"),
                     "encoder": d.get("encoder"), "index_base": d.get("index_base"),
                     "range": d.get("range"), "candidates": d.get("candidates"),
                     "anchor_puzzle": d.get("anchor_puzzle"),
                     "anchor_bits": d.get("anchor_bits"),
                     "hits": d.get("hits"), "elapsed_s": d.get("elapsed_s")})
    return rows


def main():
    try:
        commit = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "HEAD"],
                                         text=True).strip()
    except Exception:
        commit = None
    hyp = json.loads(json.dumps(STATIC))
    cov = sweep_coverage()
    for h in hyp:
        if h["id"] == "H3-seed-sweep":
            h["coverage"] = cov
            h["candidates_total"] = sum(r["candidates"] for r in cov)
            h["hits_total"] = sum(len(r["hits"] or []) for r in cov)
    doc = {
        "rule": "Nenhuma hipotese pode ter status 'closed' sem positive_control.executed == true. "
                "Sem controle positivo o resultado e 'no-power', nao 'negativo'.",
        "generated": datetime.date.today().isoformat(),
        "commit": commit,
        "entry_point": "BRIEFING.md",
        "hypotheses": hyp,
    }
    with open(OUT, "w") as f:
        json.dump(doc, f, indent=1, ensure_ascii=False)
    print("HYPOTHESES.json: %d hipoteses, %d varreduras, %d candidatos, %d hits"
          % (len(hyp), len(cov), sum(r["candidates"] for r in cov),
             sum(len(r["hits"] or []) for r in cov)))


if __name__ == "__main__":
    main()
