#!/usr/bin/env python3
"""Gera HYPOTHESES.json: o registro de hipoteses do repositorio.

Regra do repositorio: uma hipotese so pode ter status "closed" se
positive_control.executed for true. Sem controle positivo o status maximo e
"no-power" (o teste rodou mas nao detectaria a hipotese nem se ela fosse
verdadeira) ou "covered" (varredura exaustiva de um espaco declarado).

A cobertura das varreduras e lida de analysis/sweeps/*.json, entao este arquivo
se mantem atualizado sozinho. Rode depois de cada varredura.
"""
import glob, json, os, subprocess, datetime, hashlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
OUT = os.path.join(ROOT, "HYPOTHESES.json")

STATIC = [
 {"id": "H8-mpk-highindex-verifier", "title": "Teste exato de MPK pelas pubkeys expostas de #161-#256",
  "statement": "Para carteira aditiva com offset derivavel de dado publico, a identidade "
               "MPK + h_n*G - (P_n - 2^(n-1)G) == k_n * 2^(n-1)G com 0 <= k_n < ceil(N/2^(n-1)) "
               "aceita ou rejeita um candidato (mpk, branch, shift) sem nenhuma chave privada.",
  "space": "Ancoras n=248..256 (k_n de 512 a 2 candidatos); Electrum v1 offset; branch 0 e 1; "
           "shift de -64 a 64; candidatos = 148 pubkeys expostas do criador e dos puzzles.",
  "test": {"scripts": ["mpk_highindex_verifier.py"],
           "command": "python3 -B analysis/mpk_highindex_verifier.py",
           "evidence": "analysis/mpk-highindex-verifier-results.json"},
  "positive_control": {"required": True, "executed": True,
                       "result": "3 carteiras Electrum v1 sinteticas, 12/12 checagens: MPK verdadeiro "
                                 "aceito; shift errado, branch errado e MPK com 1 bit trocado rejeitados."},
  "status": "open",
  "coverage": "38.184 combinacoes testadas, zero correspondencias. Falso positivo 2/N ~ 2^-255 "
              "pela ancora n=256 sozinha (apenas 2 valores admissiveis de k).",
  "value": "Fornece a condicao que faltava em electrum_old_mpk.compatible(), m*G == MPK, usando "
           "SO dado publico. Torna H4 (OSINT) verificavel: qualquer MPK candidato que apareca em "
           "gist/pastebin/carteira watch-only e aceito ou rejeitado em milissegundos.",
  "next": "E um VERIFICADOR, nao um solver: nao reduz o custo de achar a MPK e nao toca #71 nem #140. "
          "Derivacao endurecida torna h_n incognito e anula o teste. Ampliar: offset BIP32 nao "
          "endurecido com chaincode candidato, e janela de shift maior se surgir um candidato real."},
 {"id": "H7-interval-polynomial", "title": "Pertinencia ao intervalo por polinomio de coordenadas",
  "statement": "Uma representacao e avaliacao compacta de F_I(X)=produto_(j em I)(X-x(jG)) "
               "permite decidir metades do intervalo mais barato que resolver o DLP por colisao.",
  "space": "Intervalo prometido dentro de [1,N/2); secp256k1; coeficientes modulo p; "
           "prototipo com larguras 16, 64 e 256 e inicio de 140 bits.",
  "test": {"scripts": ["interval_polynomial_lab.py", "interval_polynomial_structure.py"],
           "command": "python3 -B analysis/interval_polynomial_lab.py && "
                      "python3 -B analysis/interval_polynomial_structure.py",
           "evidence": ["analysis/interval-polynomial-results.json",
                        "analysis/interval-polynomial-structure-results.json"]},
  "positive_control": {"required": True, "executed": True,
                       "result": "41 chaves sinteticas recuperadas sem fornecer a chave ao solver; "
                                 "12 controles fora do intervalo rejeitados. Ambiguidade Q/-Q demonstrada "
                                 "e resolvida pela verificacao final do ponto completo."},
  "status": "open",
  "coverage": "Formulacao exata validada. Implementacao explicita nao acelera: enumera W pontos na "
              "preparacao; log2(W) decisoes custam W-1 multiplicacoes de campo por Horner, "
              "alem da verificacao final. Medidos 15, 63 e 255 nas tres larguras.",
  "degree_obstruction": "Um polinomio univariado nao nulo com W/2 raizes distintas tem grau >=W/2. "
                        "Isso nao limita por si so o tamanho de um circuito aritmetico que o representa.",
  "structure_audit": {
      "build_without_enumeration": "RESPONDIDO, sim e conhecido. Identidade verificada: "
          "Res_u(F_A(u), S3(u, x(sG), X)) = F_A(x(sG))^2 * F_{A+s}(X) * F_{A-s}(X), onde S3 e o "
          "terceiro polinomio de somatorio de Semaev (ePrint 2004/031). Coeficientes de "
          "F_{A+s}*F_{A-s} reconstruidos com ZERO multiplicacoes escalares sobre A, larguras 8 e 16. "
          "Sem ganho: o grau de saida e 2|A|, entao a propria lista de coeficientes ja custa 2|A| e "
          "uma cadeia de duplicacoes ate a largura W custa Omega(W).",
      "degree_is_not_the_obstruction": "Confirmado experimentalmente. psi_N (polinomio de divisao) "
          "tem grau ~2^510 e e avaliado exatamente em ~12.240 multiplicacoes de campo por recorrencia "
          "de sequencia de divisibilidade eliptica, decidindo pertinencia a n-torcao. Controle: "
          "escada bate com a recorrencia ingenua para n=1..400 e psi_N anula em todo ponto testado. "
          "A recorrencia existe porque o conjunto de raizes e um SUBGRUPO, fechado sob a lei de grupo. "
          "Um intervalo [L,L+W) nao tem esse fechamento; a construcao nao transfere.",
      "remaining_question": "Existe circuito aritmetico pequeno para X -> F_I(X)? Um circuito de "
          "tamanho s daria DLP em intervalo em O(s log W) operacoes de campo. Limite generico: "
          "Omega(sqrt(W)); melhor algoritmo conhecido para intervalo: canguru de Pollard, ~2 sqrt(W) "
          "operacoes de grupo. Ou seja, esse circuito nao e um passo em direcao a quebra do ECDLP, "
          "ele E a quebra. O limite generico nao o exclui formalmente porque F_I opera na "
          "representacao de corpo de x, fora do modelo de grupo generico; essa e exatamente a brecha "
          "que o index calculus por polinomios de somatorio ataca, sem ganho sobre sqrt(W) em corpos "
          "primos como secp256k1."},
  "next": "Nao investir mais nesta direcao sem um resultado novo de circuito. As duas sub-perguntas "
          "concretas foram respondidas em 08/09/2026: construir sem enumerar e possivel, conhecido e "
          "inutil; grau alto nao e o obstaculo, a falta de fechamento do intervalo sob a lei de grupo e. "
          "Nenhuma reivindicacao de novidade na literatura."},

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
  "test": {"scripts": ["creator_tx_forensics.py", "verify_creator_signatures.py"],
           "data": "data/creator_txs.json",
           "evidence": "analysis/creator-signature-verification.json"},
  "positive_control": {"required": True, "executed": False,
                       "note": "Controle valido: pegar transacoes de origem conhecida da mesma "
                               "epoca (Core 0.9/0.10, Electrum 1.9.x, blockchain.info, pybitcointools) "
                               "e verificar que os indicadores as separam."},
  "status": "open",
  "facts_extracted": [
      "2015: nVersion=1; 2017/2019/2023: nVersion=2. nSequence sempre 0xFFFFFFFF, locktime 0.",
      "2015: a UNICA assinatura e low-S -> sem informacao (50% por acaso). NAO tratar como fingerprint.",
      "2017: 97/97 low-S, compativel com normalizacao. A probabilidade 2^-97 pressupoe "
      "sinais independentes uniformes; nao identifica software nem prova determinismo do nonce.",
      "Todas as transacoes tem saidas em ordem crescente de valor; em 2015 sao 256 valores "
      "distintos, ou seja as saidas estao em ordem de indice do puzzle.",
      "Taxas absolutas de 400000, 2000000, 79000, 269000 e 1000000 sat; "
      "valores redondos nao bastam para atribuir construcao manual ou carteira grafica.",
      "2015: entrada 1Czoy8xtddvcGrEhUUCZDQ9QqdRfKh697F usa pubkey comprimida. "
      "1CENDvi6tmKGrR8RxqwURpX9WHbbKip1db e a entrada adicional 96 de 2017, nao comprimida.",
      "2023: entrada nativa P2WPKH; assinatura no witness, anteriormente omitida pelo extrator."],
  "source_review": [
      {"source": "https://raw.githubusercontent.com/spesmilo/electrum/1.9.8/lib/transaction.py",
       "observation": "serialize fixa versao 1, sequence final e locktime 0; preserva ordem de saidas fornecida. "
                      "sign usa sign_digest_deterministic com SHA256. Esses indicadores nao atribuem 2015 ao Electrum."},
      {"source": "https://raw.githubusercontent.com/bitcoin/bitcoin/v0.9.3/src/rpcrawtransaction.cpp",
       "observation": "createrawtransaction recebe as entradas e as saidas do chamador; "
                      "a ordem crescente pode ter sido fornecida pelo script que chamou o RPC."}],
  "next": "Executar controles de transacoes com software conhecido. A validacao ECDSA abaixo "
          "valida a extracao, nao substitui controles de atribuicao. Distinguir o signatario "
          "de transacoes posteriores do gerador de chaves de 2015."},

 {"id": "H2-mask-variants", "title": "Variantes de mascara e de indice",
  "statement": "O mapeamento chave-filha -> chave-de-puzzle nao e truncamento dos bits baixos "
               "com indice consecutivo a partir de 0 ou 1.",
  "space": "mascaras: low (bits baixos, modelo declarado), high (n bits altos), "
           "low_le (filho em little-endian). Mapas de indice: consecutive com offset e "
           "stride arbitrarios, reverse (#256 no comeco da carteira), rejection "
           "(sorteio sequencial descartando filhos sem o bit n-1 setado). "
           "Ramo de troco coberto pelo caminho BIP32 (ex.: m/1/i).",
  "test": {"scripts": ["master_seed_sweep.py"],
           "flags": ["--mask", "--index-map", "--index-base", "--index-stride"],
           "command": "./analysis/run_sweeps_h2.sh"},
  "positive_control": {"required": True, "executed": True,
                       "result": "PASSOU 20/20 em 2026-09-07: recuperacao da seed sintetica "
                                 "e rejeicao do conjunto adulterado para cada mascara "
                                 "(low/high/low_le) e cada mapa (offset 7, stride 2, reverse, "
                                 "rejection), em bip32 e hashseq.",
                       "evidence": "analysis/sweeps/selftest-h2.json"},
  "status": "open",
  "criticality": "ALTA: a cobertura de H3-seed-sweep so vale para a combinacao "
                 "(mask, index_map) registrada em cada linha. Confira essas colunas "
                 "antes de citar cobertura."},

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
  "space": "conta saatoshi_rising no BitcoinTalk; financiamento 2015: 1Czoy8xtddvcGrEhUUCZDQ9QqdRfKh697F; "
           "entrada adicional de 2017: 1CENDvi6tmKGrR8RxqwURpX9WHbbKip1db; "
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
                     "encoder": d.get("encoder"),
                     "mask": d.get("mask", "low"),
                     "index_map": d.get("index_map", "consecutive(base=%s,stride=1)"
                                        % d.get("index_base", 0)),
                     "range": d.get("range"), "candidates": d.get("candidates"),
                     "anchor_puzzle": d.get("anchor_puzzle"),
                     "anchor_bits": d.get("anchor_bits"),
                     "hits": d.get("hits"), "elapsed_s": d.get("elapsed_s")})
    return rows


def raw_generator_hypotheses():
    """Import measured raw-PRNG coverage without closing weak-seed families."""
    current_sha = hashlib.sha256(open(os.path.join(ROOT, 'data', 'puzzles.json'), 'rb').read()).hexdigest()
    entries = []
    jp = os.path.join(HERE, 'java-random-results.json')
    if os.path.exists(jp):
        report = json.load(open(jp))
        controls = report.get('self_tests', {}).get('controls', [])
        passed = len(controls) == 12 and all(
            c.get('original_state_recovered') and c.get('synthetic_71_prediction_correct') and
            c.get('tampered_validation_rejected') and c.get('validation_matches') == c.get('validation_total')
            for c in controls)
        results = report.get('real_results', [])
        current = report.get('input_sha256') == current_sha
        excluded = len(results) == 4 and all(r.get('anchor_survivors') == 0 for r in results)
        entries.append({
            'id': 'H5-java-raw', 'title': 'Saida direta de java.util.Random antes da mascara',
            'statement': 'As chaves sao bytes/inteiros brutos de um LCG Java de 48 bits, depois mascarados.',
            'space': 'Quatro layouts: bigint256, bigint_i, bigint_i_minus_1, int32_be; mascara low; ancora #70.',
            'test': {'scripts': ['java_random_recovery.py', 'JavaRandomVectors.java'],
                     'command': 'python3 -B analysis/java_random_recovery.py', 'evidence': 'analysis/java-random-results.json'},
            'positive_control': {'required': True, 'executed': passed,
                'result': '12 controles Java; 1920 chaves comparadas; estado recuperado e 81/81 validacoes por controle.' if passed else 'Controles incompletos ou falharam.'},
            'status': 'covered' if passed and current and excluded else 'open',
            'input_matches_current_dataset': current, 'coverage': results,
            'note': 'Uma palavra observada fixa 32 bits; todos os 65536 sufixos de estado sao examinados por layout. Zero sobreviventes exclui qualquer estado de 48 bits para a ancora, inclusive com reseeding entre chaves. Nao cobre SecureRandom, hashing ou uso apenas para gerar uma seed de carteira.'})
    vp = os.path.join(HERE, 'v8-mwc-results.json')
    mp = os.path.join(HERE, 'v8-native-masks-results.json')
    if os.path.exists(vp) and os.path.exists(mp):
        report, masks = json.load(open(vp)), json.load(open(mp))
        controls = masks.get('positive_controls', [])
        passed = (len(controls) == 9 and all(c.get('true_projected_state_recovered') for c in controls)
                  and masks.get('native_reference_words_checked') == 300
                  and len(report.get('controls', [])) == 4
                  and all(c.get('fixed_positive') == 'sat' and c.get('fixed_tampered') == 'unsat'
                          for c in report['controls']))
        current = all(r.get('input_sha256') == current_sha for r in (report, masks))
        conclusions = report.get('conclusions', [])
        excluded = (len(conclusions) == 4 and all(c.get('status') == 'incompatible' for c in conclusions)
                    and len(masks.get('results', [])) == 3
                    and all(c.get('survivors') == 0 for c in masks['results']))
        entries.append({
            'id': 'H6-v8-raw', 'title': 'Saida direta do MWC do V8 3.14.5',
            'statement': 'As chaves usam saidas consecutivas do gerador nativo V8 3.14.5, sem transformacao criptografica intermediaria.',
            'space': 'word32_be, word32_le, word16_be com mascara low; byte8 com mascaras low, low_le e high. Ancora #130; 128 ou 120 bits observados.',
            'test': {'scripts': ['v8_mwc_audit.py', 'v8_mwc_reference.c', 'v8_native_masks.py'],
                     'command': 'python3 -B analysis/v8_native_masks.py',
                     'evidence': ['analysis/v8-mwc-results.json', 'analysis/v8-native-masks-results.json']},
            'positive_control': {'required': True, 'executed': passed,
                'result': '300 palavras e conversoes double conferidas com C; nove controles recuperam o estado parcial verdadeiro; controles SMT positivos e adulterados.' if passed else 'Controles incompletos ou falharam.'},
            'status': 'covered' if passed and current and excluded else 'open',
            'input_matches_current_dataset': current,
            'coverage': {'low_mask_layouts': conclusions, 'byte_mask_variants': masks.get('results', [])},
            'note': 'O timeout do SMT para byte8 nao foi usado como negativo. A exclusao vem de enumeracao nativa exaustiva de uma condicao necessaria em a, relaxando b. Nao cobre outras versoes V8, chamadas extras dentro da chave, ARC4, hashes ou derivacao HD. Nao identifica o software do criador.'})
    return entries


def main():
    try:
        commit = subprocess.check_output(["git", "-C", ROOT, "rev-parse", "HEAD"],
                                         text=True).strip()
    except Exception:
        commit = None
    hyp = json.loads(json.dumps(STATIC))
    hyp.extend(raw_generator_hypotheses())
    cov = sweep_coverage()
    for h in hyp:
        if h['id'] == 'H1-forensics':
            evidence = os.path.join(HERE, 'creator-signature-verification.json')
            if os.path.exists(evidence):
                result = json.load(open(evidence))
                h['signature_validation'] = {
                    'input_matches_current_dataset': result['input_sha256'] == hashlib.sha256(
                        open(os.path.join(ROOT, 'data/creator_txs.json'), 'rb').read()).hexdigest(),
                    **{k: result[k] for k in ('controls', 'verified_signatures',
                                              'repeated_r_groups', 'previous_target_rows_matched',
                                              'limitations')}}
        if h['id'] == 'H0-nonce':
            evidence = os.path.join(HERE, 'funding-nonce-results.json')
            if os.path.exists(evidence):
                result = json.load(open(evidence))
                h['funding_extension'] = {
                    'evidence': 'analysis/funding-nonce-results.json',
                    'verification_matches_current_report': result['verification_sha256'] == hashlib.sha256(
                        open(os.path.join(HERE, 'creator-signature-verification.json'), 'rb').read()).hexdigest(),
                    **{k: result[k] for k in ('controls', 'bound_inclusive', 'funding_nonce_points_checked',
                                              'pairs_checked', 'point_sum_difference_checks',
                                              'small_nonce_matches', 'related_nonce_matches', 'limitations')}}
        if h["id"] == "H3-seed-sweep":
            evidence = os.path.join(HERE, 'phrase-sweep-results.json')
            if os.path.exists(evidence):
                r = json.load(open(evidence))
                h["phrase_branch"] = {
                    'evidence': 'analysis/phrase-sweep-results.json',
                    'note': 'Ramo de FRASES do H3, executado pela primeira vez em 08/09/2026. '
                            'master_seed_sweep.py so aceita faixas de inteiros, entao este ramo '
                            'do enunciado nunca tinha implementacao.',
                    'scripts': ['phrase_seed_sweep.py', 'run_phrase_sweeps.py'],
                    'command': 'python3 -B analysis/run_phrase_sweeps.py',
                    **{k: r[k] for k in ('phrase_sources', 'seed_modes', 'masks', 'families',
                                         'controls_all_passed', 'total_anchor_tests',
                                         'anchor_survivors_total', 'fully_confirmed',
                                         'seconds', 'limitations')}}
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
