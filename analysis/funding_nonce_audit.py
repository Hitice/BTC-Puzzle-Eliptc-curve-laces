#!/usr/bin/env python3
"""Extend the bounded nonce audit to five non-puzzle funding inputs, offline.

R = s^-1(zG+rQ) recovers a nonce POINT, not its discrete logarithm.
Only test |k| <= 65536 and |k_i +/- k_j| <= 65536 modulo N.
Pairs must contain at least one of the five additional funding inputs.
Different-key nonce relations alone need not permit private-key recovery.
"""
import hashlib
import json
from itertools import combinations
from pathlib import Path

from electrum_old_mpk import add, mul, G, N, P
from verify_creator_signatures import decode_public

BOUND = 65536
PUZZLE_INPUTS = {
    '5d45587cfd1d5b0fb826805541da7d94c61fe432259e68ee26f4a04544384164': range(96),
    '17e4e323cfbc68d7f0071cad09364e8193eedf8fefbcbd8a21b4b65717a4b3d3': range(20),
}


def negate(point):
    return None if point is None else (point[0], -point[1] % P)


def nonce_point(row):
    r, s, z = (int(row[k], 16) for k in ('r', 's', 'z'))
    q = decode_public(bytes.fromhex(row['pubkey']))
    inverse = pow(s, -1, N)
    result = add(mul(z*inverse), mul(r*inverse, q))
    assert result is not None and result[0] % N == r
    return result


def small_scalars():
    point, table = None, {None: 0}
    for k in range(1, BOUND+1):
        point = add(point, G)
        table[point] = k
        table[negate(point)] = -k
    return table


def self_test(table):
    # Independent synthetic signing equation, including low-S sign reversal.
    secret, z = 123456789, 987654321
    pubkey = mul(secret)
    public = bytes([2+(pubkey[1] & 1)])+pubkey[0].to_bytes(32, 'big')
    for k in (1, BOUND, BOUND+1, 1 << 20, (1 << 20)+31):
        point = mul(k)
        r = point[0] % N
        s = (z+r*secret)*pow(k, -1, N) % N
        for s_actual, k_actual in ((s, k), (N-s, -k)):
            row = {'r': f'{r:x}', 's': f'{s_actual:x}', 'z': f'{z:x}', 'pubkey': public.hex()}
            recovered = nonce_point(row)
            assert recovered == mul(k_actual)
            assert table.get(recovered) == (k_actual if abs(k_actual) <= BOUND else None)
    a, b = mul(1 << 20), mul((1 << 20)+31)
    assert table[add(b, negate(a))] == 31
    assert table[add(a, negate(b))] == -31
    assert table[add(a, negate(a))] == 0
    assert table[add(negate(b), a)] == -31
    return {'synthetic_signature_cases': 10, 'passed': True,
            'boundary_inclusive': True, 'above_boundary_rejected': True,
            'positive_negative_and_zero_relations': True}


def main():
    here = Path(__file__).resolve().parent
    source = (here/'creator-signature-verification.json').read_bytes()
    verified = json.loads(source)
    assert verified['input_sha256'] == hashlib.sha256(
        (here.parent/'data/creator_txs.json').read_bytes()).hexdigest()
    table = small_scalars()
    controls = self_test(table)
    rows = []
    for tx in verified['transactions']:
        for row in tx['signatures']:
            assert row['valid']
            rows.append({'txid': tx['txid'], 'input': row['index'],
                         'funding': row['index'] not in PUZZLE_INPUTS.get(tx['txid'], ()),
                         'point': nonce_point(row)})
    assert len(rows) == 121 and sum(r['funding'] for r in rows) == 5
    small, related, pairs = [], [], 0
    ref = lambda row: {'txid': row['txid'], 'input': row['input']}
    for row in rows:
        if row['funding'] and row['point'] in table:
            small.append({**ref(row), 'signed_nonce': table[row['point']]})
    for a, b in combinations(rows, 2):
        if not (a['funding'] or b['funding']):
            continue
        pairs += 1
        for operation, point in (('sum', add(a['point'], b['point'])),
                                 ('difference', add(a['point'], negate(b['point'])))):
            if point in table:
                related.append({'a': ref(a), 'b': ref(b), 'operation': operation,
                                'signed_delta': table[point]})
    assert pairs == 590
    report = {'verification_sha256': hashlib.sha256(source).hexdigest(),
              'bound_inclusive': BOUND, 'controls': controls,
              'funding_inputs': [ref(r) for r in rows if r['funding']],
              'funding_nonce_points_checked': 5, 'pairs_checked': pairs,
              'point_sum_difference_checks': 2*pairs,
              'small_nonce_matches': small, 'related_nonce_matches': related,
              'limitations': ['Only the stated bounded modular nonce models are covered.',
                              'Funding inputs do not establish creator identity or key-generator software.',
                              'A relation between nonces under distinct keys need not recover either key.']}
    (here/'funding-nonce-results.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'funding_inputs'}, indent=2))


if __name__ == '__main__':
    main()
