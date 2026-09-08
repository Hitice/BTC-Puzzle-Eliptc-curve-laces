#!/usr/bin/env python3
"""Finish the V8 byte8 projection and test the three H2 masks without Z3.

Masks match master_seed_sweep.py; the byte stream is 32 consecutive outputs of
floor(Math.random()*256), under V8 3.14.5's native recurrence. Only full known
bytes are used. No assumptions about seed value or inter-key indexing.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from v8_mwc_audit import STARTS, native_projection, produce, step

MASKS = ('low', 'low_le', 'high')


def mask_value(raw, mask):
    value = int.from_bytes(raw[::-1] if mask == 'low_le' else raw, 'big')
    if mask == 'high':
        value >>= 126  # 256 - puzzle 130
    return (value & ((1 << 129)-1)) | (1 << 129)


def known_bytes(key, mask):
    if not (1 << 129) <= key < (1 << 130):
        raise ValueError('Anchor must be a puzzle #130 key')
    if mask == 'high':
        # Original bits 247..128: bytes 1..15. Key bits 121..2.
        return ((key >> 2) & ((1 << 120)-1)).to_bytes(15, 'big'), 1
    raw = (key & ((1 << 128)-1)).to_bytes(16, 'big')
    return (raw[::-1], 0) if mask == 'low_le' else (raw, 16)


def main():
    here = Path(__file__).resolve().parent
    source = (here.parent/'data/puzzles.json').read_bytes()
    row = next(r for r in json.loads(source)['puzzles'] if r['puzzle'] == 130)
    key = int(row['privkey_hex'], 16)
    report = {'source': 'https://raw.githubusercontent.com/v8/v8/3.14.5/src/v8.cc',
              'input_sha256': hashlib.sha256(source).hexdigest(),
              'native_source_sha256': hashlib.sha256((here/'v8_mwc_reference.c').read_bytes()).hexdigest(),
              'anchor': 130, 'anchor_key_hex': row['privkey_hex'],
              'generator_layout': '32 consecutive floor(Math.random()*256) bytes',
              'positive_controls': [], 'results': [],
              'limitations': ['Only V8 3.14.5 native recurrence and three explicit masks.',
                             'No within-key extra calls, reseeding, hashes, ARC4, or HD derivation.',
                             'No historical evidence linking this generator to the puzzle.',
                             'A projection survivor is not a recovered full state or puzzle key.']}
    with tempfile.TemporaryDirectory(prefix='puzzle-native-masks-') as folder:
        binary = str(Path(folder)/'reference')
        subprocess.run(['clang', '-std=c11', '-O2', str(here/'v8_mwc_reference.c'), '-o', binary],
                       check=True, capture_output=True, text=True, timeout=30)
        reference = subprocess.run([binary], check=True, text=True, capture_output=True, timeout=10)
        states = list(STARTS)
        lines = reference.stdout.splitlines()
        assert len(lines) == 300
        for line in lines:
            seed, index, native, floating = map(int, line.split(','))
            a, b, expected = step(*states[seed])
            states[seed] = (a, b)
            assert native == floating == expected
        report['native_reference_words_checked'] = len(lines)
        for seed, start in enumerate(STARTS):
            raw = bytes(produce(*start, 'byte8', 32))
            for mask in MASKS:
                visible, skip = known_bytes(mask_value(raw, mask), mask)
                assert visible == raw[skip:skip+len(visible)]
                a, b = start
                for _ in range(skip+1):
                    a, b, _ = step(a, b)
                result = native_projection(binary, visible)
                # The fixtures have unique projected survivors; verify identity.
                assert result['survivors'] == 1 and result['witness_a_after_first_call'] == a
                report['positive_controls'].append({'seed_index': seed, 'mask': mask,
                    'known_bits': 8*len(visible), 'true_projected_state_recovered': True, **result})
        for mask in MASKS:
            visible, skip = known_bytes(key, mask)
            result = native_projection(binary, visible)
            report['results'].append({'mask': mask, 'known_bits': 8*len(visible),
                'first_observed_byte_index': skip,
                'status': 'incompatible' if result['survivors'] == 0 else 'inconclusive', **result})
    target = here/'v8-native-masks-results.json'
    target.write_text(json.dumps(report, indent=2)+'\n')
    print(f'{len(report["positive_controls"])} positive controls passed; 300 native words checked')
    for result in report['results']:
        print(result['mask'], result['status'], result['after_first_call_states_checked'], 'states')
    print(target)


if __name__ == '__main__':
    main()
