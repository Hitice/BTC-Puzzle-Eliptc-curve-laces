#!/usr/bin/env python3
"""Offline TXID and ECDSA verification for the five cached puzzle transactions.

Supports exactly the P2PKH and native P2WPKH SIGHASH_ALL inputs in this dataset.
Prevout scripts/amounts come from the cached explorer response; parent transactions
are not independently fetched here. No signing or transaction broadcast.
"""
import copy
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from creator_tx_forensics import parse_der, script_pushes, signature_payload, analyze
from electrum_old_mpk import add, mul, N, P


def digest(data):
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def compact(n):
    if n < 253:
        return bytes([n])
    for prefix, width in ((253, 2), (254, 4), (255, 8)):
        if n < 1 << (width*8):
            return bytes([prefix])+n.to_bytes(width, 'little')
    raise ValueError('CompactSize overflow')


def field(raw):
    return compact(len(raw))+raw


def outpoint(v):
    return bytes.fromhex(v['txid'])[::-1]+v['vout'].to_bytes(4, 'little')


def outputs(tx):
    return b''.join(o['value'].to_bytes(8, 'little')+field(bytes.fromhex(o['scriptpubkey']))
                    for o in tx['vout'])


def serialize(tx, witness=False, signing_index=None):
    has_witness = witness and any(v.get('witness') for v in tx['vin'])
    raw = tx['version'].to_bytes(4, 'little')
    if has_witness:
        raw += b'\x00\x01'
    raw += compact(len(tx['vin']))
    for i, v in enumerate(tx['vin']):
        script = bytes.fromhex(v.get('scriptsig', ''))
        if signing_index is not None:
            script = bytes.fromhex(v['prevout']['scriptpubkey']) if i == signing_index else b''
        raw += outpoint(v)+field(script)+v['sequence'].to_bytes(4, 'little')
    raw += compact(len(tx['vout']))+outputs(tx)
    if has_witness:
        for v in tx['vin']:
            stack = [bytes.fromhex(x) for x in v.get('witness', [])]
            raw += compact(len(stack))+b''.join(field(x) for x in stack)
    return raw+tx['locktime'].to_bytes(4, 'little')


def sighash_all(tx, index):
    v = tx['vin'][index]
    kind = v['prevout']['scriptpubkey_type']
    if kind == 'p2pkh':
        return digest(serialize(tx, signing_index=index)+b'\x01\x00\x00\x00')
    if kind != 'v0_p2wpkh':
        raise ValueError('Unsupported script type')
    program = bytes.fromhex(v['prevout']['scriptpubkey'])
    if len(program) != 22 or program[:2] != b'\x00\x14':
        raise ValueError('Invalid P2WPKH witness program')
    preimage = (tx['version'].to_bytes(4, 'little') +
        digest(b''.join(outpoint(w) for w in tx['vin'])) +
        digest(b''.join(w['sequence'].to_bytes(4, 'little') for w in tx['vin'])) +
        outpoint(v) + field(b'\x76\xa9\x14'+program[2:]+b'\x88\xac') +
        v['prevout']['value'].to_bytes(8, 'little') + v['sequence'].to_bytes(4, 'little') +
        digest(outputs(tx)) + tx['locktime'].to_bytes(4, 'little') + b'\x01\x00\x00\x00')
    return digest(preimage)


def decode_public(raw):
    if len(raw) == 33 and raw[0] in (2, 3):
        x = int.from_bytes(raw[1:], 'big')
        y = pow((x*x*x+7) % P, (P+1)//4, P)
        if y % 2 != raw[0] % 2:
            y = P-y
    elif len(raw) == 65 and raw[0] == 4:
        x, y = int.from_bytes(raw[1:33], 'big'), int.from_bytes(raw[33:], 'big')
    else:
        raise ValueError('Unsupported public key encoding')
    if x >= P or y >= P or (y*y-x*x*x-7) % P:
        raise ValueError('Public key outside curve')
    return x, y


def check_signature(tx, index):
    v = tx['vin'][index]
    sig, public, origin = signature_payload(v)
    r, s, flag, strict, minimal = parse_der(sig.hex())
    if flag != 1 or not strict or not minimal or not (1 <= r < N and 1 <= s < N):
        raise ValueError('Unsupported SIGHASH or invalid signature encoding/scalars')
    h160 = hashlib.new('ripemd160', hashlib.sha256(public).digest()).digest()
    script = (b'\x00\x14'+h160 if origin == 'witness' else
              b'\x76\xa9\x14'+h160+b'\x88\xac')
    if script.hex() != v['prevout']['scriptpubkey']:
        raise ValueError('Public key does not match prevout script')
    z = sighash_all(tx, index)
    inverse = pow(s, -1, N)
    point = add(mul(int.from_bytes(z, 'big')*inverse), mul(r*inverse, decode_public(public)))
    if point is None or point[0] % N != r:
        raise ValueError('ECDSA verification failed')
    return {'index': index, 'signature_source': origin, 'pubkey': public.hex(),
            'r': f'{r:064x}', 's': f'{s:064x}', 'z': z.hex(),
            'low_s': s <= N//2, 'valid': True}


def self_test():
    # Published native P2WPKH SIGHASH_ALL vector from BIP143.
    tx = {'version': 1, 'locktime': 17, 'vin': [
        {'txid': bytes.fromhex('fff7f7881a8099afa6940d42d1e7f6362bec38171ea3edf433541db4e4ad969f')[::-1].hex(),
         'vout': 0, 'sequence': 0xffffffee},
        {'txid': bytes.fromhex('ef51e1b804cc89d182d279655c3aa89e815b1b309fe287d9b2b55d57b90ec68a')[::-1].hex(),
         'vout': 1, 'sequence': 0xffffffff, 'scriptsig': '',
         'prevout': {'scriptpubkey_type': 'v0_p2wpkh', 'value': 600000000,
                     'scriptpubkey': '00141d0f172a0ecb48aee1be1f2687d2963ae33f71a1'},
         'witness': ['304402203609e17b84f6a7d30c80bfa610b5b4542f32a8a0d5447a12fb1366d7f01cc44a0220573a954c4518331561406f90300e8f3358f51928d43c212a8caed02de67eebee01',
                     '025476c2e83188368da1ff3e292e7acafcdb3566bb0ad253f62fc70f07aeee6357']}],
        'vout': [{'value': 112340000, 'scriptpubkey': '76a9148280b37df378db99f66f85c95a783a76ac7a6d5988ac'},
                 {'value': 223450000, 'scriptpubkey': '76a9143bde42dbee7e4dbe6a21b2d50ce2f0167faa815988ac'}]}
    assert sighash_all(tx, 1).hex() == 'c37af31116d1b27caf68aae9e3ac82f1477929014d5b917657d0eb49478cb670'
    assert check_signature(tx, 1)['valid']
    tampered = copy.deepcopy(tx)
    tampered['vin'][1]['prevout']['value'] += 1
    try:
        check_signature(tampered, 1)
    except ValueError:
        pass
    else:
        raise AssertionError('Modified signed amount was accepted')
    # DER truncation must be rejected explicitly, not silently omitted/crash.
    for malformed in ('', '3006020101020101', '300602050102010101'):
        try:
            parse_der(malformed)
        except ValueError:
            pass
        else:
            raise AssertionError('Malformed DER accepted')
    for malformed in ('02ff', '4c', '4d01', '4e010000', '76'):
        try:
            script_pushes(malformed)
        except ValueError:
            pass
        else:
            raise AssertionError('Malformed script push accepted')
    return {'bip143_digest_and_signature': 'passed', 'modified_amount_rejected': True,
            'malformed_der_cases_rejected': 3,
            'malformed_script_cases_rejected': 5,
            'source': 'https://raw.githubusercontent.com/bitcoin/bips/master/bip-0143.mediawiki'}


def main():
    here = Path(__file__).resolve().parent
    source = (here.parent/'data/creator_txs.json').read_bytes()
    records = json.loads(source)['transactions']
    report = {'input_sha256': hashlib.sha256(source).hexdigest(), 'controls': self_test(),
              'transactions': [], 'limitations': [
                  'Cached prevout scripts and amounts are used; parent transactions not independently fetched.',
                  'Metadata does not uniquely identify wallet software or the private-key generator.',
                  'No new puzzle private key recovered.']}
    seen = defaultdict(list)
    target_rows = json.loads((here.parent/'breach-review/target-signatures.json').read_text())
    target_txids = {'tx-2019': '17e4e323cfbc68d7f0071cad09364e8193eedf8fefbcbd8a21b4b65717a4b3d3'}
    assert len(target_rows) == 5
    target_checks = 0
    for record in records:
        tx = record['_raw']
        stripped, full = serialize(tx), serialize(tx, witness=True)
        assert digest(stripped)[::-1].hex() == tx['txid'] == record['txid']
        assert len(full) == tx['size'] and 3*len(stripped)+len(full) == tx['weight']
        assert sum(v['prevout']['value'] for v in tx['vin'])-sum(o['value'] for o in tx['vout']) == tx['fee']
        signatures = [check_signature(tx, i) for i in range(len(tx['vin']))]
        extracted = analyze(tx)
        assert extracted['indicators']['signed_inputs'] == len(signatures)
        for s in signatures:
            seen[s['r']].append({'txid': tx['txid'], 'input': s['index']})
            for target in target_rows:
                if target_txids[target['transaction']] == tx['txid'] and target['input'] == s['index']:
                    assert all(s[k] == target[k] for k in ('r', 's', 'z', 'pubkey'))
                    target_checks += 1
        report['transactions'].append({'txid': tx['txid'], 'label': record['label'],
            'txid_size_weight_fee_verified': True, 'version': tx['version'],
            'verified_signatures': len(signatures),
            'witness_signatures': sum(s['signature_source'] == 'witness' for s in signatures),
            'low_s_signatures': sum(s['low_s'] for s in signatures), 'signatures': signatures})
        print(record['label'], len(signatures), 'signatures verified', flush=True)
    report['verified_signatures'] = sum(t['verified_signatures'] for t in report['transactions'])
    report['repeated_r_groups'] = [values for values in seen.values() if len(values) > 1]
    report['previous_target_rows_matched'] = target_checks
    assert target_checks == len(target_rows), 'Not all prior target signatures were checked'
    target = here/'creator-signature-verification.json'
    target.write_text(json.dumps(report, indent=2)+'\n')
    print(target)


if __name__ == '__main__':
    main()
