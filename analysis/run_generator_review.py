#!/usr/bin/env python3
"""Reproduce the local key audit and a named negative MPK control, offline."""
import hashlib
import json
from pathlib import Path

from electrum_old_mpk import OFFICIAL_MPK, address, compatible, mul, parse_mpk, raw_point


def main():
    here = Path(__file__).resolve().parent
    source = (here.parent/'data/puzzles.json').read_bytes()
    rows = [r for r in json.loads(source)['puzzles'] if r['status'] == 'solved']
    known = {}
    errors = []
    for row in rows:
        i, d = row['puzzle'], int(row['privkey_hex'], 16)
        known[i] = d
        if d != row['privkey_int'] or not (1 << (i-1)) <= d < (1 << i):
            errors.append({'puzzle': i, 'error': 'key encoding or range mismatch'})
            continue
        point = mul(d)
        public = (bytes([2+(point[1] & 1)]) + raw_point(point)[:32]).hex()
        if address(point, compressed=True) != row['address']:
            errors.append({'puzzle': i, 'error': 'address mismatch'})
        if row.get('pubkey') and public != row['pubkey']:
            errors.append({'puzzle': i, 'error': 'public key mismatch'})
    if errors:
        raise RuntimeError(json.dumps(errors))
    mpk = parse_mpk(OFFICIAL_MPK)
    controls = [compatible(mpk, known, branch, shift)
                for branch in (0, 1) for shift in (-1, 0)]
    report = {
        'input_sha256': hashlib.sha256(source).hexdigest(),
        'known_keys_verified_against_addresses': len(rows),
        'stored_public_keys_verified': sum(bool(r.get('pubkey')) for r in rows),
        'verification_errors': errors,
        'negative_control': {
            'description': 'Official Electrum test MPK; no evidence linking it to the puzzle',
            'source': 'https://raw.githubusercontent.com/spesmilo/electrum/master/tests/test_wallet_vertical.py',
            'mpk': mpk.hex(),
            'results': controls,
        },
        'limits': [
            'No historically linked puzzle master public key or seed was found in this investigation.',
            'The negative control does not exclude Electrum or any other wallet family.',
            'Dataset contains 82 solved keys; the prior 83-key audit is not reproduced here.',
            'No new puzzle key recovered; no live balance/status checks performed.',
        ],
    }
    target = here/'generator-review-results.json'
    target.write_text(json.dumps(report, indent=2)+'\n')
    print(f'Verified {len(rows)} known keys; negative control: ' +
          ', '.join(r['status'] for r in controls))
    print(target)


if __name__ == '__main__':
    main()
