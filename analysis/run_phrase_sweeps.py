#!/usr/bin/env python3
"""Fila do H3 ramo de frases.

A derivacao seed <- frase e independente da familia e da mascara, e o filho na
ancora e independente da mascara. Entao cada frase paga UMA seed (o PBKDF2 do
BIP39 e o custo dominante) e UM filho por familia, e as tres mascaras sao apenas
comparacoes. Isso evita recalcular o mesmo PBKDF2 30 vezes.
"""
import json, os, sys, time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import multiprocessing as mp
from master_seed_sweep import (MASKS, Bip32, HashChain, HashSeq, IndexMap,
                               load_solved, synthetic_keys)
from phrase_seed_sweep import SEED_MODES, chunked, phrase_stream, self_test

FAMILIES = [('hashseq:sha256/be4', HashSeq, ('sha256', 'be4')),
            ('hashseq:sha256/le4', HashSeq, ('sha256', 'le4')),
            ('hashseq:sha256/str', HashSeq, ('sha256', 'str')),
            ('hashseq:sha256d/be4', HashSeq, ('sha256d', 'be4')),
            ('bip32:m/0/i', Bip32, ('m/0/i',)),
            ('bip32:m/0h/i', Bip32, ('m/0h/i',)),
            ('bip32:m/i', Bip32, ('m/i',)),
            ('bip32:m/ih', Bip32, ('m/ih',)),
            ('bip32:m/44h/0h/0h/0/i', Bip32, ('m/44h/0h/0h/0/i',)),
            ('hashchain:sha256', HashChain, ('sha256',))]
MODES = ['sha256', 'sha256d', 'raw', 'bip39']
MASK_NAMES = ['low', 'high', 'low_le']
_S = {}


def _init(state):
    _S.update(state)
    _S['families'] = [(name, cls(*args)) for name, cls, args in FAMILIES]


def _scan(chunk):
    seedfn = SEED_MODES[_S['mode']]
    anchor, anchor_key, index = _S['anchor'], _S['anchor_key'], _S['index']
    hits = {}
    for phrase in chunk:
        try:
            seed = seedfn(phrase)
        except Exception:
            continue
        for name, fam in _S['families']:
            try:
                ctx = fam.prepare(seed)
                if ctx is None:
                    continue
                child = fam.child(ctx, index)
            except Exception:
                continue
            for mask in MASK_NAMES:
                if MASKS[mask](anchor, child) == anchor_key:
                    hits.setdefault(f'{name}|{mask}', []).append(phrase)
    return len(chunk), hits


def main():
    jobs = max(1, (os.cpu_count() or 2)-1)
    solved = load_solved()
    anchor = max(solved)
    imap = IndexMap('consecutive', 0)
    log = open(Path(__file__).with_name('phrase-sweep.log'), 'w')

    def say(msg):
        print(msg, flush=True)
        log.write(msg+'\n')
        log.flush()

    say('controles positivos...')
    controls = self_test(jobs)
    ok = all(c['phrase_recovered'] and c['tampered_rejected'] for c in controls)
    say(f'controles: {len(controls)} combinacoes, todos passaram = {ok}')
    if not ok:
        raise SystemExit('controles falharam; varredura abortada')

    rows, started, survivors_all = [], time.time(), {}
    for mode in MODES:
        t0, tested, hits = time.time(), 0, {}
        state = {'mode': mode, 'anchor': anchor, 'anchor_key': solved[anchor],
                 'index': imap.index_for(anchor)}
        with mp.Pool(jobs, initializer=_init, initargs=(state,)) as pool:
            blocks = chunked(phrase_stream('both'), 5000)
            for count, found in pool.imap_unordered(_scan, blocks, chunksize=1):
                tested += count
                for key, phrases in found.items():
                    hits.setdefault(key, []).extend(phrases)
        elapsed = time.time()-t0
        combos = len(FAMILIES)*len(MASK_NAMES)
        say(f'{mode:8s} {tested:>9,} frases x {combos} combinacoes = '
            f'{tested*combos:>12,} testes de ancora  '
            f'{tested/max(elapsed,1e-9):>9,.0f} frases/s  {elapsed:6.1f}s  '
            f'sobreviventes={sum(len(v) for v in hits.values())}')
        rows.append({'seed_mode': mode, 'phrases_tested': tested,
                     'combinations': combos, 'anchor_tests': tested*combos,
                     'seconds': round(elapsed, 1),
                     'anchor_survivors': hits})
        survivors_all.update({f'{mode}|{k}': v for k, v in hits.items()})

    confirmed = []
    for key, phrases in survivors_all.items():
        mode, famname, mask = key.split('|')
        cls, args = next((c, a) for n, c, a in FAMILIES if n == famname)[0:2]
        fam = cls(*args)
        for phrase in phrases:
            keys = synthetic_keys(fam, SEED_MODES[mode](phrase), sorted(solved),
                                  imap, mask)
            if keys == solved:
                confirmed.append({'phrase': phrase, 'seed_mode': mode,
                                  'family': famname, 'mask': mask})

    report = {
        'hypothesis': 'H3 ramo de frases (seeds humanas) - primeira execucao',
        'model': 'puzzle_n = 2^(n-1) | (child_{base+n-1} mod 2^(n-1))',
        'anchor': f'puzzle #{anchor}, {anchor-1} bits, falso positivo 2^-{anchor-1}',
        'phrase_sources': 'dicionario do sistema (235.976 palavras x 4 variantes de caixa) '
                          '+ gerador combinatorio tematico',
        'seed_modes': MODES, 'masks': MASK_NAMES,
        'families': [n for n, _, _ in FAMILIES],
        'positive_controls': controls, 'controls_all_passed': ok,
        'total_anchor_tests': sum(r['anchor_tests'] for r in rows),
        'anchor_survivors_total': sum(len(v) for r in rows
                                      for v in r['anchor_survivors'].values()),
        'fully_confirmed': confirmed,
        'per_seed_mode': rows,
        'seconds': round(time.time()-started, 1),
        'limitations': [
            'Cobre SO as frases enumeradas: dicionario ingles com variantes de caixa e '
            'combinacoes tematicas. Nao cobre frases arbitrarias, outros idiomas, nem '
            'BIP39 com mnemonico desconhecido e passphrase escolhida.',
            'Indice consecutive(base=0). Outros index-base/stride nao varridos aqui.',
            'Familia electrum1 excluida: 100k SHA256 por candidato inviabiliza o espaco.',
            'Ausencia de acerto exclui o espaco enumerado, NAO a hipotese H3.']}
    out = Path(__file__).with_name('phrase-sweep-results.json')
    out.write_text(json.dumps(report, indent=2)+'\n')
    say(f"TOTAL {report['total_anchor_tests']:,} testes de ancora, "
        f"{report['anchor_survivors_total']} sobreviventes, "
        f"{len(confirmed)} confirmadas, {report['seconds']}s")
    say(str(out))
    log.close()


if __name__ == '__main__':
    main()
