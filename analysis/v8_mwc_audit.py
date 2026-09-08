#!/usr/bin/env python3
"""Bounded exact bit-vector tests of raw V8 3.14.5 Math.random outputs.

Models fill 32 bytes consecutively, interpret as big-endian, then mask.
Each query uses only the 128 fully observed low bits of published puzzle #130.
Unknown/timeouts are recorded as inconclusive, never as model exclusions.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time

MODELS = {'word32_be': (32, 'big'), 'word32_le': (32, 'little'),
          'word16_be': (16, 'big'), 'byte8': (8, 'big')}
STARTS = ((1, 2), (0x12345678, 0x87654321), (0xffffffff, 0xffffffff))


def step(a, b):
    a = 18273*(a & 65535) + (a >> 16)
    b = 36969*(b & 65535) + (b >> 16)
    return a, b, ((a << 14)+(b & 262143)) & 0xffffffff


def observations(raw, model):
    width, order = MODELS[model]
    size = width//8
    return [int.from_bytes(raw[i:i+size], order) for i in range(0, len(raw), size)]


def produce(a, b, model, count):
    width, _ = MODELS[model]
    values = []
    for _ in range(count):
        a, b, word = step(a, b)
        values.append(word >> (32-width))
    return values


def solve(values, width, timeout_ms, fixed_state=None):
    import z3
    a0, b0 = z3.BitVecs('initial_a initial_b', 32)
    a, b = a0, b0
    solver = z3.SolverFor('QF_BV')
    solver.set(timeout=timeout_ms)
    # Allow all 64-bit pairs, even unreachable ones: unsat on this superset
    # is still an exclusion. Automatic reseeding at zero is outside the model.
    if fixed_state is not None:
        solver.add(a0 == fixed_state[0], b0 == fixed_state[1])
    for value in values:
        a = 18273*(a & 65535) + z3.LShR(a, 16)
        b = 36969*(b & 65535) + z3.LShR(b, 16)
        word = (a << 14) + (b & 262143)
        solver.add(z3.Extract(31, 32-width, word) == value)
    started = time.monotonic()
    status = solver.check()
    result = {'solver_status': str(status), 'elapsed_seconds': time.monotonic()-started}
    if status == z3.sat:
        m = solver.model()
        state = (m.eval(a0).as_long(), m.eval(b0).as_long())
        assert produce(*state, next(k for k, v in MODELS.items() if v[0] == width), len(values)) == values
        result['witness_state_hex'] = [f'{x:08x}' for x in state]
        result['witness_replayed'] = True
    elif status == z3.unknown:
        result['reason'] = solver.reason_unknown()
    return result


def byte_projection(values, timeout_ms, fixed_a=None):
    """Necessary constraints on state a, independent of b.

    output = ((a << 14) + (b & (2^18-1))) mod 2^32.
    Its upper byte is (a >> 10) & 255, optionally incremented by one.
    That carry requires (a & 1023) >= 1009. Relaxing b to allow either
    carry enlarges the solution set, so unsat still excludes the full model.
    """
    import z3
    initial = z3.BitVec('projection_a', 32)
    a = initial
    solver = z3.SolverFor('QF_BV')
    solver.set(timeout=timeout_ms)
    if fixed_a is not None:
        solver.add(initial == fixed_a)
    for value in values:
        a = 18273*(a & 65535) + z3.LShR(a, 16)
        high = z3.Extract(17, 10, a)
        solver.add(z3.Or(high == value,
                        z3.And(z3.UGE(a & 1023, 1009), high+1 == value)))
    started = time.monotonic()
    status = solver.check()
    result = {'solver_status': str(status), 'elapsed_seconds': time.monotonic()-started,
              'scope': 'Necessary conditions on state a only; sat is not a full witness'}
    if status == z3.unknown:
        result['reason'] = solver.reason_unknown()
    return result


def native_projection(binary, values):
    encoded = bytes(values).hex()
    run = subprocess.run([binary, encoded], check=True, capture_output=True, text=True, timeout=30)
    checked, survivors, witness = map(int, run.stdout.strip().split(','))
    return {'after_first_call_states_checked': checked, 'survivors': survivors,
            'scope': 'Exhaustive necessary-condition projection; not full MWC state recovery',
            'witness_a_after_first_call': witness if survivors else None}


def reference_check(real_bytes):
    here = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory(prefix='puzzle-mwc-') as folder:
        binary = str(Path(folder)/'reference')
        subprocess.run(['clang', '-std=c11', '-O2', str(here/'v8_mwc_reference.c'), '-o', binary],
                       check=True, capture_output=True, text=True, timeout=30)
        run = subprocess.run([binary], check=True, capture_output=True, text=True, timeout=10)
        controls = []
        for start in STARTS:
            projected = native_projection(binary, produce(*start, 'byte8', 16))
            assert projected['survivors'] >= 1
            controls.append(projected)
        projected_real = native_projection(binary, real_bytes)
    states = list(STARTS)
    for line in run.stdout.splitlines():
        seed, index, native, floating = map(int, line.split(','))
        a, b, word = step(*states[seed])
        states[seed] = (a, b)
        assert word == native == floating
    assert len(run.stdout.splitlines()) == 300
    return {'native_words_and_double_conversion_checked': 300,
            'native_fixture_sha256': hashlib.sha256(run.stdout.encode()).hexdigest(),
            'native_projection_positive_controls': controls,
            'native_projection_real': projected_real}


def main():
    import z3
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--timeout-ms', type=int, default=15000)
    parser.add_argument('--skip-byte-smt', action='store_true',
                        help='Use the exhaustive native byte projection instead of repeating slow SMT queries')
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('v8-mwc-results.json'))
    args = parser.parse_args()
    if not 1 <= args.timeout_ms <= 60000:
        parser.error('timeout must be between 1 and 60000 ms per query')
    source = (Path(__file__).resolve().parent.parent/'data/puzzles.json').read_bytes()
    rows = json.loads(source)['puzzles']
    key = int(next(r['privkey_hex'] for r in rows if r['puzzle'] == 130), 16)
    raw = (key & ((1 << 128)-1)).to_bytes(16, 'big')
    report = {'version': 'V8 3.14.5 recurrence and scaling; not the simplified V8 blog example',
              'source': 'https://raw.githubusercontent.com/v8/v8/3.14.5/src/v8.cc',
              'input_sha256': hashlib.sha256(source).hexdigest(),
              'anchor_key_hex': f'{key:064x}', 'byte_smt_skipped': args.skip_byte_smt,
              'z3_version': z3.get_version_string(), 'timeout_ms_per_query': args.timeout_ms,
              'anchor': 130, 'known_low_bits_used': 128,
              'native_control': reference_check(observations(raw, 'byte8')), 'controls': [], 'real_results': [],
              'limitations': ['No evidence linking this V8 version to the puzzle.',
                             'Only consecutive raw outputs and four layouts; not ARC4, hashes, HD derivation, or reseeding inside the observed segment.',
                             'A sat witness is arithmetic compatibility, not a recovered puzzle key.',
                             'unknown/timeout is inconclusive.']}
    def checkpoint():
        args.output.write_text(json.dumps(report, indent=2)+'\n')
    for model, (width, _) in MODELS.items():
        values = produce(*STARTS[1], model, 128//width)
        fixed = solve(values, width, args.timeout_ms, STARTS[1])
        assert fixed['solver_status'] == 'sat'
        changed = list(values)
        changed[-1] ^= 1
        assert solve(changed, width, args.timeout_ms, STARTS[1])['solver_status'] == 'unsat'
        skipped = {'solver_status': 'not_run', 'reason': 'Exhaustive native byte projection used'}
        free = skipped if width == 8 and args.skip_byte_smt else solve(values, width, args.timeout_ms)
        assert free['solver_status'] != 'unsat', 'Known witness was incorrectly excluded'
        report['controls'].append({'model': model, 'fixed_positive': 'sat',
                                   'fixed_tampered': 'unsat', 'free_recovery': free})
        print(f'{model} synthetic recovery: {free["solver_status"]}', flush=True)
        real = skipped if width == 8 and args.skip_byte_smt else solve(observations(raw, model), width, args.timeout_ms)
        report['real_results'].append({'model': model, **real})
        checkpoint()
        print(f'{model} actual puzzle: {real["solver_status"]}', flush=True)
    # Test the relaxed carry formula against every possible 10-bit residue
    # and all carry transition endpoints, independently of the recurrence.
    for low in range(1024):
        for bpart in (0, 1, 262142, 262143):
            carry = ((low << 14)+bpart) >> 24
            assert carry in (0, 1) and (carry == 0 or low >= 1009)
    control_values = produce(*STARTS[1], 'byte8', 16)
    assert byte_projection(control_values, args.timeout_ms, STARTS[1][0])['solver_status'] == 'sat'
    report['byte_projection'] = skipped if args.skip_byte_smt else byte_projection(observations(raw, 'byte8'), args.timeout_ms)
    report['conclusions'] = []
    for result in report['real_results']:
        native_excluded = (result['model'] == 'byte8' and
                           report['native_control']['native_projection_real']['survivors'] == 0)
        report['conclusions'].append({'model': result['model'],
            'status': 'incompatible' if native_excluded or result['solver_status'] == 'unsat' else 'inconclusive',
            'method': 'exhaustive_native_projection' if native_excluded else 'SMT'})
    checkpoint()
    print('byte8 necessary-condition projection:', report['byte_projection']['solver_status'], flush=True)
    print(args.output)


if __name__ == '__main__':
    main()
