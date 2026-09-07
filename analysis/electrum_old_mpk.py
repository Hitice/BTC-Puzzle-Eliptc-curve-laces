#!/usr/bin/env python3
"""Offline compatibility filter for Electrum OldAccount and masked puzzle keys.

A supplied MPK determines child offsets, not the master private key. Surviving
integer progressions are necessary arithmetic conditions, NOT recovered keys:
the missing condition is m*G == MPK. No seed enumeration or network access.
"""
import argparse
import hashlib
import json
from pathlib import Path

N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
G = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
     0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)
OFFICIAL_SEED = 'acb740e454c3134901d7c8f16497cc1c'
OFFICIAL_MPK = ('e9d4b7866dd1e91c862aebf62a49548c7dbf7bcc6e4b7b8c9da820c7737968df'
                '9c09d5a3e271dc814a29981f81b3faaf2737b551ef5dcc6189cf0f8252c442b3')


def hash256(data):
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def add(a, b):
    if a is None:
        return b
    if b is None:
        return a
    x, y = a
    X, Y = b
    if x == X and (y + Y) % P == 0:
        return None
    slope = (3*x*x * pow(2*y, -1, P) if a == b else
             (Y-y) * pow(X-x, -1, P)) % P
    xx = (slope*slope-x-X) % P
    return xx, (slope*(x-xx)-y) % P


def mul(k, point=G):
    result = None
    k %= N
    while k:
        if k & 1:
            result = add(result, point)
        point = add(point, point)
        k >>= 1
    return result


def raw_point(point):
    if point is None:
        raise ValueError('Point at infinity')
    return b''.join(v.to_bytes(32, 'big') for v in point)


def parse_mpk(value):
    raw = bytes.fromhex(value)
    if len(raw) == 65 and raw[0] == 4:
        raw = raw[1:]
    if len(raw) != 64:
        raise ValueError('MPK must be 64 bytes x||y, optionally prefixed by 04')
    x, y = int.from_bytes(raw[:32], 'big'), int.from_bytes(raw[32:], 'big')
    if not (x < P and y < P and (y*y-x*x*x-7) % P == 0):
        raise ValueError('MPK is not a secp256k1 point')
    return raw


def offset(mpk, index, branch):
    if index < 0 or branch not in (0, 1):
        raise ValueError('Invalid child index or branch')
    return int.from_bytes(hash256(f'{index}:{branch}:'.encode('ascii') + mpk), 'big') % N


def stretch(seed_hex):
    # OldAccount receives the ASCII hexadecimal seed, not decoded seed bytes.
    original = seed_hex.encode('ascii')
    state = original
    for _ in range(100000):
        state = hashlib.sha256(state + original).digest()
    return int.from_bytes(state, 'big')


def address(point, compressed=False):
    raw = raw_point(point)
    public = bytes([2 + (point[1] & 1)]) + raw[:32] if compressed else b'\x04' + raw
    payload = b'\x00' + hashlib.new('ripemd160', hashlib.sha256(public).digest()).digest()
    value = payload + hash256(payload)[:4]
    alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    num, result = int.from_bytes(value, 'big'), ''
    while num:
        num, digit = divmod(num, 58)
        result = alphabet[digit] + result
    return '1' * (len(value)-len(value.lstrip(b'\x00'))) + result


def refine(states, h, bits, observed, modulus=N):
    """Intersect progressions with low_bits((m+h) % modulus) == observed.

    State=(residue, power-of-two step, first, last), with inclusive endpoints.
    Exact carry intervals also exclude invalid child scalar zero.
    """
    h %= modulus
    step = 1 << bits
    if not 0 <= observed < step:
        raise ValueError('Observed residue outside its bit range')
    output = set()
    for residue, old_step, first, last in states:
        for carry in (0, 1):
            required = (observed-h+carry*modulus) % step
            if (required-residue) % min(step, old_step):
                continue
            new_step = max(step, old_step)
            new_residue = required if step >= old_step else residue
            lo = max(first, carry*modulus-h+1)
            hi = min(last, (carry+1)*modulus-h-1)
            lo += (new_residue-lo) % new_step
            hi -= (hi-new_residue) % new_step
            if lo <= hi:
                output.add((new_residue, new_step, lo, hi))
    return sorted(output)


def compatible(mpk, known, branch, index_shift):
    states = [(0, 1, 1, N-1)]
    checked = []
    for puzzle, key in sorted(known.items()):
        if not (1 << (puzzle-1)) <= key < (1 << puzzle):
            raise ValueError(f'Key outside puzzle #{puzzle} interval')
        bits = puzzle-1
        h = offset(mpk, puzzle+index_shift, branch)
        states = refine(states, h, bits, key % (1 << bits))
        checked.append(puzzle)
        if not states:
            break
    return {'branch': branch, 'index_shift': index_shift,
            'status': 'arithmetic_compatible' if states else 'incompatible',
            'checked_indices': checked,
            'master_progressions': [dict(zip(('residue', 'step', 'first', 'last'), s)) for s in states],
            'remaining_integer_candidates': sum((s[3]-s[2])//s[1]+1 for s in states),
            'master_public_key_equality_checked': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mpk', required=True, help='Public master key in hexadecimal')
    parser.add_argument('--input', type=Path, default=Path(__file__).parent.parent/'data/puzzles.json')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    mpk = parse_mpk(args.mpk)
    source = args.input.read_bytes()
    rows = json.loads(source)['puzzles']
    known = {r['puzzle']: int(r['privkey_hex'], 16) for r in rows if r['status'] == 'solved'}
    # Fixed four mappings: puzzle 1 corresponds to child 0 or child 1, on either branch.
    results = [compatible(mpk, known, branch, shift)
               for branch in (0, 1) for shift in (-1, 0)]
    report = {'model': 'Electrum OldAccount; standard low-bit mask',
              'input_sha256': hashlib.sha256(source).hexdigest(), 'known_keys': len(known),
              'mpk': mpk.hex(), 'results': results,
              'limitation': 'Only this MPK and four mappings. Compatibility is necessary, not sufficient; no seed recovered.'}
    result = json.dumps(report, indent=2)+'\n'
    if args.output:
        args.output.write_text(result)
    print(result)


if __name__ == '__main__':
    main()
