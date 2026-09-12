#!/usr/bin/env python3
"""H3 ramo de TIMESTAMP EM MILISSEGUNDOS. Nunca coberto.

A cobertura de inteiros do repo vai ate 2^32 e cobre timestamps em SEGUNDOS
(1356998400..1421345235). Um timestamp de 2015 em MILISSEGUNDOS e ~1.42e12,
precisa de 41 bits: esta inteiramente fora do espaco varrido.

Motivacao especifica, do proprio BRIEFING secao 8: os testes H5/H6 cobrem a
saida BRUTA de java.util.Random e do MWC do V8 como CHAVE, e o briefing anota
que eles "nao testam esses PRNGs como fontes de seed de uma carteira que depois
usa hashes/HD". Date.now() do V8 e exatamente milissegundos. Este script fecha
esse buraco pelo lado da SEED.

Ancora: puzzle #130, 129 bits, falso positivo 2^-129. Como no ramo de frases,
cada candidato paga UMA codificacao por encoder e UM filho por familia; as tres
mascaras sao apenas comparacoes.

Sem acesso a rede e sem busca de chave por forca bruta.
"""
import argparse, json, os, sys, time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import multiprocessing as mp
from master_seed_sweep import (ENCODERS, MASKS, Bip32, HashChain, HashSeq,
                               IndexMap, load_solved, synthetic_keys)

TX_2015_BLOCK_TIME = 1421345234          # 2015-01-15T18:07:14Z, tx de financiamento
MASK_NAMES = ['low', 'high', 'low_le']
FAMILY_SPECS = {
    'hashseq:sha256/be4': (HashSeq, ('sha256', 'be4')),
    'hashseq:sha256/str': (HashSeq, ('sha256', 'str')),
    'hashseq:sha256d/be4': (HashSeq, ('sha256d', 'be4')),
    'bip32:m/0h/i': (Bip32, ('m/0h/i',)),
    'bip32:m/0/i': (Bip32, ('m/0/i',)),
    'hashchain:sha256': (HashChain, ('sha256',)),
}
_S = {}


def _init(state):
    _S.update(state)
    _S['fams'] = [(n, FAMILY_SPECS[n][0](*FAMILY_SPECS[n][1])) for n in state['families']]


def _scan(bounds):
    lo, hi = bounds
    encs = [(n, ENCODERS[n]) for n in _S['encoders']]
    anchor, key, index = _S['anchor'], _S['anchor_key'], _S['index']
    hits = {}
    for t in range(lo, hi):
        for encname, enc in encs:
            try:
                seed = enc(t)
            except Exception:
                continue
            for famname, fam in _S['fams']:
                try:
                    ctx = fam.prepare(seed)
                    if ctx is None:
                        continue
                    child = fam.child(ctx, index)
                except Exception:
                    continue
                for mask in MASK_NAMES:
                    if MASKS[mask](anchor, child) == key:
                        hits.setdefault(f'{encname}|{famname}|{mask}', []).append(t)
    return hi-lo, hits


def sweep(lo, hi, encoders, families, solved, jobs, chunk):
    anchor = max(solved)
    imap = IndexMap('consecutive', 0)
    state = {'encoders': encoders, 'families': families, 'anchor': anchor,
             'anchor_key': solved[anchor], 'index': imap.index_for(anchor)}
    bounds = [(a, min(a+chunk, hi)) for a in range(lo, hi, chunk)]
    tested, hits, t0 = 0, {}, time.time()
    if jobs == 1:
        _init(state)
        for b in bounds:
            c, f = _scan(b)
            tested += c
            for k, v in f.items():
                hits.setdefault(k, []).extend(v)
    else:
        with mp.Pool(jobs, initializer=_init, initargs=(state,)) as pool:
            for c, f in pool.imap_unordered(_scan, bounds, chunksize=1):
                tested += c
                for k, v in f.items():
                    hits.setdefault(k, []).extend(v)
    elapsed = time.time()-t0
    return {'range': [lo, hi], 'candidates': tested,
            'derivations': tested*len(encoders)*len(families),
            'anchor_tests': tested*len(encoders)*len(families)*len(MASK_NAMES),
            'seconds': round(elapsed, 1),
            'candidates_per_second': round(tested/max(elapsed, 1e-9)),
            'anchor_survivors': hits}


def positive_control(jobs):
    """Planta um timestamp conhecido; exige recuperacao e rejeicao de adulterado."""
    solved_idx = list(range(1, 141))
    rows = []
    for encname in ('ascii', 'raw8be', 'sha256'):
        for famname in ('hashseq:sha256/be4', 'bip32:m/0h/i'):
            cls, args = FAMILY_SPECS[famname]
            fam = cls(*args)
            secret = TX_2015_BLOCK_TIME*1000 - 12345
            seed = ENCODERS[encname](secret)
            planted = synthetic_keys(fam, seed, solved_idx, IndexMap('consecutive', 0), 'low')
            found = sweep(secret-500, secret+500, [encname], [famname], planted, 1, 200)
            # a ancora e max(planted); adulterar QUALQUER outra chave nao testa o filtro
            tampered = dict(planted); tampered[max(planted)] ^= 1
            miss = sweep(secret-500, secret+500, [encname], [famname], tampered, 1, 200)
            # e um candidato vizinho nao pode passar na ancora verdadeira
            off = sweep(secret+1, secret+500, [encname], [famname], planted, 1, 200)
            key = f'{encname}|{famname}|low'
            rows.append({'encoder': encname, 'family': famname,
                         'anchor_puzzle': max(planted),
                         'timestamp_recovered': found['anchor_survivors'].get(key) == [secret],
                         'tampered_anchor_rejected': miss['anchor_survivors'] == {},
                         'neighbours_rejected': off['anchor_survivors'] == {}})
    return rows


def main():
    ap = argparse.ArgumentParser(description='H3: seed = timestamp em milissegundos.')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--days-before', type=float, default=1.0,
                    help='janela em dias antes da tx de 2015')
    ap.add_argument('--encoders', default='ascii,raw8be,sha256')
    ap.add_argument('--families', default='hashseq:sha256/be4,hashseq:sha256/str,bip32:m/0h/i')
    ap.add_argument('--jobs', type=int, default=max(1, (os.cpu_count() or 2)-1))
    ap.add_argument('--chunk', type=int, default=200000)
    ap.add_argument('--output')
    args = ap.parse_args()

    if args.self_test:
        rows = positive_control(args.jobs)
        ok = all(r['timestamp_recovered'] and r['tampered_anchor_rejected']
                 and r['neighbours_rejected'] for r in rows)
        print(json.dumps({'controls': rows, 'all_passed': ok}, indent=2))
        return

    solved = load_solved()
    encoders = args.encoders.split(',')
    families = args.families.split(',')
    hi = TX_2015_BLOCK_TIME*1000
    lo = hi - int(args.days_before*86400*1000)
    result = sweep(lo, hi, encoders, families, solved, args.jobs, args.chunk)
    confirmed = []
    for key, ts in result['anchor_survivors'].items():
        encname, famname, mask = key.split('|')
        cls, fargs = FAMILY_SPECS[famname]
        for t in ts:
            keys = synthetic_keys(cls(*fargs), ENCODERS[encname](t), sorted(solved),
                                  IndexMap('consecutive', 0), mask)
            if keys == solved:
                confirmed.append({'timestamp_ms': t, 'encoder': encname,
                                  'family': famname, 'mask': mask})
    report = {'hypothesis': 'H3 ramo timestamp em milissegundos',
              'anchor_tx_block_time': TX_2015_BLOCK_TIME,
              'window_days_before_tx': args.days_before,
              'encoders': encoders, 'families': families, 'masks': MASK_NAMES,
              **result, 'fully_confirmed': confirmed,
              'limitations': [
                  'Cobre so a janela e as combinacoes declaradas acima.',
                  'Indice consecutive(base=0).',
                  'Ausencia de acerto exclui o espaco enumerado, NAO a hipotese.']}
    print(json.dumps({k: report[k] for k in (
        'range', 'candidates', 'derivations', 'anchor_tests', 'seconds',
        'candidates_per_second', 'fully_confirmed')}, indent=2))
    print('sobreviventes:', sum(len(v) for v in result['anchor_survivors'].values()))
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
