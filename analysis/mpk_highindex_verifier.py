#!/usr/bin/env python3
"""Exact MPK test built from the 96 EXPOSED pubkeys of #161-#256.

electrum_old_mpk.compatible() consumes SOLVED PRIVATE keys (n <= 160) and ends
with an unmet condition, m*G == MPK. This supplies that condition from public
data only, and needs no solved key at all.

Model (repo standard):  puzzle_n = 2^(n-1) | (child_{base+n-1} mod 2^(n-1))
Additive wallet:        child_i   = (m + h_i) mod N,  ChildPub_i = MPK + h_i*G
                        h_i computable from the PUBLIC mpk (Electrum v1 offset)

Writing child_n = (p_n - 2^(n-1)) + k_n * 2^(n-1) gives the exact identity

        MPK + h_n*G - T_n  ==  k_n * B_n ,
        T_n = P_n - 2^(n-1)*G ,  B_n = 2^(n-1)*G ,  0 <= k_n < ceil(N/2^(n-1))

The bound on k_n collapses with n: TWO candidates at n=256, four at n=255.
So #256 alone is a complete accept/reject test for a candidate (mpk, branch,
shift) at a false-positive rate of 2/N ~ 2^-255, costing one k*G plus two point
comparisons. This is a VERIFIER, not a solver: it does not help find an MPK.

No puzzle key search, no network access.
"""
import json
from pathlib import Path

from electrum_old_mpk import N, P, offset, parse_mpk
from secp_fast import add_affine, mul_g

ROOT = Path(__file__).resolve().parent.parent


def negate(point):
    return None if point is None else (point[0], (-point[1]) % P)


def decompress(hex_pubkey):
    raw = bytes.fromhex(hex_pubkey)
    if raw[0] == 4:
        return int.from_bytes(raw[1:33], 'big'), int.from_bytes(raw[33:65], 'big')
    x = int.from_bytes(raw[1:], 'big')
    y = pow((x*x*x + 7) % P, (P+1)//4, P)
    if y % 2 != raw[0] % 2:
        y = (-y) % P
    if (y*y - x*x*x - 7) % P:
        raise ValueError('pubkey not on secp256k1')
    return x, y


def load_high_pubkeys():
    data = json.loads((ROOT/'data'/'puzzles_161_256.json').read_text())
    rows = data if isinstance(data, list) else data.get('puzzles', list(data.values())[-1])
    return {r['puzzle']: decompress(r['pubkey']) for r in rows if r.get('pubkey')}


def anchors(pubkeys, indices):
    """Precompute (T_n, B_n, bound_n) per index, cheapest bound first."""
    out = []
    for n in sorted(indices, key=lambda n: -n):
        base = mul_g(1 << (n-1))
        out.append({'n': n, 'T': add_affine(pubkeys[n], negate(base)),
                    'B': base, 'bound': -(-N // (1 << (n-1)))})
    return out


def verify(mpk_bytes, branch, shift, table, budget=4096):
    """True if every anchor admits a valid k_n. Rejects on the first failure."""
    mpk_point = (int.from_bytes(mpk_bytes[:32], 'big'),
                 int.from_bytes(mpk_bytes[32:], 'big'))
    for anchor in table:
        if anchor['bound'] > budget:
            continue
        h = offset(mpk_bytes, anchor['n']+shift, branch)
        target = add_affine(add_affine(mpk_point, mul_g(h)), negate(anchor['T']))
        accumulator, hit = None, target is None
        for _ in range(anchor['bound']-1):
            accumulator = add_affine(accumulator, anchor['B'])
            if accumulator == target:
                hit = True
                break
        if not hit:
            return False
    return True


def positive_control(indices, trials=3):
    """Synthetic Electrum v1 wallet -> masked puzzles -> the verifier must accept."""
    import hashlib
    rows = []
    for t in range(trials):
        m = int.from_bytes(hashlib.sha256(f'mpk-control:{t}'.encode()).digest(), 'big') % N
        mpk_point = mul_g(m)
        mpk_bytes = b''.join(v.to_bytes(32, 'big') for v in mpk_point)
        branch, shift = 0, 7
        pubkeys = {}
        for n in indices:
            child = (m + offset(mpk_bytes, n+shift, branch)) % N
            puzzle = (1 << (n-1)) | (child % (1 << (n-1)))
            pubkeys[n] = mul_g(puzzle)
        table = anchors(pubkeys, indices)
        wrong = bytearray(mpk_bytes)
        wrong[31] ^= 1                       # perturb the MPK, keep it 64 bytes
        rows.append({'trial': t,
                     'true_mpk_accepted': verify(mpk_bytes, branch, shift, table),
                     'wrong_shift_rejected': not verify(mpk_bytes, branch, shift+1, table),
                     'wrong_branch_rejected': not verify(mpk_bytes, 1, shift, table),
                     'perturbed_mpk_rejected': not verify(bytes(wrong), branch, shift, table)})
    return rows


def candidate_mpks():
    """Every distinct pubkey the creator has exposed, as MPK candidates."""
    out, seen = [], set()
    for name in ('creator_txs.json', 'puzzles_161_256.json', 'satoshi_early_pubkeys.json'):
        path = ROOT/'data'/name
        if not path.exists():
            continue
        text = path.read_text()
        for token in set(__import__('re').findall(r'"(0[23][0-9a-f]{64}|04[0-9a-f]{128})"', text)):
            try:
                point = decompress(token)
            except Exception:
                continue
            raw = b''.join(v.to_bytes(32, 'big') for v in point)
            if raw not in seen:
                seen.add(raw)
                out.append({'source': name, 'pubkey': token, 'mpk_bytes': raw})
    return out


def main():
    indices = [n for n in (256, 255, 254, 253, 252, 251, 250, 249, 248)]
    pubkeys = load_high_pubkeys()
    missing = [n for n in indices if n not in pubkeys]
    if missing:
        raise SystemExit(f'missing pubkeys for {missing}')
    controls = positive_control(indices)
    table = anchors(pubkeys, indices)

    shifts = range(-64, 65)
    candidates = candidate_mpks()
    hits, tested = [], 0
    for candidate in candidates:
        for branch in (0, 1):
            for shift in shifts:
                tested += 1
                if verify(candidate['mpk_bytes'], branch, shift, table):
                    hits.append({'pubkey': candidate['pubkey'], 'source': candidate['source'],
                                 'branch': branch, 'shift': shift})
    report = {
        'formulation': 'MPK + h_n*G - (P_n - 2^(n-1)G) == k_n * 2^(n-1)G, '
                       '0 <= k_n < ceil(N/2^(n-1))',
        'why_it_is_exact': 'k_n has only 2 admissible values at n=256 and 4 at n=255, so a '
                           'single anchor is a complete accept/reject test; false positive 2/N.',
        'anchors': [{'n': a['n'], 'k_candidates': a['bound']} for a in table],
        'positive_controls': controls,
        'controls_all_passed': all(all(v for k, v in r.items() if k != 'trial') for r in controls),
        'real_run': {'candidate_pubkeys': len(candidates),
                     'branches': 2, 'shift_range': [min(shifts), max(shifts)],
                     'combinations_tested': tested, 'matches': hits},
        'interpretation': 'A match would yield the master public key and, with '
                          'electrum_old_mpk.compatible(), the master private key progression. '
                          'No match only excludes the tested candidates: this is a verifier, '
                          'it does not search the MPK space.',
        'limitations': [
            'Assumes the repo mask model and an ADDITIVE wallet whose child offset is '
            'computable from public data (Electrum v1 / non-hardened BIP32 with known '
            'chaincode). Hardened derivation makes h_n unknowable and voids the test.',
            'Only the Electrum v1 offset function is implemented here.',
            'Index shift swept over a finite window; branch limited to 0 and 1.',
            'No literature novelty claimed and no puzzle key recovered.']}
    out = Path(__file__).with_name('mpk-highindex-verifier-results.json')
    out.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: report[k] for k in
                      ('anchors', 'positive_controls', 'controls_all_passed', 'real_run')}, indent=2))
    print(out)


if __name__ == '__main__':
    main()
