#!/usr/bin/env python3
"""Exact state recovery for four explicit raw java.util.Random key layouts.

Not a test of SecureRandom, hashed PRNG output, arbitrary calls, or Java wallets
in general. Models are fixed before evaluation; puzzle #70 is the sole anchor.
Requires only Python stdlib; Java independently generates the positive fixtures.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

MULT = 0x5DEECE66D
INC = 11
MOD = 1 << 48
MASK = MOD-1
MODELS = ('bigint256', 'bigint_i', 'bigint_i_minus_1', 'int32_be')
ANCHOR = 70


def layout(puzzle, model):
    if model not in MODELS or not 1 <= puzzle <= 256:
        raise ValueError('Unsupported layout or puzzle index')
    bits = 256 if model in ('bigint256', 'int32_be') else (
        puzzle if model == 'bigint_i' else puzzle-1)
    return (bits+7)//8, 'big' if model == 'int32_be' else 'little'


def affine(steps):
    """Return exact LCG jump coefficients, including negative steps."""
    a, c = MULT, INC
    if steps < 0:
        a = pow(a, -1, MOD)
        c = -a*c % MOD
        steps = -steps
    ra, rc = 1, 0
    while steps:
        if steps & 1:
            ra, rc = a*ra % MOD, (a*rc+c) % MOD
        a, c = a*a % MOD, (a*c+c) % MOD
        steps >>= 1
    return ra, rc


def advance(state, steps):
    a, c = affine(steps)
    return (a*state+c) & MASK


def generate(state, puzzle, model):
    size, word_order = layout(puzzle, model)
    raw = bytearray()
    for _ in range((size+3)//4):
        state = (state*MULT+INC) & MASK
        raw.extend((state >> 16).to_bytes(4, word_order))
    value = int.from_bytes(raw[:size], 'big')
    top = 1 << (puzzle-1)
    return state, (value & (top-1)) | top


def recover_anchor(key, puzzle, model):
    """Enumerate all states compatible with one fully observed output word.

    A 32-bit output fixes the upper 32 state bits; all 2^16 suffixes are
    checked. The inverse recurrence recovers the state before this key.
    """
    if not 1 << (puzzle-1) <= key < 1 << puzzle:
        raise ValueError('Anchor key outside puzzle interval')
    size, word_order = layout(puzzle, model)
    mask = ((1 << (puzzle-1))-1).to_bytes(size, 'big')
    observed = (key & ((1 << (puzzle-1))-1)).to_bytes(size, 'big')
    chunks = [j for j in range(0, size-3, 4) if mask[j:j+4] == b'\xff'*4]
    if not chunks:
        raise ValueError('Anchor must expose a full 32-bit output word')
    j = chunks[-1]
    word = int.from_bytes(observed[j:j+4], word_order)
    reverse_a, reverse_c = affine(-(j//4+1))
    survivors = []
    for suffix in range(1 << 16):
        after_word = (word << 16) | suffix
        before_key = (reverse_a*after_word+reverse_c) & MASK
        _, predicted = generate(before_key, puzzle, model)
        if predicted == key:
            survivors.append(before_key)
    return survivors


def infer_stream(known, model):
    states = recover_anchor(known[ANCHOR], ANCHOR, model)
    prefix_calls = sum((layout(i, model)[0]+3)//4 for i in range(1, ANCHOR))
    results = []
    for before_anchor in states:
        initial = advance(before_anchor, -prefix_calls)
        current, matches, mismatches, predictions = initial, [], [], {}
        for i in range(1, 161):
            current, prediction = generate(current, i, model)
            predictions[i] = prediction
            if i in known and i != ANCHOR:
                (matches if prediction == known[i] else mismatches).append(i)
        results.append({'initial_internal_state_hex': f'{initial:012x}',
                        'validation_matches': len(matches),
                        'validation_total': len(known)-1,
                        'mismatch_indices': mismatches,
                        'prediction_71_hex': f'{predictions[71]:x}' if not mismatches else None})
    return {'model': model, 'anchor_puzzle': ANCHOR, 'state_suffixes_checked': 1 << 16,
            'anchor_survivors': len(states), 'candidates': results,
            'status': 'compatible' if any(not r['mismatch_indices'] for r in results) else 'incompatible'}


def self_test(known_indices):
    here = Path(__file__).resolve().parent
    run = subprocess.run(['java', str(here/'JavaRandomVectors.java')],
                         check=True, text=True, capture_output=True, timeout=60)
    fixtures = {}
    for line in run.stdout.splitlines():
        seed, model, puzzle, value = line.split(',')
        fixtures.setdefault((int(seed), model), {})[int(puzzle)] = int(value, 16)
    if len(fixtures) != 12 or any(len(v) != 160 for v in fixtures.values()):
        raise AssertionError('Incomplete Java fixtures')
    controls = []
    for (seed, model), expected in fixtures.items():
        state = (seed ^ MULT) & MASK
        original = state
        for i, key in sorted(expected.items()):
            state, value = generate(state, i, model)
            assert key == value, (seed, model, i)
        assert advance(original, 557) == advance(advance(original, 1000), -443)
        known = {i: expected[i] for i in known_indices}
        result = infer_stream(known, model)
        good = [r for r in result['candidates'] if not r['mismatch_indices']]
        assert len(good) == 1 and int(good[0]['initial_internal_state_hex'], 16) == original
        assert int(good[0]['prediction_71_hex'], 16) == expected[71]
        # Alter a validation key, leaving the recovery anchor untouched.
        tampered = dict(known)
        tampered[65] ^= 1
        assert infer_stream(tampered, model)['status'] == 'incompatible'
        controls.append({'seed': seed, 'model': model, 'original_state_recovered': True,
                         'validation_matches': good[0]['validation_matches'],
                         'validation_total': good[0]['validation_total'],
                         'synthetic_71_prediction_correct': True,
                         'tampered_validation_rejected': True})
    return {'java_runtime': subprocess.run(['java', '-version'], check=True,
            text=True, capture_output=True).stderr.splitlines()[0],
            'java_fixture_sha256': hashlib.sha256(run.stdout.encode()).hexdigest(),
            'java_generated_keys_compared': 1920, 'controls': controls}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('java-random-results.json'))
    args = parser.parse_args()
    source = (Path(__file__).resolve().parent.parent/'data/puzzles.json').read_bytes()
    known = {r['puzzle']: int(r['privkey_hex'], 16) for r in json.loads(source)['puzzles']
             if r['status'] == 'solved'}
    start = time.monotonic()
    tests = self_test(sorted(known))
    print('Independent Java fixtures and recovery controls passed.', flush=True)
    results = [infer_stream(known, model) for model in MODELS]
    report = {'input_sha256': hashlib.sha256(source).hexdigest(), 'known_keys': len(known),
              'self_tests': tests, 'real_results': results,
              'elapsed_seconds': time.monotonic()-start,
              'limitations': ['No historical evidence linking java.util.Random to the puzzle.',
                             'Only the four raw output layouts are tested; not SecureRandom or hashed outputs.',
                             'Zero anchor survivors excludes any 48-bit state for that key/layout, even with per-key reseeding.',
                             'Cross-key predictions additionally assume an uninterrupted stream from puzzle 1.',
                             'Synthetic recovery is not a recovered Bitcoin puzzle key.']}
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    for result in results:
        print(result['model'], result['status'], 'anchor survivors:', result['anchor_survivors'])
    print(args.output)


if __name__ == '__main__':
    main()
