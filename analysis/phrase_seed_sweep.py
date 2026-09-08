#!/usr/bin/env python3
"""H3, ramo de FRASES: seeds humanas. Nunca varrido ate agora.

master_seed_sweep.py so aceita faixas de INTEIROS (--range lo-hi), entao o
enunciado do H3 "seed = SHA256(frase) e BIP39 com passphrase escolhida" nunca
teve implementacao. Este script fornece esse ramo, reusando as familias de
derivacao e o modelo de mascara do sweep original.

    puzzle_n = 2^(n-1) | (child_{base + n - 1} mod 2^(n-1))

Ancora: o puzzle resolvido com mais bits (#130 -> 129 bits). Um acerto na ancora
tem falso positivo 2^-129, e os sobreviventes sao confirmados contra as 82
chaves conhecidas. Fontes de frase: dicionario do sistema com variantes de caixa,
gerador combinatorio tematico e arquivo do usuario.

Controle positivo obrigatorio (regra da secao 3 do BRIEFING): planta uma frase
conhecida, exige recuperacao, e exige rejeicao de um conjunto adulterado.

Sem acesso a rede e sem busca de chave por forca bruta.
"""
import argparse
import hashlib
import itertools
import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from master_seed_sweep import (MASKS, Bip32, ElectrumV1, HashChain, HashSeq,
                               IndexMap, load_solved, synthetic_keys)

HERE = Path(__file__).resolve().parent


# --------------------------------------------------------------------------
# frase -> bytes de seed
# --------------------------------------------------------------------------
def seed_sha256(phrase):
    return hashlib.sha256(phrase.encode('utf-8')).digest()


def seed_sha256d(phrase):
    return hashlib.sha256(hashlib.sha256(phrase.encode('utf-8')).digest()).digest()


def seed_raw(phrase):
    return phrase.encode('utf-8')


def seed_bip39(phrase):
    return hashlib.pbkdf2_hmac('sha512', phrase.encode('utf-8'),
                               b'mnemonic', 2048, dklen=64)


SEED_MODES = {'sha256': seed_sha256, 'sha256d': seed_sha256d,
              'raw': seed_raw, 'bip39': seed_bip39}


# --------------------------------------------------------------------------
# fontes de frase
# --------------------------------------------------------------------------
THEME_TOKENS = [
    'bitcoin', 'satoshi', 'saatoshi', 'saatoshi_rising', 'nakamoto', 'puzzle',
    'transaction', 'challenge', 'privatekey', 'private key', 'secret', 'seed',
    'brainwallet', 'deterministic', 'wallet', 'electrum', 'blockchain', 'btc',
    'genesis', 'hal', 'finney', 'cypherpunk', 'proof of work', '32BitEx',
    'the times', 'chancellor', 'brink of second bailout for banks',
]
THEME_SUFFIXES = ['', '2015', '2014', '1', '123', '!', '.', '256', '2015!', '0']
THEME_JOINS = ['', ' ', '_', '-']


def phrases_dict(limit=None):
    path = Path('/usr/share/dict/words')
    if not path.exists():
        return
    seen = 0
    with path.open() as handle:
        for line in handle:
            word = line.strip()
            if not word:
                continue
            for variant in (word, word.lower(), word.capitalize(), word.upper()):
                yield variant
            seen += 1
            if limit and seen >= limit:
                return


def phrases_theme():
    for a, b in itertools.product(THEME_TOKENS, repeat=2):
        for join in THEME_JOINS:
            for suffix in THEME_SUFFIXES:
                yield a + join + b + suffix
    for token in THEME_TOKENS:
        for suffix in THEME_SUFFIXES:
            yield token + suffix
            yield (token + suffix).upper()
            yield (token + suffix).capitalize()


def phrases_file(path):
    with open(path, encoding='utf-8', errors='replace') as handle:
        for line in handle:
            line = line.rstrip('\n')
            if line:
                yield line


def phrase_stream(source, wordlist=None, limit=None):
    if source == 'dict':
        return phrases_dict(limit)
    if source == 'theme':
        return phrases_theme()
    if source == 'file':
        return phrases_file(wordlist)
    if source == 'both':
        return itertools.chain(phrases_theme(), phrases_dict(limit))
    raise ValueError(source)


# --------------------------------------------------------------------------
# nucleo
# --------------------------------------------------------------------------
_STATE = {}


def _init(state):
    _STATE.update(state)


def _scan(chunk):
    fam, imap = _STATE['family'], _STATE['imap']
    maskfn, seedfn = MASKS[_STATE['mask']], SEED_MODES[_STATE['seed_mode']]
    anchor, anchor_key = _STATE['anchor'], _STATE['anchor_key']
    index = imap.index_for(anchor)
    hits = []
    for phrase in chunk:
        try:
            ctx = fam.prepare(seedfn(phrase))
        except Exception:
            continue
        if ctx is None:
            continue
        if maskfn(anchor, fam.child(ctx, index)) == anchor_key:
            hits.append(phrase)
    return len(chunk), hits


def chunked(iterable, size):
    block = []
    for item in iterable:
        block.append(item)
        if len(block) >= size:
            yield block
            block = []
    if block:
        yield block


def run(family, seed_mode, imap, mask, solved, stream, jobs, chunk_size,
        progress_every=2_000_000):
    anchor = max(solved)
    state = {'family': family, 'imap': imap, 'mask': mask, 'seed_mode': seed_mode,
             'anchor': anchor, 'anchor_key': solved[anchor]}
    tested, survivors, started = 0, [], time.time()
    blocks = chunked(stream, chunk_size)
    if jobs == 1:
        _init(state)
        results = (_scan(b) for b in blocks)
        for count, hits in results:
            tested += count
            survivors.extend(hits)
    else:
        with mp.Pool(jobs, initializer=_init, initargs=(state,)) as pool:
            for count, hits in pool.imap_unordered(_scan, blocks, chunksize=1):
                tested += count
                survivors.extend(hits)
                if progress_every and tested % progress_every < chunk_size:
                    rate = tested/max(time.time()-started, 1e-9)
                    print(f'  ... {tested:,} frases, {rate:,.0f}/s', file=sys.stderr)
    confirmed = []
    for phrase in survivors:
        seed = SEED_MODES[seed_mode](phrase)
        keys = synthetic_keys(family, seed, sorted(solved), imap, mask)
        if keys == solved:
            confirmed.append(phrase)
    return {'family': family.name, 'seed_mode': seed_mode, 'index_map': imap.name,
            'mask': mask, 'anchor_puzzle': anchor, 'anchor_bits': anchor-1,
            'phrases_tested': tested, 'anchor_survivors': survivors,
            'fully_confirmed': confirmed,
            'seconds': round(time.time()-started, 2),
            'rate_per_second': round(tested/max(time.time()-started, 1e-9))}


def self_test(jobs):
    """Planta uma frase conhecida; exige recuperacao e rejeicao de dado adulterado."""
    puzzles = list(range(1, 141))
    rows = []
    for famname, family in (('hashseq', HashSeq('sha256', 'be4')),
                            ('bip32', Bip32('m/0/i')),
                            ('hashchain', HashChain('sha256'))):
        for seed_mode in ('sha256', 'bip39'):
            secret = f'controle-{famname}-{seed_mode}-2015'
            imap = IndexMap('consecutive', 0)
            planted = synthetic_keys(family, SEED_MODES[seed_mode](secret),
                                     puzzles, imap, 'low')
            decoys = [f'decoy-{i}' for i in range(400)]
            stream = decoys[:200] + [secret] + decoys[200:]
            found = run(family, seed_mode, imap, 'low', planted, iter(stream), 1, 64)
            tampered = dict(planted)
            tampered[130] ^= 1
            miss = run(family, seed_mode, imap, 'low', tampered,
                       iter(decoys + [secret]), 1, 64)
            rows.append({'family': famname, 'seed_mode': seed_mode,
                         'phrase_recovered': found['fully_confirmed'] == [secret],
                         'tampered_rejected': miss['fully_confirmed'] == [],
                         'phrases_tested': found['phrases_tested']})
    return rows


def main():
    ap = argparse.ArgumentParser(description='H3 ramo de frases: seeds humanas.')
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--source', default='both', choices=('dict', 'theme', 'file', 'both'))
    ap.add_argument('--wordlist')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--seed-mode', default='sha256', choices=sorted(SEED_MODES))
    ap.add_argument('--family', default='hashseq',
                    choices=('bip32', 'hashseq', 'hashchain', 'electrum1'))
    ap.add_argument('--path', default='m/0/i')
    ap.add_argument('--hash', default='sha256')
    ap.add_argument('--index-enc', default='be4')
    ap.add_argument('--branch', type=int, default=0)
    ap.add_argument('--index-base', type=int, default=0)
    ap.add_argument('--index-stride', type=int, default=1)
    ap.add_argument('--index-map', default='consecutive', choices=('consecutive', 'reverse'))
    ap.add_argument('--mask', default='low', choices=sorted(MASKS))
    ap.add_argument('--jobs', type=int, default=max(1, (os.cpu_count() or 2)-1))
    ap.add_argument('--chunk', type=int, default=20000)
    ap.add_argument('--output')
    args = ap.parse_args()

    if args.self_test:
        rows = self_test(args.jobs)
        report = {'controls': rows,
                  'all_passed': all(r['phrase_recovered'] and r['tampered_rejected']
                                    for r in rows)}
        print(json.dumps(report, indent=2))
        return

    family = {'bip32': lambda: Bip32(args.path),
              'hashseq': lambda: HashSeq(args.hash, args.index_enc),
              'hashchain': lambda: HashChain(args.hash),
              'electrum1': lambda: ElectrumV1(args.branch)}[args.family]()
    imap = IndexMap(args.index_map, args.index_base, args.index_stride)
    solved = load_solved()
    stream = phrase_stream(args.source, args.wordlist, args.limit)
    result = run(family, args.seed_mode, imap, args.mask, solved, stream,
                 args.jobs, args.chunk)
    print(json.dumps(result, indent=2))
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
