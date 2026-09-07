#!/usr/bin/env python3
"""Deterministic controls for specific claims in the reviewed puzzle repository.

All private keys generated here are synthetic. They are not puzzle discoveries.
With --repo, run the original read-only analysis functions on synthetic inputs.
"""
import argparse
import ast
from collections import Counter
from contextlib import redirect_stdout
import hashlib
import io
import json
import math
from pathlib import Path
import runpy

from cryptography.hazmat.primitives.asymmetric import utils
from single_signature_lattice import N, synthetic_signature, validate_signature


def masked(number, value):
    return (1 << (number-1)) | (value & ((1 << (number-1))-1))


def weak_key(seed, number):
    raw = seed.to_bytes(2, 'big') + number.to_bytes(4, 'big')
    return masked(number, int.from_bytes(hashlib.sha256(raw).digest(), 'big'))


def original_function(path, name, globals_dict):
    """Load only the requested, reviewed function; do not run network/main code."""
    tree = ast.parse(path.read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    module = ast.Module(body=[node], type_ignores=[])
    exec(compile(module, str(path), 'exec'), globals_dict)
    return globals_dict[name]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    indices = list(range(1,71)) + list(range(75,131,5))

    # A one-bit nonce produces a 255-bit r; the signature is verified.
    d = (1 << 139) + 123456789
    row = synthetic_signature(140, d, 1, b'k=1 synthetic control')
    r, s, z = validate_signature(row)
    nonce_control = {'nonce': 1, 'r_bits': r.bit_length(), 'r_hex': row['r'],
                     'signature_validated': True, 'repository_small_r_condition': r.bit_length() < 200}
    assert r.bit_length() == 255

    # Fixed seed and model, selected before evaluating results. Deliberately weak.
    secret_seed = 12345
    generated = {i: weak_key(secret_seed, i) for i in indices}
    training = [32, 50, 70]
    recovered = [candidate for candidate in range(1 << 16)
                 if all(weak_key(candidate, i) == generated[i] for i in training)]
    assert recovered == [secret_seed]
    held_out = [i for i in indices if i not in training]
    assert all(weak_key(recovered[0], i) == generated[i] for i in held_out)
    seed_control = {'model': 'mask_i(SHA256(seed_16bit_big_endian || i_32bit_big_endian))',
                    'fixed_seed': secret_seed, 'seed_candidates_enumerated': 65536,
                    'training_indices': training, 'recovered_seeds': recovered,
                    'held_out_exact_matches': len(held_out), 'held_out_total': len(held_out),
                    'synthetic_71_prediction_correct': weak_key(recovered[0],71) == weak_key(secret_seed,71),
                    'limitation': 'No evidence that this model generated the actual puzzle keys.'}

    # Hashing a masked key is a different operation from hashing a hidden state.
    state = hashlib.sha256(b'fixed synthetic hidden-state chain').digest()
    states, keys = {}, {}
    for number in range(1,72):
        states[number] = state
        keys[number] = masked(number, int.from_bytes(state, 'big'))
        state = hashlib.sha256(state).digest()
    pairs = list(range(30,71))
    masked_hits = sum(masked(i+1, int.from_bytes(hashlib.sha256(keys[i].to_bytes(32,'big')).digest(),'big'))
                      == keys[i+1] for i in pairs)
    full_hits = sum(masked(i+1, int.from_bytes(hashlib.sha256(states[i]).digest(),'big'))
                   == keys[i+1] for i in pairs)
    assert masked_hits == 0 and full_hits == len(pairs)
    chain_control = {'model': 'state_(i+1)=SHA256(state_i); key_i=mask_i(state_i)',
                     'transitions_tested': len(pairs), 'masked_key_chain_matches': masked_hits,
                     'true_hidden_state_chain_matches': full_hits}

    if args.repo:
        analyze = original_function(args.repo/'analysis/ecdsa_signatures.py', 'analyze_signatures',
                                    {'Counter': Counter, 'math': math, 'N_ORDER': N})
        original_row = dict(row, r=r, s=s, r_hex=row['r'], s_hex=row['s'],
                            txid='synthetic-control', input_idx=0, sighash_type=1,
                            sig_der=utils.encode_dss_signature(r,s).hex())
        out = io.StringIO()
        with redirect_stdout(out):
            analyze([original_row], 'SYNTHETIC k=1')
        nonce_control['original_function_output'] = out.getvalue()
        nonce_control['original_small_r_alarm'] = 'r PEQUENO DETECTADO' in out.getvalue()
        assert not nonce_control['original_small_r_alarm']

        # This reviewed module only loads its local JSON and defines functions.
        weak = runpy.run_path(str(args.repo/'analysis/weak_generator_scan.py'))
        scan = weak['scan_index_hash']
        scan.__globals__['SOLVED'] = generated
        out = io.StringIO()
        with redirect_stdout(out):
            scan()
        seed_control['original_function_output'] = out.getvalue()
        seed_control['original_function_rejected_family'] = 'Index/seed-hash REJEITADO' in out.getvalue()
        assert seed_control['original_function_rejected_family']

    report = {'purpose': 'Counterexamples to overbroad inferences, not actual puzzle solutions',
              'small_nonce_control': nonce_control, 'weak_seed_control': seed_control,
              'hidden_state_hash_chain_control': chain_control}
    content = json.dumps(report, indent=2, ensure_ascii=False) + '\n'
    if args.output:
        args.output.write_text(content)
    else:
        print(content)
    print('Controls passed: k=1/r=255 bits; 16-bit seed recovered; hidden-state chain distinguished.')


if __name__ == '__main__':
    main()
